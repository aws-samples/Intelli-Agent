import json
import os 
from functools import partial
import copy
import asyncio

from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from ..retriever import (
    QueryDocumentRetriever,
    QueryQuestionRetriever,
    index_results_format,
)
from ..serialization_utils import JSONEncoder
from ..reranker import BGEReranker, MergeReranker
from ..retriever import (
    QueryDocumentRetriever,
    QueryQuestionRetriever,
    index_results_format,
)

from ..logger_utils import logger
from ..langchain_utils import add_key_to_debug,chain_logger,RunnableDictAssign
from ..context_utils import contexts_trunc
from ..llm_utils import LLMChain
from ..constant import IntentType
from ..query_process_utils import get_query_process_chain
from ..intent_utils import auto_intention_recoginition_chain
from .. import parse_config

zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")

def return_strict_qq_result(x):
    return {
        "answer": json.dumps(
            x["intent_info"]["strict_qq_intent_result"], ensure_ascii=False
        ),
        "sources": [],
        "contexts": [],
        "context_docs": [],
        "context_sources": [],
    }


def get_qd_chain(
    aos_index_list, retriever_top_k=10, reranker_top_k=5, using_whole_doc=True, chunk_num=0, enable_reranker=True
):
    retriever_list = [
        QueryDocumentRetriever(index, using_whole_doc, chunk_num, retriever_top_k)
        for index in aos_index_list
    ]
    lotr = MergerRetriever(retrievers=retriever_list)
    if enable_reranker:
        compressor = BGEReranker(top_n=reranker_top_k)
    else:
        compressor = MergeReranker(top_n=reranker_top_k)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    qd_chain = RunnablePassthrough.assign(docs=compression_retriever) 
    return qd_chain

def get_qq_chain(aos_index_list, retriever_top_k=5):
    retriever_list = [
        QueryQuestionRetriever(index, size=retriever_top_k)
        for index in aos_index_list
    ]
    qq_chain = MergerRetriever(retrievers=retriever_list)
    qq_chain = RunnablePassthrough.assign(qq_result=qq_chain)
    qq_chain = chain_logger(qq_chain, 'qq_chain')
    return qq_chain

