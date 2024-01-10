import copy
import json
import logging
import os
import sys
import time
import traceback
import uuid

import boto3
from langchain.callbacks.base import BaseCallbackHandler
from langchain.globals import set_verbose
from langchain.llms import OpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.pydantic_v1 import BaseModel, Field, validator
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank

# from llm_utils import CustomLLM
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain.retrievers.web_research import WebResearchRetriever
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain.utilities import GoogleSearchAPIWrapper
from reranker import BGEReranker
from retriever import (
    QueryDocumentRetriever,
    QueryQuestionRetriever,
    index_results_format,
)

logger = logging.getLogger()
# handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
# logger.addHandler(handler)
opensearch_logger = logging.getLogger("opensearch")
opensearch_logger.setLevel(logging.ERROR)
boto3_logger = logging.getLogger("botocore")
boto3_logger.setLevel(logging.ERROR)

from aos_utils import LLMBotOpenSearchClient
from constant import IntentType, Type
from ddb_utils import DynamoDBChatMessageHistory
from intent_utils import auto_intention_recoginition_chain
from langchain_utils import create_identity_lambda

# from llm_utils import generate as llm_generate
from llm_utils import get_llm_chain
from llmbot_utils import (
    QueryType,
    combine_recalls,
    concat_recall_knowledge,
    process_input_messages,
)
from preprocess_utils import run_preprocess
from response_utils import process_response
from sm_utils import SagemakerEndpointVectorOrCross
from constant import Type,IntentType
from intent_utils import auto_intention_recoginition_chain
from langchain_utils import add_key_to_debug
from query_expansion_utils import get_query_expansion_chain


region = os.environ["AWS_REGION"]
embedding_endpoint = os.environ.get("embedding_endpoint", "")
zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")
cross_endpoint = os.environ.get("rerank_endpoint", "")
rerank_endpoint = os.environ.get("rerank_endpoint", "")
aos_endpoint = os.environ.get("aos_endpoint", "")
aos_index = os.environ.get("aos_index", "")
aos_faq_index = os.environ.get("aos_faq_index", "")
aos_ug_index = os.environ.get("aos_ug_index", "")
llm_endpoint = os.environ.get("llm_endpoint", "")
chat_session_table = os.environ.get("chat_session_table", "")
websocket_url = os.environ.get("websocket_url", "")
sm_client = boto3.client("sagemaker-runtime")
aos_client = LLMBotOpenSearchClient(aos_endpoint)
ws_client = None

# get aos_index_dict


class APIException(Exception):
    def __init__(self, message, code: str = None):
        if code:
            super().__init__("[{}] {}".format(code, message))
        else:
            super().__init__(message)


def load_ws_client():
    global ws_client
    if ws_client is None:
        ws_client = boto3.client("apigatewaymanagementapi", endpoint_url=websocket_url)
    return ws_client


