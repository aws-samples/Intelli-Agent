import time
import os
import logging
import json
import copy
import traceback 
import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional 

from langchain.schema.retriever import BaseRetriever
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.docstore.document import Document

from time_utils import timeit
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
logger.setLevel(logging.INFO)

region = os.environ["AWS_REGION"]
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

def parse_qq_query(
    query_input: str,
    history: list,
    zh_embedding_model_endpoint: str,
    en_embedding_model_endpoint: str,
    debug_info: dict,
):
    # print('query_input',query_input)
    start = time.time()
    # concatenate query_input and history to unified prompt
    query_knowledge = "".join([query_input] + [row[0] for row in history][::-1])

    # get query embedding
    parsed_query = run_preprocess(query_knowledge)
    # print('run_preprocess time: ',time.time()-start)
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
    parsed_query["filter"] = []
    if parsed_query["is_api_query"]:
        parsed_query["filter"].append({"term": {"metadata.is_api": True}})
    elpase_time = time.time() - start
    logger.info(f"runing time of parse query: {elpase_time}s seconds")
    return parsed_query

@timeit
def get_similarity_embedding(
    query: str,
    embedding_model_endpoint: str,
):
    query_similarity_embedding_prompt = query
    query_embedding = SagemakerEndpointVectorOrCross(
        prompt=query_similarity_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    return query_embedding

@timeit
def get_relevance_embedding(
    query: str,
    query_lang: str,
    embedding_model_endpoint: str,
):
    if query_lang == "zh":
        query_relevance_embedding_prompt = (
            "为这个句子生成表示以用于检索相关文章：" + query
        )
    elif query_lang == "en":
        query_relevance_embedding_prompt = (
            "Represent this sentence for searching relevant passages: "
            + query
        )
    query_embedding = SagemakerEndpointVectorOrCross(
        prompt=query_relevance_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        region_name=region,
        model_type="vector",
        stop=None,
    )
    return query_embedding

def get_filter_list(parsed_query: dict):
    filter_list = []
    if parsed_query["is_api_query"]:
        filter_list.append({"term": {"metadata.is_api": True}})
    return filter_list



def get_faq_answer(source, index_name, source_field):
    opensearch_query_response = aos_client.search(
        index_name=index_name,
        query_type="basic",
        query_term=source,
        field=f"metadata.{source_field}",
    )
    for r in opensearch_query_response["hits"]["hits"]:
        if "field" in r["_source"]["metadata"] and "answer" == r["_source"]["metadata"]["field"]:
            return r["_source"]["content"]
        elif "jsonlAnswer" in r["_source"]["metadata"]:
            return r["_source"]["metadata"]["jsonlAnswer"]["answer"]
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

def get_doc(file_path, index_name):
    opensearch_query_response = aos_client.search(
        index_name=index_name,
        query_type="basic",
        query_term=file_path,
        field="metadata.file_path",
        size=100,
    )
    chunk_list = []
    chunk_id_set = set()
    for r in opensearch_query_response["hits"]["hits"]:
        if "chunk_id" not in r["_source"]["metadata"] or not r["_source"]["metadata"]["chunk_id"].startswith("$"):
            continue
        chunk_id = r["_source"]["metadata"]["chunk_id"]
        content_type = r["_source"]["metadata"]["content_type"]
        chunk_group_id = int(chunk_id.split("-")[0].strip("$"))
        chunk_section_id = int(chunk_id.split("-")[-1])
        if (chunk_id, content_type) in chunk_id_set:
            continue
        chunk_id_set.add((chunk_id, content_type))
        chunk_list.append((chunk_id, chunk_group_id, content_type, chunk_section_id, r["_source"]["text"]))
    sorted_chunk_list = sorted(chunk_list, key=lambda x: (x[1], x[2], x[3]))
    chunk_text_list = [x[4] for x in sorted_chunk_list]
    return "\n".join(chunk_text_list)

def get_context(previous_chunk_id, next_chunk_id, index_name, window_size):
    previous_content_list = []
    previous_pos = 0
    next_pos = 0
    while previous_chunk_id and previous_chunk_id.startswith("$") and previous_pos < window_size:
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=previous_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            previous_chunk_id = r["_source"]["metadata"]["heading_hierarchy"]["previous"]
            previous_content_list.insert(0, r["_source"]["text"])
            previous_pos += 1
        else:
            break
    next_content_list = []
    while next_chunk_id and next_chunk_id.startswith("$") and next_pos < window_size:
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=next_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            next_chunk_id = r["_source"]["metadata"]["heading_hierarchy"]["next"]
            next_content_list.append(r["_source"]["text"])
            next_pos += 1
        else:
            break
    return [previous_content_list, next_content_list]

def get_parent_content(previous_chunk_id, next_chunk_id, index_name):
    previous_content_list = []
    while previous_chunk_id.startswith("$"):
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=previous_chunk_id,
            field="metadata.chunk_id",
            size=10,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            previous_chunk_id = r["_source"]["metadata"]["chunk_id"]
            previous_content_list.append(r["_source"]["text"])
        else:
            break
    next_content_list = []
    while next_chunk_id.startswith("$"):
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=next_chunk_id,
            field="metadata.chunk_id",
            size=10,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            next_chunk_id = r["_source"]["metadata"]["chunk_id"]
            next_content_list.append(r["_source"]["text"])
        else:
            break
    return [previous_content_list, next_content_list]

def organize_faq_results(response, index_name, source_field="file_path", text_field="text"):
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
            result["score"] = aos_hit["_score"]
            result["detail"] = aos_hit["_source"]
            if "field" in aos_hit["_source"]["metadata"]:
                result["answer"] = get_faq_answer(result["source"], index_name, source_field)
                result["content"] = aos_hit["_source"]["content"]
                result["question"] = aos_hit["_source"]["content"]
                result[source_field] = aos_hit["_source"]["metadata"][source_field]
            elif "jsonlAnswer" in aos_hit["_source"]["metadata"]:
                result["answer"] = aos_hit["_source"]["metadata"]["jsonlAnswer"]["answer"]
                result["question"] = aos_hit["_source"]["metadata"]["jsonlAnswer"]["question"]
                result["content"] = aos_hit["_source"]["text"]
                if source_field in aos_hit["_source"]["metadata"]["jsonlAnswer"].keys():
                    result[source_field] = aos_hit["_source"]["metadata"]["jsonlAnswer"][source_field]
                else:
                    result[source_field] = aos_hit["_source"]["metadata"][source_field]
            # result["doc"] = get_faq_content(result["source"], index_name)
        except:
            logger.info("index_error")
            logger.info(traceback.format_exc())
            logger.info(aos_hit["_source"])
            continue
        # result.update(aos_hit["_source"])
        results.append(result)
    return results

class QueryQuestionRetriever(BaseRetriever):
    index: Any
    vector_field: Any
    source_field: Any
    size: Any
    lang: Any
    embedding_model_endpoint: Any

    def __init__(self, index: str, vector_field: str, source_field: str,
                 size: float, lang: str, embedding_model_endpoint: str):
        super().__init__()
        self.index = index
        self.vector_field = vector_field
        self.source_field = source_field
        self.size = size
        self.lang = lang
        self.embedding_model_endpoint = embedding_model_endpoint

    @timeit
    def _get_relevant_documents(self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        query = question["query"] 
        debug_info = question["debug_info"]
        start = time.time()
        opensearch_knn_results = []
        query_embedding = get_similarity_embedding(query, self.embedding_model_endpoint)
        opensearch_knn_response = aos_client.search(
            index_name=self.index,
            query_type="knn",
            query_term=query_embedding,
            field=self.vector_field,
            size=self.size,
        )
        opensearch_knn_results.extend(
            organize_faq_results(opensearch_knn_response, self.index, self.source_field)
        )
        debug_info[f"q_q_match_info_{self.index}"] = remove_redundancy_debug_info(opensearch_knn_results)
        docs = []
        for result in opensearch_knn_results:
            docs.append(Document(page_content=result["content"], metadata={
                "source": result[self.source_field], "score":result["score"],
                "answer": result["answer"], "question": result["question"]}))
        return docs

class QueryDocumentRetriever(BaseRetriever):
    index: Any
    vector_field: Any
    text_field: Any
    source_field: Any
    using_whole_doc: Any
    context_num: Any
    top_k: Any
    lang: Any
    embedding_model_endpoint: Any

    def __init__(self, index, vector_field, text_field,  source_field, using_whole_doc,
                 context_num, top_k, lang, embedding_model_endpoint):
        super().__init__()
        self.index = index
        self.vector_field = vector_field
        self.text_field = text_field
        self.source_field = source_field
        self.using_whole_doc = using_whole_doc
        self.context_num = context_num
        self.top_k = top_k
        self.lang = lang
        self.embedding_model_endpoint = embedding_model_endpoint

    async def __ainvoke_get_context(self, previous_chunk_id, next_chunk_id, window_size, loop):
        return await loop.run_in_executor(None,
                                          get_context,
                                          previous_chunk_id,
                                          next_chunk_id,
                                          self.index,
                                          window_size)

    async def __spawn_task(self, aos_hits, context_size):
        loop = asyncio.get_event_loop()
        task_list = []
        for aos_hit in aos_hits:
            if context_size and ("heading_hierarchy" in aos_hit['_source']["metadata"] and 
                                    "previous" in aos_hit['_source']["metadata"]["heading_hierarchy"] and
                                    "next" in aos_hit['_source']["metadata"]["heading_hierarchy"]):
                    task = asyncio.create_task(
                        self.__ainvoke_get_context(
                            aos_hit['_source']["metadata"]["heading_hierarchy"]["previous"],
                            aos_hit['_source']["metadata"]["heading_hierarchy"]["next"],
                            context_size,
                            loop))
                    task_list.append(task)
        return await asyncio.gather(*task_list)

    @timeit
    def organize_results(self, response, aos_index=None, source_field="file_path", text_field="text", using_whole_doc=True, context_size=0):
        """
        Organize results from aos response

        :param query_type: query type
        :param response: aos response json
        """
        results = []
        if not response:
            return results
        aos_hits = response["hits"]["hits"]
        if len(aos_hits) == 0:
            return results
        for aos_hit in aos_hits:
            result = {}
            result["source"] = aos_hit['_source']['metadata'][source_field]
            result["score"] = aos_hit["_score"]
            result["detail"] = aos_hit['_source']
            # result["content"] = aos_hit['_source'][text_field]
            result["content"] = aos_hit['_source'][text_field]
            result["doc"] = result["content"]
            results.append(result)
        if using_whole_doc:
            for result in results:
                doc = get_doc(result["source"], aos_index)
                if doc:
                    result["doc"] = doc
        else:
            response_list = asyncio.run(self.__spawn_task(aos_hits, context_size))
            for context, result in zip(response_list, results):
                result["doc"] = "\n".join(context[0] + [result["doc"]] + context[1])
            # context = get_context(aos_hit['_source']["metadata"]["heading_hierarchy"]["previous"],
            #                     aos_hit['_source']["metadata"]["heading_hierarchy"]["next"],
            #                     aos_index,
            #                     context_size)
            # if context:
            #     result["doc"] = "\n".join(context[0] + [result["doc"]] + context[1])
        return results

    @timeit
    def _get_relevant_documents(self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        query = question["query"] 
        debug_info = question["debug_info"]
        opensearch_knn_results = []
        query_embedding = get_relevance_embedding(query, self.lang, self.embedding_model_endpoint)
        filter = get_filter_list(question)
        opensearch_knn_response = aos_client.search(
            index_name=self.index,
            query_type="knn",
            query_term=query_embedding,
            field=self.vector_field,
            size=self.top_k,
            filter=filter
        )
        opensearch_knn_results.extend(
            self.organize_results(opensearch_knn_response, self.index, self.source_field, self.text_field, self.using_whole_doc, self.context_num)[:self.top_k]
        )

       # 2. get AOS invertedIndex recall
        opensearch_query_results = []

        # 3. combine these two opensearch_knn_response and opensearch_query_response
        final_results = opensearch_knn_results + opensearch_query_results
        debug_info[f"knowledge_qa_knn_recall_{self.index}"] = remove_redundancy_debug_info(final_results)

        doc_list = []
        content_set = set()
        for result in final_results:
            if result["doc"] in content_set:
                continue
            content_set.add(result["content"])
            doc_list.append(Document(page_content=result["doc"],
                                     metadata={"source": result["source"],
                                               "retrieval_content": result["content"],
                                               "retrieval_score": result["score"],
                                                # set common score for llm.
                                               "score": result["score"]}))
        return doc_list

class GoogleRetriever(BaseRetriever):
    search: Any
    result_num: Any
    def __init__(self, result_num):
        super().__init__()
        from langchain.tools import Tool
        from langchain.utilities import GoogleSearchAPIWrapper
        self.search = GoogleSearchAPIWrapper()
        self.result_num = result_num

    def _get_relevant_documents(self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        results = self.search.results(question["query"], self.result_num)
        for result in results:
            logger.info(result)

def index_results_format(docs:list, threshold=-1):
    results = []
    for doc in docs:
        if doc.metadata["score"] < threshold:
            continue
        results.append({"score": doc.metadata["score"], 
                        "source": doc.metadata["source"],
                        "answer": doc.metadata["answer"],
                        "question": doc.metadata["question"]})
    # output = {"answer": json.dumps(results, ensure_ascii=False), "sources": [], "contexts": []}
    output = {"answer": results, "sources": [], "contexts": [], "context_docs": [], "context_sources": []}
    return output