def get_qd_llm_chain(
    aos_index_list, 
    rag_config, 
    stream=False, 
    # top_n=5
):
    using_whole_doc = rag_config['retriever_config']['using_whole_doc']
    chunk_num = rag_config['retriever_config']['chunk_num']
    retriever_top_k = rag_config['retriever_config']['retriever_top_k']
    reranker_top_k = rag_config['retriever_config']['reranker_top_k']
    enable_reranker = rag_config['retriever_config']['enable_reranker']

    qd_chain = get_qd_chain(aos_index_list, using_whole_doc=using_whole_doc,
                            chunk_num=chunk_num, retriever_top_k=retriever_top_k,
                            reranker_top_k=reranker_top_k, enable_reranker=enable_reranker)
    
    generator_llm_config = rag_config['generator_llm_config']
    # TODO opt with efficiency
    context_num = generator_llm_config['context_num']
    llm_chain = RunnableDictAssign(lambda x: contexts_trunc(x['docs'],context_num=context_num)) |\
          RunnablePassthrough.assign(
               answer=LLMChain.get_chain(
                    intent_type=IntentType.KNOWLEDGE_QA.value,
                    stream=stream,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history']
          )

    qd_llm_chain = chain_logger(qd_chain, 'qd_retriever') | chain_logger(llm_chain,'llm_chain')
    return qd_llm_chain

def get_chat_llm_chain(
        rag_config,
        stream=False
        ):

    chat_llm_chain = LLMChain.get_chain(
        intent_type=IntentType.CHAT.value,
        stream=stream,
        **rag_config['generator_llm_config']
    ) | {
        "answer": lambda x: x,
        "sources": lambda x: [],
        "contexts": lambda x: [],
        "intent_type": lambda x: IntentType.CHAT.value,
        "context_docs": lambda x: [],
        "context_sources": lambda x: [],
    }
    return chat_llm_chain

def market_chain_entry(
    query_input: str,
    stream=False,
    manual_input_intent=None,
    event_body=None,
    rag_config=None
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.
    :param stream(Bool): Whether to use llm stream decoding output.
    return: answer(str)
    """
    if rag_config is None:
        rag_config = parse_config.parse_mkt_entry_core_config(event_body)

    assert rag_config is not None

    logger.info(f'market rag configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}')

    generator_llm_config = rag_config['generator_llm_config']
    intent_type = rag_config['intent_config']['intent_type']
    aos_index_dict = json.loads(os.environ["aos_index_dict"])
        
    aos_index_mkt_qd_name = aos_index_dict["aos_index_mkt_qd"]
    aos_index_mkt_qq_name = aos_index_dict["aos_index_mkt_qq"]
    aos_index_dgr_qd_name = aos_index_dict["aos_index_dgr_qd"]
    aos_index_dgr_faq_qd_name = aos_index_dict["aos_index_dgr_faq_qd"]
    aos_index_dgr_qq_name = aos_index_dict["aos_index_dgr_qq"]
    aos_index_acts_qd_name = "acts-qd-index-20240305"

    debug_info = {}
    contexts = []
    sources = []
    answer = ""
    intent_info = {
        "manual_input_intent": manual_input_intent,
        "strict_qq_intent_result": {},
    }

    # 1. Strict Query Question Intent
    # 1.1. strict query question retrieval.
    # strict_q_q_chain = get_strict_qq_chain(aos_index_mkt_qq)

    # 2. Knowledge QA Intent
    # 2.1 query question retrieval.
    aos_index_dgr_qq = {
        "index_name": aos_index_dgr_qq_name,
        "lang": "zh",
        "embedding_endpoint": zh_embedding_endpoint,
        "source_field": "source",
        "vector_field": "vector_field",
        "model_type": "vector"
    }
    aos_index_mkt_qq = {
        "index_name": aos_index_mkt_qq_name,
        "lang": "zh",
        "embedding_endpoint": zh_embedding_endpoint,
        "source_field": "file_path",
        "vector_field": "vector_field",
        "model_type": "vector"
    }
    qq_chain = get_qq_chain([aos_index_dgr_qq, aos_index_mkt_qq])

    # 2.2 query document retrieval + LLM.
    aos_index_acts_qd = {
        "index_name": aos_index_acts_qd_name,
        "lang": "zh",
        "embedding_endpoint": zh_embedding_endpoint,
        "source_field": "source",
        "vector_field": "vector_field",
        "model_type": "m3"
    }

    qd_llm_chain = get_qd_llm_chain(
        [aos_index_acts_qd],
        rag_config,
        stream,
    )

    # 2.3 query question router.
    def qq_route(info):
        for doc in info["qq_result"]:
            if doc.metadata["score"] > rag_config["retriever_config"]["q_q_match_threshold"]:
                output = {
                    "answer": doc.metadata["answer"],
                    "sources": doc.metadata["source"],
                    "contexts": [],
                    "context_docs": [],
                    "context_sources": [],
                    # "debug_info": lambda x: x["debug_info"],
                }
                logger.info('qq matched...')
                info.update(output)
                return info
        return qd_llm_chain

    qq_qd_llm_chain = qq_chain | RunnableLambda(qq_route)

    # query process chain
    query_process_chain = get_query_process_chain(
        rag_config['chat_history'],
        rag_config['query_process_config']
    )
    # | add_key_to_debug(add_key='conversation_query_rewrite',debug_key="debug_info")
    #   | add_key_to_debug(add_key='query_rewrite',debug_key="debug_info")
    
    # query_rewrite_chain = chain_logger(
    #     query_rewrite_chain,
    #     "query rewrite module"
    # )
    # intent recognition
    intent_recognition_chain = auto_intention_recoginition_chain(
        q_q_retriever_config={
            "index_q_q":aos_index_mkt_qq_name,
            'lang':'zh',
            'embedding_endpoint':zh_embedding_endpoint,
            "q_q_match_threshold": rag_config['retriever_config']['q_q_match_threshold']
        },
        intent_config=rag_config['intent_config']
    )

    intent_recognition_chain = chain_logger(
        intent_recognition_chain,
        'intention module',
        log_output_template='intent chain output: {intent_type}'
    )
   
    full_chain = query_process_chain | intent_recognition_chain  | RunnableBranch(
        (lambda x:x['intent_type'] == IntentType.KNOWLEDGE_QA.value, qq_qd_llm_chain),
        (lambda x:x['intent_type'] == IntentType.STRICT_QQ.value, return_strict_qq_result),
        # (lambda x:x['intent_type'] == IntentType.STRICT_QQ.value, strict_q_q_chain),
        get_chat_llm_chain(rag_config=rag_config,stream=stream),  # chat
    )
    # full_chain = intent_recognition_chain
    # full_chain = RunnableLambda(route)
    response = asyncio.run(full_chain.ainvoke(
        {
            "query": query_input,
            "debug_info": debug_info,
            "intent_type": intent_type,
            "intent_info": intent_info,
            "chat_history": rag_config['chat_history']
        }
    ))

    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]

    return answer, sources, contexts, debug_info