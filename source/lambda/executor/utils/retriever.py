import time
import os
import logging
import json
import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional 

from langchain.schema.retriever import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.docstore.document import Document


from aos_utils import LLMBotOpenSearchClient

from preprocess_utils import run_preprocess
from sm_utils import SagemakerEndpointVectorOrCross
from llmbot_utils import (
    QueryType,
    combine_recalls,
    concat_recall_knowledge,
    process_input_messages,
)

logger = logging.getLogger()
handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

region = os.environ["AWS_REGION"]
rerank_model_endpoint = os.environ.get("rerank_endpoint", "")
aos_index = os.environ.get("aos_index", "")
aos_faq_index = os.environ.get("aos_faq_index", "")
zh_embedding_model_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_model_endpoint = os.environ.get("en_embedding_endpoint", "")
aos_endpoint = os.environ.get("aos_endpoint", "")

aos_client = LLMBotOpenSearchClient(aos_endpoint)

# debug_info = {
#     "query": "",
#     "query_parser_info": {},
#     "q_q_match_info": {},
#     "knowledge_qa_knn_recall": {},
#     "knowledge_qa_boolean_recall": {},
#     "knowledge_qa_combined_recall": {},
#     "knowledge_qa_cross_model_sort": {},
#     "knowledge_qa_llm": {},
#     "knowledge_qa_rerank": {},
# }

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
            print("index_error")
            print(aos_hit["_source"])
            continue
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
        result["source"] = aos_hit['_source']['metadata']['file_path']
        result["score"] = aos_hit["_score"]
        result["detail"] = aos_hit['_source']
        result["content"] = aos_hit['_source']['text']
        result["doc"] = aos_hit['_source']['text']
        results.append(result)
    return results

class QueryQuestionRetriever(BaseRetriever):
    def _get_relevant_documents(self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        query = question["question"] 
        debug_info = question["debug_info"]
        start = time.time()
        opensearch_knn_results = []
        parsed_query = parse_query(
            query,
            [],
            zh_embedding_model_endpoint,
            en_embedding_model_endpoint,
            debug_info,
        )
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
        return answer, sources, debug_info

class QueryDocumentRetriever(BaseRetriever):
    def _get_relevant_documents(self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        query = question["question"] 
        debug_info = question["debug_info"]
        parsed_query = parse_query(
            query,
            [],
            zh_embedding_model_endpoint,
            en_embedding_model_endpoint,
            debug_info,
        )
        # 1. get AOS knn recall
        result_num = 20
        start = time.time()
        opensearch_knn_results = []
        opensearch_knn_response = aos_client.search(
            index_name=aos_index,
            query_type="knn",
            query_term=parsed_query["zh_query_relevance_embedding"],
            field="vector_field",
            size=result_num,
        )
        opensearch_knn_results.extend(
            organize_results(opensearch_knn_response, aos_index)[:result_num]
        )
        recall_end_time = time.time()
        elpase_time = recall_end_time - start
        logger.info(f"runing time of recall : {elpase_time}s seconds")

        # 2. get AOS invertedIndex recall
        opensearch_query_results = []

        # 3. combine these two opensearch_knn_response and opensearch_query_response
        recall_knowledge = combine_recalls(opensearch_knn_results, opensearch_query_results)

        rerank_pair = []
        rerank_text_length = 1024 * 10
        for knowledge in recall_knowledge:
            # rerank_pair.append([parsed_query["query"], knowledge["content"]][:1024])
            rerank_pair.append(
                [parsed_query["zh_query"], knowledge["content"]][: rerank_text_length]
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
        doc_list = []
        for knowledge, score in zip(recall_knowledge, zh_score_list):
            # if score > 0:
            new_knowledge = knowledge.copy()
            new_knowledge["rerank_score"] = score
            rerank_knowledge.append(new_knowledge)
            doc_list.append(Document(page_content=new_knowledge["content"], metadata={"source": new_knowledge["source"]}))
        debug_info["knowledge_qa_rerank"] = rerank_knowledge

        rerank_end_time = time.time()
        elpase_time = rerank_end_time - recall_end_time
        logger.info(f"runing time of rerank: {elpase_time}s seconds")

        return doc_list