def handle_error(func):
    """Decorator for exception handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIException as e:
            logger.exception(e)
            raise e
        except Exception as e:
            logger.exception(e)
            raise RuntimeError(
                "Unknown exception, please check Lambda log for more details"
            )

    return wrapper


def get_faq_answer(source, index_name):
    opensearch_query_response = aos_client.search(
        index_name=index_name,
        query_type="basic",
        query_term=source,
        field="metadata.source",
    )
    for r in opensearch_query_response["hits"]["hits"]:
        if r["_source"]["metadata"]["field"] == "answer":
            return r["_source"]["content"]
    return ""


def get_faq_content(source, index_name):
    opensearch_query_response = aos_client.search(
        index_name=index_name,
        query_type="basic",
        query_term=source,
        field="metadata.source",
    )
    for r in opensearch_query_response["hits"]["hits"]:
        if r["_source"]["metadata"]["field"] == "all_text":
            return r["_source"]["content"]
    return ""


def organize_faq_results(response, index_name):
    """
    Organize results from aos response

    :param query_type: query type
    :param response: aos response json
    """
    results = []
    if not response:
        return results
    aos_hits = response["hits"]["hits"]
    for aos_hit in aos_hits:
        result = {}
        try:
            result["source"] = aos_hit["_source"]["metadata"]["source"]
            result["score"] = aos_hit["_score"]
            result["detail"] = aos_hit["_source"]
            result["content"] = aos_hit["_source"]["content"]
            result["answer"] = get_faq_answer(result["source"], index_name)
            result["doc"] = get_faq_content(result["source"], index_name)
        except:
            logger.info("index_error")
            logger.info(aos_hit["_source"])
            continue
        # result.update(aos_hit["_source"])
        results.append(result)
    return results


def get_ug_content(source, index_name):
    opensearch_query_response = aos_client.search(
        index_name=index_name,
        query_type="basic",
        query_term=source,
        field="metadata.source",
        size=100,
    )
    for r in opensearch_query_response["hits"]["hits"]:
        if r["_source"]["metadata"]["field"] == "all_text":
            return r["_source"]["content"]
    return ""


def organize_ug_results(response, index_name):
    """
    Organize results from aos response

    :param query_type: query type
    :param response: aos response json
    """
    results = []
    aos_hits = response["hits"]["hits"]
    for aos_hit in aos_hits:
        result = {}
        result["source"] = aos_hit["_source"]["metadata"]["source"]
        result["score"] = aos_hit["_score"]
        result["detail"] = aos_hit["_source"]
        result["content"] = aos_hit["_source"]["content"]
        result["doc"] = get_ug_content(result["source"], index_name)
        # result.update(aos_hit["_source"])
        results.append(result)
    return results


def organize_results(response, aos_index=None):
    """
    Organize results from aos response

    :param query_type: query type
    :param response: aos response json
    """
    results = []
    aos_hits = response["hits"]["hits"]
    for aos_hit in aos_hits:
        result = {}
        result["source"] = aos_hit["_source"]["metadata"]["file_path"]
        result["score"] = aos_hit["_score"]
        result["detail"] = aos_hit["_source"]
        result["content"] = aos_hit["_source"]["text"]
        result["doc"] = aos_hit["_source"]["text"]
        results.append(result)
    return results


def remove_redundancy_debug_info(results):
    filtered_results = copy.deepcopy(results)
    for result in filtered_results:
        for field in list(result["detail"].keys()):
            if field.endswith("embedding") or field.startswith("vector"):
                del result["detail"][field]
    return filtered_results


def parse_query(
    query_input: str,
    history: list,
    zh_embedding_model_endpoint: str,
    en_embedding_model_endpoint: str,
    debug_info: dict,
):
    start = time.time()
    # concatenate query_input and history to unified prompt
    query_knowledge = "".join([query_input] + [row[0] for row in history][::-1])

    # get query embedding
    parsed_query = run_preprocess(query_knowledge)
    debug_info["query_parser_info"] = parsed_query
    if parsed_query["query_lang"] == "zh":
        parsed_query["zh_query"] = query_knowledge
        parsed_query["en_query"] = parsed_query["translated_text"]
    elif parsed_query["query_lang"] == "en":
        parsed_query["zh_query"] = parsed_query["translated_text"]
        parsed_query["en_query"] = query_knowledge
    zh_query_similarity_embedding_prompt = parsed_query["zh_query"]
    en_query_similarity_embedding_prompt = parsed_query["en_query"]
    zh_query_relevance_embedding_prompt = (
        "为这个句子生成表示以用于检索相关文章：" + parsed_query["zh_query"]
    )
    en_query_relevance_embedding_prompt = (
        "Represent this sentence for searching relevant passages: "
        + parsed_query["en_query"]
    )
    parsed_query["zh_query_similarity_embedding"] = SagemakerEndpointVectorOrCross(
        prompt=zh_query_similarity_embedding_prompt,
        endpoint_name=zh_embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    parsed_query["zh_query_relevance_embedding"] = SagemakerEndpointVectorOrCross(
        prompt=zh_query_relevance_embedding_prompt,
        endpoint_name=zh_embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    parsed_query["en_query_similarity_embedding"] = SagemakerEndpointVectorOrCross(
        prompt=en_query_similarity_embedding_prompt,
        endpoint_name=en_embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    parsed_query["en_query_relevance_embedding"] = SagemakerEndpointVectorOrCross(
        prompt=en_query_relevance_embedding_prompt,
        endpoint_name=en_embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    elpase_time = time.time() - start
    logger.info(f"runing time of parse query: {elpase_time}s seconds")
    return parsed_query


def q_q_match(parsed_query, debug_info):
    start = time.time()
    opensearch_knn_results = []
    opensearch_knn_response = aos_client.search(
        index_name=aos_faq_index,
        query_type="knn",
        query_term=parsed_query["zh_query_similarity_embedding"],
        field="embedding",
        size=2,
    )
    opensearch_knn_results.extend(
        organize_faq_results(opensearch_knn_response, aos_faq_index)
    )
    opensearch_knn_response = aos_client.search(
        index_name=aos_faq_index,
        query_type="knn",
        query_term=parsed_query["en_query_similarity_embedding"],
        field="embedding",
        size=2,
    )
    opensearch_knn_results.extend(
        organize_faq_results(opensearch_knn_response, aos_faq_index)
    )
    # logger.info(json.dumps(opensearch_knn_response, ensure_ascii=False))
    elpase_time = time.time() - start
    logger.info(f"runing time of opensearch_knn : {elpase_time}s seconds")
    answer = None
    sources = None
    if len(opensearch_knn_results) > 0:
        debug_info["q_q_match_info"] = remove_redundancy_debug_info(
            opensearch_knn_results[:3]
        )
        if opensearch_knn_results[0]["score"] >= 0.9:
            source = opensearch_knn_results[0]["source"]
            answer = opensearch_knn_results[0]["answer"]
            sources = [source]
            return answer, sources
    return answer, sources


def get_relevant_documents_dgr(
    parsed_query,
    rerank_model_endpoint: str,
    aos_faq_index: str,
    aos_ug_index: str,
    debug_info,
):
    # 1. get AOS knn recall
    faq_result_num = 2
    ug_result_num = 20
    start = time.time()
    opensearch_knn_results = []
    opensearch_knn_response = aos_client.search(
        index_name=aos_faq_index,
        query_type="knn",
        query_term=parsed_query["zh_query_relevance_embedding"],
        field="embedding",
        size=faq_result_num,
    )
    opensearch_knn_results.extend(
        organize_faq_results(opensearch_knn_response, aos_faq_index)[:faq_result_num]
    )
    opensearch_knn_response = aos_client.search(
        index_name=aos_faq_index,
        query_type="knn",
        query_term=parsed_query["en_query_relevance_embedding"],
        field="embedding",
        size=faq_result_num,
    )
    opensearch_knn_results.extend(
        organize_faq_results(opensearch_knn_response, aos_faq_index)[:faq_result_num]
    )
    # logger.info(json.dumps(opensearch_knn_response, ensure_ascii=False))
    faq_recall_end_time = time.time()
    elpase_time = faq_recall_end_time - start
    logger.info(f"runing time of faq recall : {elpase_time}s seconds")
    filter = None
    if parsed_query["is_api_query"]:
        filter = [{"term": {"metadata.is_api": True}}]

    opensearch_knn_response = aos_client.search(
        index_name=aos_ug_index,
        query_type="knn",
        query_term=parsed_query["zh_query_relevance_embedding"],
        field="embedding",
        filter=filter,
        size=ug_result_num,
    )
    opensearch_knn_results.extend(
        organize_ug_results(opensearch_knn_response, aos_ug_index)[:ug_result_num]
    )
    opensearch_knn_response = aos_client.search(
        index_name=aos_ug_index,
        query_type="knn",
        query_term=parsed_query["en_query_relevance_embedding"],
        field="embedding",
        filter=filter,
        size=ug_result_num,
    )
    opensearch_knn_results.extend(
        organize_ug_results(opensearch_knn_response, aos_ug_index)[:ug_result_num]
    )

    debug_info["knowledge_qa_knn_recall"] = remove_redundancy_debug_info(
        opensearch_knn_results
    )
    ug_recall_end_time = time.time()
    elpase_time = ug_recall_end_time - faq_recall_end_time
    logger.info(f"runing time of ug recall: {elpase_time}s seconds")

    # 2. get AOS invertedIndex recall
    opensearch_query_results = []

    # 3. combine these two opensearch_knn_response and opensearch_query_response
    recall_knowledge = combine_recalls(opensearch_knn_results, opensearch_query_results)

    rerank_pair = []
    for knowledge in recall_knowledge:
        # rerank_pair.append([parsed_query["query"], knowledge["content"]][:1024])
        rerank_pair.append(
            [parsed_query["en_query"], knowledge["content"]][: 1024 * 10]
        )
    en_score_list = json.loads(
        SagemakerEndpointVectorOrCross(
            prompt=json.dumps(rerank_pair),
            endpoint_name=rerank_model_endpoint,
            region_name=region,
            model_type="rerank",
            stop=None,
        )
    )
    rerank_pair = []
    for knowledge in recall_knowledge:
        # rerank_pair.append([parsed_query["query"], knowledge["content"]][:1024])
        rerank_pair.append(
            [parsed_query["zh_query"], knowledge["content"]][: 1024 * 10]
        )
    zh_score_list = json.loads(
        SagemakerEndpointVectorOrCross(
            prompt=json.dumps(rerank_pair),
            endpoint_name=rerank_model_endpoint,
            region_name=region,
            model_type="rerank",
            stop=None,
        )
    )
    rerank_knowledge = []
    for knowledge, score in zip(recall_knowledge, zh_score_list):
        # if score > 0:
        new_knowledge = knowledge.copy()
        new_knowledge["rerank_score"] = score
        rerank_knowledge.append(new_knowledge)
    for knowledge, score in zip(recall_knowledge, en_score_list):
        # if score > 0:
        new_knowledge = knowledge.copy()
        new_knowledge["rerank_score"] = score
        rerank_knowledge.append(new_knowledge)
    rerank_knowledge.sort(key=lambda x: x["rerank_score"], reverse=True)
    debug_info["knowledge_qa_rerank"] = rerank_knowledge

    rerank_end_time = time.time()
    elpase_time = rerank_end_time - ug_recall_end_time
    logger.info(f"runing time of rerank: {elpase_time}s seconds")

    return rerank_knowledge


def dgr_entry(
    session_id: str,
    query_input: str,
    history: list,
    zh_embedding_model_endpoint: str,
    en_embedding_model_endpoint: str,
    cross_model_endpoint: str,
    rerank_model_endpoint: str,
    llm_model_endpoint: str,
    aos_faq_index: str,
    aos_ug_index: str,
    enable_knowledge_qa: bool,
    temperature: float,
    enable_q_q_match: bool,
    llm_model_id=None,
    stream=False,
):
    """
    Entry point for the Lambda function.

    :param session_id: The ID of the session.
    :param query_input: The query input.
    :param history: The history of the conversation.
    :param embedding_model_endpoint: The endpoint of the embedding model.
    :param cross_model_endpoint: The endpoint of the cross model.
    :param llm_model_endpoint: The endpoint of the language model.
    :param llm_model_name: The name of the language model.
    :param aos_faq_index: The faq index of the AOS engine.
    :param aos_ug_index: The ug index of the AOS engine.
    :param enable_knowledge_qa: Whether to enable knowledge QA.
    :param temperature: The temperature of the language model.
    :param stream(Bool): Whether to use llm stream decoding output.

    return: answer(str)
    """
    debug_info = {
        "query": query_input,
        "query_parser_info": {},
        "q_q_match_info": {},
        "knowledge_qa_knn_recall": {},
        "knowledge_qa_boolean_recall": {},
        "knowledge_qa_combined_recall": {},
        "knowledge_qa_cross_model_sort": {},
        "knowledge_qa_llm": {},
        "knowledge_qa_rerank": {},
    }
    contexts = []
    sources = []
    answer = ""
    try:
        # 1. parse query
        parsed_query = parse_query(
            query_input,
            history,
            zh_embedding_model_endpoint,
            en_embedding_model_endpoint,
            debug_info,
        )
        # 2. query question match
        if enable_q_q_match:
            answer, sources = q_q_match(parsed_query, debug_info)
            if answer and sources:
                return answer, sources, contexts, debug_info
        # 3. recall and rerank
        knowledges = get_relevant_documents_dgr(
            parsed_query,
            rerank_model_endpoint,
            aos_faq_index,
            aos_ug_index,
            debug_info,
        )
        context_num = 6
        sources = list(set([item["source"] for item in knowledges[:context_num]]))
        contexts = knowledges[:context_num]
        # 4. generate answer using question and recall_knowledge
        parameters = {"temperature": temperature}
        generate_input = dict(
            model_id=llm_model_id,
            query=query_input,
            contexts=knowledges[:context_num],
            history=history,
            region_name=region,
            model_kwargs=parameters,
            context_num=context_num,
            model_type="answer",
            llm_model_endpoint=llm_model_endpoint,
            stream=stream,
        )

        llm_start_time = time.time()
        llm_chain = get_rag_llm_chain(**generate_input)
        llm_chain.invoke()

        answer = llm_generate(**generate_input)
        llm_end_time = time.time()
        elpase_time = llm_end_time - llm_start_time
        logger.info(f"runing time of llm: {elpase_time}s seconds")
        # answer = ret["answer"]
        debug_info["knowledge_qa_llm"] = answer
    except Exception as e:
        logger.info(f"Exception Query: {query_input}")
        logger.info(f"{traceback.format_exc()}")
        answer = ""

    # 5. update_session
    # start = time.time()
    # update_session(session_id=session_id, chat_session_table=chat_session_table,
    #                question=query_input, answer=answer, knowledge_sources=sources)
    # elpase_time = time.time() - start
    # logger.info(f'runing time of update_session : {elpase_time}s seconds')

    return answer, sources, contexts, debug_info


def get_strict_qq_chain(strict_q_q_index):
    def get_strict_qq_result(docs, threshold=0.7):
        results = []
        for doc in docs:
            results.append(
                {
                    "score": doc.metadata["score"],
                    "source": doc.metadata["source"],
                    "answer": doc.metadata["answer"],
                    "question": doc.metadata["question"],
                }
            )
        output = {
            "answer": json.dumps(results, ensure_ascii=False),
            "sources": [],
            "contexts": [],
        }
        return output

    mkt_q_q_retriever = QueryQuestionRetriever(
        index=strict_q_q_index,
        vector_field="vector_field",
        source_field="file_path",
        size=5,
    )
    strict_q_q_chain = mkt_q_q_retriever | RunnableLambda(get_strict_qq_result)
    return strict_q_q_chain


def return_strict_qq_result(x):
    # def get_strict_qq_result(docs, threshold=0.7):
    #     results = []
    #     for doc in docs:
    #         results.append({"score": doc.metadata["score"],
    #                         "source": doc.metadata["source"],
    #                         "answer": doc.metadata["answer"],
    #                         "question": doc.metadata["question"]})
    #     output = {"answer": json.dumps(results, ensure_ascii=False), "sources": [], "contexts": []}
    #     return output
    # return get_strict_qq_result(x["intent_info"]["strict_qq_intent_result"])
    return {
        "answer": json.dumps(
            x["intent_info"]["strict_qq_intent_result"], ensure_ascii=False
        ),
        "sources": [],
        "contexts": [],
    }


def get_rag_llm_chain(llm_model_id, stream, model_kwargs=None):
    def contexts_trunc(docs: list, context_num=2):
        docs = [doc for doc in docs[:context_num]]
        # filter same docs
        s = set()
        context_strs = []
        context_docs = []
        context_sources = []

        for doc in docs:
            content = doc.page_content
            if content not in s:
                context_strs.append(content)
                s.add(content)
                context_docs.append({
                    "doc": content,
                    "source": doc.metadata["source"],
                    # "score": doc.metadata["score"]
                    })
                context_sources.append(doc.metadata["source"])
        return {
            "contexts": context_strs,
            "context_docs": context_docs,
            "context_sources":context_sources
        }
    
    # TODO opt with efficiency
    contexts_trunc_stage = RunnablePassthrough.assign(
        contexts=lambda x: contexts_trunc(x["docs"], context_num=5)['contexts'],
        context_docs=lambda x: contexts_trunc(x["docs"], context_num=5)['context_docs'],
        context_sources=lambda x: contexts_trunc(x["docs"], context_num=5)['context_sources'],
    )
 
    llm_chain = get_llm_chain(
        model_id=llm_model_id,
        intent_type=IntentType.KNOWLEDGE_QA.value,
        model_kwargs=model_kwargs,  # TODO
        stream=stream,
    )
    llm_chain = contexts_trunc_stage | RunnablePassthrough.assign(answer=llm_chain)
    return llm_chain


def get_qd_llm_chain(
    aos_index_list, llm_model_id, stream=False, top_n=5, using_whole_doc=True
):
    retriever_list = [
        QueryDocumentRetriever(
            index, "vector_field", "text", "file_path", using_whole_doc
        )
        for index in aos_index_list
    ]
    lotr = MergerRetriever(retrievers=retriever_list)
    compressor = BGEReranker(top_n=top_n)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )

    # def format_docs(docs, top_k=2):
    #     # return "\n\n".join(doc.page_content for doc in docs["docs"][:top_k])
    #     return [doc.page_content for doc in docs["docs"][:top_k]]

    # def format_sources(docs, top_k=2):
    #     return [doc.metadata["source"] for doc in docs["docs"][:top_k]]

    llm_chain = get_rag_llm_chain(llm_model_id, stream)
    qd_llm_chain = RunnableParallel(
        {
            "docs": compression_retriever,
            "query": lambda x: x["query"],
            "debug_info": lambda x: x["debug_info"],
        }
    ) |  llm_chain
    
    
    # RunnableParallel(
    #     {
    #         "answer": llm_chain,
    #         # "contexts": format_docs,
    #         # "sources": format_sources,
    #         "debug_info": lambda x: x["debug_info"],
    #     }
    # )
    return qd_llm_chain


def get_qq_result(docs, threshold=0.7):
    if len(docs) > 0 and docs[0]["score"]:
        source = docs[0]["source"]
        answer = docs[0]["answer"]
        sources = [source]
        return answer, sources
    else:
        return None, []


def output_postprocess(raw_output):
    output = {"answer": "", "sources": [], "contexts": []}
    if raw_output is not None:
        output["answer"] = raw_output.get("answer", "")
        output["sources"] = raw_output.get("sources", [])
        output["contexts"] = raw_output.get("contexts", [])
    return output


def market_chain_entry(
    query_input: str,
    llm_model_id=None,
    stream=False,
    intent_type=IntentType.KNOWLEDGE_QA,
    manual_input_intent=None,
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.
    :param stream(Bool): Whether to use llm stream decoding output.
    return: answer(str)
    """
    aos_index_dict = json.loads(
        os.environ.get(
            "aos_index_dict",
            '{"aos_index_mkt_qd":"aws-cn-mkt-knowledge","aos_index_mkt_qq":"gcr-mkt-qq","aos_index_dgr_qd":"ug-index","aos_index_dgr_qq":"faq-index-2"}',
        )
    )
    aos_index_mkt_qd = aos_index_dict["aos_index_mkt_qd"]
    aos_index_mkt_qq = aos_index_dict["aos_index_mkt_qq"]
    aos_index_dgr_qd = aos_index_dict["aos_index_dgr_qd"]
    aos_index_dgr_faq_qd = aos_index_dict["aos_index_dgr_faq_qd"]
    aos_index_dgr_qq = aos_index_dict["aos_index_dgr_qq"]

    debug_info = {
        "query": query_input,
        "query_parser_info": {},
        "q_q_match_info": {},
        "knowledge_qa_knn_recall": {},
        "knowledge_qa_boolean_recall": {},
        "knowledge_qa_combined_recall": {},
        "knowledge_qa_cross_model_sort": {},
        "knowledge_qa_llm": {},
        "knowledge_qa_rerank": {},
    }
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
    dgr_q_q_retriever = QueryQuestionRetriever(
        index=aos_index_dgr_qq,
        vector_field="vector_field",
        source_field="source",
        size=5,
    )
    # 2.2 query document retrieval + LLM.
    qd_llm_chain = get_qd_llm_chain(
        [aos_index_dgr_qd, aos_index_dgr_faq_qd, aos_index_mkt_qd],
        llm_model_id,
        stream,
        top_n=5,
    )

    # 2.3 query question router.
    def qq_route(info, threshold=0.9):
        for doc in info["docs"]:
            if doc.metadata["score"] > threshold:
                output = {
                    "answer": doc.metadata["answer"],
                    "sources": doc.metadata["source"],
                    "contexts": [],
                    "debug_info": lambda x: x["debug_info"],
                }
                return output
        return qd_llm_chain

    qq_chain = dgr_q_q_retriever
    qq_qd_llm_chain = RunnableParallel(
        {
            "docs": qq_chain,
            "query": lambda x: x["query"],
            "debug_info": lambda x: x["debug_info"],
        }
    ) | RunnableLambda(qq_route)

    # TODO design chat chain
    chat_llm_chain = get_llm_chain(
        model_id=llm_model_id,
        intent_type=IntentType.CHAT.value,
        model_kwargs=None,  # TODO
        stream=stream,
    ) | {
        "answer": lambda x: x,
        "sources": lambda x: [],
        "contexts": lambda x: [],
        "intent_type": lambda x: IntentType.CHAT.value,
    }
    
    # query expansion
    query_expansion_chain = RunnablePassthrough.assign(
        query_expansions=get_query_expansion_chain(
            llm_model_id=llm_model_id
        )
    ) | add_key_to_debug(add_key='query_expansions',debug_key="debug_info")

    # intent recognition
    intent_recognition_chain = RunnablePassthrough.assign(
        intent_type=auto_intention_recoginition_chain(aos_index_mkt_qq)
    )
   
    full_chain = query_expansion_chain | intent_recognition_chain  | RunnableBranch(
        (lambda x:x['intent_type'] == IntentType.KNOWLEDGE_QA.value, qq_qd_llm_chain),
        (lambda x:x['intent_type'] == IntentType.STRICT_QQ.value, return_strict_qq_result),
        # (lambda x:x['intent_type'] == IntentType.STRICT_QQ.value, strict_q_q_chain),
        chat_llm_chain,  # chat
    )
    # full_chain = intent_recognition_chain
    # full_chain = RunnableLambda(route)
    response = full_chain.invoke(
        {
            "query": query_input,
            "debug_info": debug_info,
            "intent_type": intent_type,
            "intent_info": intent_info,
        }
    )

    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]

    return answer, sources, contexts, debug_info


