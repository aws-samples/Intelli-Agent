import asyncio
import json
import logging
import os
import time
from functools import partial
from textwrap import dedent

import boto3
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from .. import parse_config
from ..constant import CONVERSATION_SUMMARY_TYPE, IntentType, RerankerType
from ..context_utils import (
    contexts_trunc,
    documents_list_filter,
    retriever_results_format,
)
from ..intent_utils import IntentRecognitionAOSIndex
from ..langchain_utils import (
    RunnableDictAssign,
    RunnableParallelAssign,
    chain_logger,
    format_trace_infos,
)
from ..llm_utils import LLMChain
from ..query_process_utils.preprocess_utils import (
    get_service_name,
    is_api_query,
    is_query_too_short,
    language_check,
    query_translate,
)
from ..reranker import BGEM3Reranker, BGEReranker, MergeReranker
from ..retriever import (
    QueryDocumentBM25Retriever,
    QueryDocumentKNNRetriever,
    QueryQuestionRetriever,
)
from ..serialization_utils import JSONEncoder
from ..workspace_utils import WorkspaceManager

logger = logging.getLogger("main_entry")
logger.setLevel(logging.INFO)

workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)


def get_workspace_list(workspace_ids):
    qq_workspace_list = []
    qd_workspace_list = []
    for workspace_id in workspace_ids:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace or "index_type" not in workspace:
            logger.warning(f"workspace {workspace_id} not found")
            continue
        if workspace["index_type"] == "qq":
            qq_workspace_list.append(workspace)
        else:
            qd_workspace_list.append(workspace)
    return qq_workspace_list, qd_workspace_list


def get_qd_chain(qd_config, qd_workspace_list):
    using_whole_doc = qd_config["using_whole_doc"]
    context_num = qd_config["context_num"]
    retriever_top_k = qd_config["retriever_top_k"]
    # reranker_top_k = qd_config['reranker_top_k']
    # enable_reranker = qd_config['enable_reranker']
    reranker_type = qd_config["reranker_type"]
    qd_query_key = qd_config["query_key"]
    retriever_list = [
        QueryDocumentKNNRetriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ] + [
        QueryDocumentBM25Retriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ]

    lotr = MergerRetriever(retrievers=retriever_list)
    if reranker_type == RerankerType.BGE_RERANKER.value:
        compressor = BGEReranker(query_key=qd_query_key)
    elif reranker_type == RerankerType.BGE_M3_RERANKER.value:
        compressor = BGEM3Reranker()
    else:
        compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    qd_chain = chain_logger(
        RunnablePassthrough.assign(
            docs=compression_retriever | RunnableLambda(retriever_results_format)
        ),
        "qd chain",
    )
    return qd_chain



def main_chain_entry(
    query_input: str,
    stream=False,
    # manual_input_intent=None,
    event_body=None,
    rag_config=None,
    message_id=None,
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.

    return: answer(str)
    """
    if rag_config is None:
        rag_config = parse_config.parse_main_entry_config(event_body)

    assert rag_config is not None

    logger.info(
        f"common rag knowledge configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}"
    )

    workspace_ids = rag_config["retriever_config"]["workspace_ids"]
    event_workspace_ids = rag_config["retriever_config"]["event_workspace_ids"]
    qq_workspace_list, qd_workspace_list = get_workspace_list(workspace_ids)
    event_qq_workspace_list, event_qd_workspace_list = get_workspace_list(
        event_workspace_ids
    )

    # logger.info(f"qq_workspace_list: {qq_workspace_list}\nqd_workspace_list: {qd_workspace_list}")

    debug_info = {"response_msg": "normal"}
    contexts = []
    sources = []
    answer = ""
    trace_infos = []

    ############################
    # step 4. qd retriever chain#
    ############################
    qd_config = rag_config["retriever_config"]["qd_config"]
    qd_chain = get_qd_chain(qd_config, qd_workspace_list)

    #####################
    # step 5. llm chain #
    #####################
    generator_llm_config = rag_config["generator_llm_config"]
    context_num = generator_llm_config["context_num"]
    llm_chain = RunnableDictAssign(
        lambda x: contexts_trunc(x["docs"], context_num=context_num)
    ) | RunnablePassthrough.assign(
        answer=LLMChain.get_chain(
            intent_type=IntentType.KNOWLEDGE_QA.value,
            stream=stream,
            **generator_llm_config,
        ),
        chat_history=lambda x: rag_config["chat_history"],
    )

    #######################
    # step 6.3 full chain #
    #######################

    full_chain = qd_chain | llm_chain

    response = asyncio.run(
        full_chain.ainvoke(
            {
                "query": query_input,
                "debug_info": debug_info,
                # "intent_type": intent_type,
                # "intent_info": intent_info,
                "chat_history": (
                    rag_config["chat_history"] if rag_config["use_history"] else []
                ),
                # "query_lang": "zh"
            }
        )
    )

    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]
    trace_info = format_trace_infos(trace_infos)
    logger.info(f"chain trace info:\n{trace_info}")

    return answer, sources, contexts, debug_info