def main_chain_entry(
    query_input: str,
    aos_index: str,
    llm_model_id=None,
    stream=False,
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.

    return: answer(str)
    """
    debug_info = {
        "query": query_input,
        "query_parser_info": {},
        "q_q_match_info": {},
        "knowledge_qa_knn_recall": {},
        "knowledge_qa_boolean_recall": {},
        "knowledge_qa_combined_recall": {},
        "knowledge_qa_cross_model_sort": {},
        "knowledge_qa_llm": {},
        "knowledge_qa_rerank": {},
    }
    contexts = []
    sources = []
    answer = ""
    full_chain = get_qd_llm_chain(
        [aos_index], llm_model_id, stream, using_whole_doc=False
    )
    response = full_chain.invoke({"query": query_input, "debug_info": debug_info})
    answer = response["answer"]
    sources = response["sources"]
    contexts = response["contexts"]
    return answer, sources, contexts, debug_info


def _is_websocket_request(event):
    """Check if the request is WebSocket or Restful

    Args:
        event: lambda request event
    """
    if (
        "requestContext" in event
        and "eventType" in event["requestContext"]
        and event["requestContext"]["eventType"] == "MESSAGE"
    ):
        return True
    else:
        return False


# @handle_error
def lambda_handler(event, context):
    request_timestamp = time.time()
    logger.info(f"request_timestamp :{request_timestamp}")
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")
    if "Records" not in event:
        # Restful API invocation
        event["Records"] = [{"body": json.dumps(event)}]
    for record in event["Records"]:
        record_event = json.loads(record["body"])
        # Get request body
        event_body = json.loads(record_event["body"])
        model = event_body["model"]
        session_id = event_body.get("session_id", "N/A")
        messages = event_body["messages"]
        temperature = event_body["temperature"]
        stream = _is_websocket_request(record_event)
        if stream:
            load_ws_client()

        logger.info(f"stream decode: {stream}")
        biz_type = event_body.get("type", Type.COMMON.value)
        enable_q_q_match = event_body.get("enable_q_q_match", False)
        enable_debug = event_body.get("enable_debug", False)

        retrieval_only = event_body.get("enable_debug", False)
        get_contexts = event_body.get("get_contexts", False)
        intent_type = (
            event_body.get("intent", None)
            or event_body.get("model", None)
            or IntentType.KNOWLEDGE_QA.value
        )
        llm_model_id = event_body.get("llm_model_id", "anthropic.claude-v2:1")
        # stream = event_body.get("stream", False)

        history, question = process_input_messages(messages)
        role = "user"

        if not session_id:
            if stream:
                session_id = record_event["requestContext"]["connectionId"]
            else:
                session_id = f"session_{int(request_timestamp)}"
        user_id = event_body.get("user_id", "default_user_id")
        message_id = str(uuid.uuid4())
        chat_history = DynamoDBChatMessageHistory(
            table_name=chat_session_table,
            session_id=session_id,
            user_id=user_id,
        )
        chat_history.add_user_message(f"user_{message_id}", question)

        knowledge_qa_flag = True if model == "knowledge_qa" else False

        main_entry_start = time.time()
        contexts = []
        if biz_type.lower() == Type.COMMON.value:
            answer, sources, contexts, debug_info = main_chain_entry(
                question,
                aos_index,
                stream=stream,
                llm_model_id=llm_model_id,
            )
        elif biz_type.lower() == Type.DGR.value:
            answer, sources, contexts, debug_info = dgr_entry(
                session_id,
                question,
                history,
                zh_embedding_endpoint,
                en_embedding_endpoint,
                cross_endpoint,
                rerank_endpoint,
                llm_endpoint,
                aos_faq_index,
                aos_ug_index,
                knowledge_qa_flag,
                temperature,
                enable_q_q_match,
                stream=stream,
            )
        elif biz_type.lower() == Type.MARKET_CHAIN.value:
            answer, sources, contexts, debug_info = market_chain_entry(
                question,
                stream=stream,
                llm_model_id=llm_model_id,
                intent_type=intent_type,
            )

        main_entry_elpase = time.time() - main_entry_start
        logger.info(f"runing time of {biz_type} entry : {main_entry_elpase}s seconds")
        
        if not stream:
            return process_response(
                **dict(
                    stream=stream,
                    session_id=session_id,
                    model=model,
                    request_timestamp=request_timestamp,
                    answer=answer,
                    sources=sources,
                    get_contexts=get_contexts,
                    contexts=contexts,
                    enable_debug=enable_debug,
                    debug_info=debug_info,
                    ws_client=ws_client,
                    chat_history=chat_history,
                    message_id=message_id,
                )
            )
        process_response(
            **dict(
                stream=stream,
                session_id=session_id,
                model=model,
                request_timestamp=request_timestamp,
                answer=answer,
                sources=sources,
                get_contexts=get_contexts,
                contexts=contexts,
                enable_debug=enable_debug,
                debug_info=debug_info,
                ws_client=ws_client,
                chat_history=chat_history,
                message_id=message_id,
            )
        )

    return {"statusCode": 200, "body": "All records have been processed"}
