import asyncio
import logging
import os
import traceback
from typing import Any, Dict, List

from common_utils.time_utils import timeit
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.docstore.document import Document
from langchain.schema.retriever import BaseRetriever
from sm_utils import SagemakerEndpointVectorOrCross

from .aos_utils import LLMBotOpenSearchClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# region = os.environ["AWS_REGION"]
zh_embedding_model_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_model_endpoint = os.environ.get("en_embedding_endpoint", "")
aos_endpoint = os.environ.get("aos_endpoint", "")

aos_client = LLMBotOpenSearchClient(aos_endpoint)


def remove_redundancy_debug_info(results):
    # filtered_results = copy.deepcopy(results)
    filtered_results = results
    for result in filtered_results:
        for field in list(result["detail"].keys()):
            if field.endswith("embedding") or field.startswith("vector"):
                del result["detail"][field]
    return filtered_results


@timeit
def get_similarity_embedding(
    query: str,
    embedding_model_endpoint: str,
    target_model: str,
    model_type: str = "vector",
) -> List[List[float]]:
    query_similarity_embedding_prompt = query
    response = SagemakerEndpointVectorOrCross(
        prompt=query_similarity_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        model_type=model_type,
        stop=None,
        region_name=None,
        target_model=target_model,
    )
    return response
    # if model_type in ["vector","m3"]:
    #     response = {"dense_vecs": response}
    # # elif model_type == "m3":
    # #     # response["dense_vecs"] = response["dense_vecs"]
    # #     response = {"dense_vecs": response}
    # return response


@timeit
def get_relevance_embedding(
    query: str,
    query_lang: str,
    embedding_model_endpoint: str,
    target_model: str,
    model_type: str = "vector",
):
    if model_type == "vector":
        if query_lang == "zh":
            query_relevance_embedding_prompt = (
                "为这个句子生成表示以用于检索相关文章：" + query
            )
        elif query_lang == "en":
            query_relevance_embedding_prompt = (
                "Represent this sentence for searching relevant passages: " + query
            )
    elif model_type == "m3" or model_type == "bce":
        query_relevance_embedding_prompt = query
    else:
        raise ValueError(f"invalid embedding model type: {model_type}")
    response = SagemakerEndpointVectorOrCross(
        prompt=query_relevance_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        model_type=model_type,
        region_name=None,
        stop=None,
        target_model=target_model,
    )
    return response
    # if model_type in ["vector",'m3']:
    #     response = {"dense_vecs": response}
    # # elif model_type == "m3":
    # #     response = {"dense_vecs": response}
    #     # response["dense_vecs"] = response["dense_vecs"]
    # return response


def get_filter_list(parsed_query: dict):
    filter_list = []
    if "is_api_query" in parsed_query and parsed_query["is_api_query"]:
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
        if (
            "field" in r["_source"]["metadata"]
            and "answer" == r["_source"]["metadata"]["field"]
        ):
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
        try:
            if "chunk_id" not in r["_source"]["metadata"] or not r["_source"][
                "metadata"
            ]["chunk_id"].startswith("$"):
                continue
            chunk_id = r["_source"]["metadata"]["chunk_id"]
            content_type = r["_source"]["metadata"]["content_type"]
            chunk_group_id = int(chunk_id.split("-")[0].strip("$"))
            chunk_section_id = int(chunk_id.split("-")[-1])
            if (chunk_id, content_type) in chunk_id_set:
                continue
        except Exception as e:
            logger.error(traceback.format_exc())
            continue
        chunk_id_set.add((chunk_id, content_type))
        chunk_list.append(
            (
                chunk_id,
                chunk_group_id,
                content_type,
                chunk_section_id,
                r["_source"]["text"],
            )
        )
    sorted_chunk_list = sorted(chunk_list, key=lambda x: (x[1], x[2], x[3]))
    chunk_text_list = [x[4] for x in sorted_chunk_list]
    return "\n".join(chunk_text_list)


def get_child_context(chunk_id, index_name, window_size):
    next_content_list = []
    previous_content_list = []
    previous_pos = 0
    next_pos = 0
    chunk_id_prefix = "-".join(chunk_id.split("-")[:-1])
    section_id = int(chunk_id.split("-")[-1])
    previous_section_id = section_id
    next_section_id = section_id
    while previous_pos < window_size:
        previous_section_id -= 1
        if previous_section_id < 1:
            break
        previous_chunk_id = f"{chunk_id_prefix}-{previous_section_id}"
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=previous_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            previous_content_list.insert(0, r["_source"]["text"])
            previous_pos += 1
        else:
            break
    while next_pos < window_size:
        next_section_id += 1
        next_chunk_id = f"{chunk_id_prefix}-{next_section_id}"
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=next_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            next_content_list.insert(0, r["_source"]["text"])
            next_pos += 1
        else:
            break
    return [previous_content_list, next_content_list]


def get_sibling_context(chunk_id, index_name, window_size):
    next_content_list = []
    previous_content_list = []
    previous_pos = 0
    next_pos = 0
    chunk_id_prefix = "-".join(chunk_id.split("-")[:-1])
    section_id = int(chunk_id.split("-")[-1])
    previous_section_id = section_id
    next_section_id = section_id
    while previous_pos < window_size:
        previous_section_id -= 1
        if previous_section_id < 1:
            break
        previous_chunk_id = f"{chunk_id_prefix}-{previous_section_id}"
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=previous_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            previous_content_list.insert(0, r["_source"]["text"])
            previous_pos += 1
        else:
            break
    while next_pos < window_size:
        next_section_id += 1
        next_chunk_id = f"{chunk_id_prefix}-{next_section_id}"
        opensearch_query_response = aos_client.search(
            index_name=index_name,
            query_type="basic",
            query_term=next_chunk_id,
            field="metadata.chunk_id",
            size=1,
        )
        if len(opensearch_query_response["hits"]["hits"]) > 0:
            r = opensearch_query_response["hits"]["hits"][0]
            next_content_list.insert(0, r["_source"]["text"])
            next_pos += 1
        else:
            break
    return [previous_content_list, next_content_list]


def get_context(aos_hit, index_name, window_size):
    previous_content_list = []
    next_content_list = []
    if "chunk_id" not in aos_hit["_source"]["metadata"]:
        return previous_content_list, next_content_list
    chunk_id = aos_hit["_source"]["metadata"]["chunk_id"]
    inner_previous_content_list, inner_next_content_list = get_sibling_context(
        chunk_id, index_name, window_size
    )
    if (
        len(inner_previous_content_list) == window_size
        and len(inner_next_content_list) == window_size
    ):
        return inner_previous_content_list, inner_next_content_list

    if "heading_hierarchy" not in aos_hit["_source"]["metadata"]:
        return [previous_content_list, next_content_list]
    if "previous" in aos_hit["_source"]["metadata"]["heading_hierarchy"]:
        previous_chunk_id = aos_hit["_source"]["metadata"]["heading_hierarchy"][
            "previous"
        ]
        previous_pos = 0
        while (
            previous_chunk_id
            and previous_chunk_id.startswith("$")
            and previous_pos < window_size
        ):
            opensearch_query_response = aos_client.search(
                index_name=index_name,
                query_type="basic",
                query_term=previous_chunk_id,
                field="metadata.chunk_id",
                size=1,
            )
            if len(opensearch_query_response["hits"]["hits"]) > 0:
                r = opensearch_query_response["hits"]["hits"][0]
                previous_chunk_id = r["_source"]["metadata"]["heading_hierarchy"][
                    "previous"
                ]
                previous_content_list.insert(0, r["_source"]["text"])
                previous_pos += 1
            else:
                break
    if "next" in aos_hit["_source"]["metadata"]["heading_hierarchy"]:
        next_chunk_id = aos_hit["_source"]["metadata"]["heading_hierarchy"]["next"]
        next_pos = 0
        while (
            next_chunk_id and next_chunk_id.startswith("$") and next_pos < window_size
        ):
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


def organize_faq_results(
    response, index_name, source_field="file_path", text_field="text"
):
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
                result["answer"] = get_faq_answer(
                    result["source"], index_name, source_field
                )
                result["content"] = aos_hit["_source"]["content"]
                result["question"] = aos_hit["_source"]["content"]
                result[source_field] = aos_hit["_source"]["metadata"][source_field]
            elif (
                "jsonlAnswer" in aos_hit["_source"]["metadata"]
                and "answer" in aos_hit["_source"]["metadata"]["jsonlAnswer"]
            ):
                result["answer"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "answer"
                ]
                result["question"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "question"
                ]
                result["content"] = aos_hit["_source"]["text"]
                if source_field in aos_hit["_source"]["metadata"]["jsonlAnswer"].keys():
                    result[source_field] = aos_hit["_source"]["metadata"][
                        "jsonlAnswer"
                    ][source_field]
                else:
                    result[source_field] = aos_hit["_source"]["metadata"]["file_path"]
            else:
                result["answer"] = aos_hit["_source"]["metadata"]
                result["content"] = aos_hit["_source"]["text"]
                result["question"] = aos_hit["_source"]["text"]
                result[source_field] = aos_hit["_source"]["metadata"]["file_path"]
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
    top_k: Any
    lang: Any
    embedding_model_endpoint: Any
    target_model: Any
    model_type: Any
    query_key: str = "query"
    enable_debug: Any

    def __init__(
        self, workspace: Dict, top_k: int, query_key="query", enable_debug=False
    ):
        super().__init__()
        self.index = workspace["open_search_index_name"]
        self.vector_field = "vector_field"
        self.source_field = "source"
        self.top_k = top_k
        self.lang = workspace["languages"][0]
        self.embedding_model_endpoint = workspace["embeddings_model_endpoint"]
        if workspace["embeddings_model_name"].endswith("tar.gz"):
            self.target_model = workspace["embeddings_model_name"]
        else:
            self.target_model = None
        self.model_type = workspace["model_type"]
        self.query_key = query_key
        self.enable_debug = enable_debug

    @timeit
    def _get_relevant_documents(
        self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        query = question[self.query_key]
        debug_info = question["debug_info"]
        opensearch_knn_results = []
        query_repr = get_similarity_embedding(
            query, self.embedding_model_endpoint, self.target_model, self.model_type
        )
        opensearch_knn_response = aos_client.search(
            index_name=self.index,
            query_type="knn",
            query_term=query_repr,
            field=self.vector_field,
            size=self.top_k,
        )
        opensearch_knn_results.extend(
            organize_faq_results(opensearch_knn_response, self.index, self.source_field)
        )
        docs = []
        for result in opensearch_knn_results:
            docs.append(
                Document(
                    page_content=result["content"],
                    metadata={
                        "source": result[self.source_field],
                        "score": result["score"],
                        "retrieval_score": result["score"],
                        "retrieval_content": result["content"],
                        "answer": result["answer"],
                        "question": result["question"],
                    },
                )
            )
        if self.enable_debug:
            debug_info[f"qq-knn-recall-{self.index}-{self.lang}"] = (
                remove_redundancy_debug_info(opensearch_knn_results)
            )
        return docs


class QueryDocumentKNNRetriever(BaseRetriever):
    index: Any
    vector_field: Any
    text_field: Any
    source_field: Any
    using_whole_doc: Any
    context_num: Any
    top_k: Any
    lang: Any
    model_type: Any
    embedding_model_endpoint: Any
    target_model: Any
    query_key: str = "query"
    enable_debug: Any

    def __init__(
        self,
        workspace,
        using_whole_doc,
        context_num,
        top_k,
        query_key="query",
        enable_debug=False,
    ):
        super().__init__()
        self.index = workspace["open_search_index_name"]
        self.vector_field = "vector_field"
        self.source_field = "file_path"
        self.text_field = "text"
        self.lang = workspace["languages"][0]
        self.embedding_model_endpoint = workspace["embeddings_model_endpoint"]
        if workspace["embeddings_model_name"].endswith("tar.gz"):
            self.target_model = workspace["embeddings_model_name"]
        else:
            self.target_model = None
        self.model_type = workspace["model_type"]
        self.using_whole_doc = using_whole_doc
        self.context_num = context_num
        self.top_k = top_k
        self.query_key = query_key
        self.enable_debug = enable_debug

    async def __ainvoke_get_context(self, aos_hit, window_size, loop):
        return await loop.run_in_executor(
            None, get_context, aos_hit, self.index, window_size
        )

    async def __spawn_task(self, aos_hits, context_size):
        loop = asyncio.get_event_loop()
        task_list = []
        for aos_hit in aos_hits:
            if context_size:
                task = asyncio.create_task(
                    self.__ainvoke_get_context(aos_hit, context_size, loop)
                )
                task_list.append(task)
        return await asyncio.gather(*task_list)

    @timeit
    def organize_results(
        self,
        response,
        aos_index=None,
        source_field="file_path",
        text_field="text",
        using_whole_doc=True,
        context_size=0,
    ):
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
            result = {"data": {}}
            source = aos_hit["_source"]["metadata"][source_field]
            result["source"] = source
            result["score"] = aos_hit["_score"]
            result["detail"] = aos_hit["_source"]
            # result["content"] = aos_hit['_source'][text_field]
            result["content"] = aos_hit["_source"][text_field]
            result["doc"] = result["content"]
            if "jsonlAnswer" in aos_hit["_source"]["metadata"]:
                result["question"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "question"
                ]
                result["answer"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "answer"
                ]
            else:
                result["question"] = ""
                result["answer"] = ""
            # if 'additional_vecs' in aos_hit['_source']['metadata'] and \
            #     'colbert_vecs' in aos_hit['_source']['metadata']['additional_vecs']:
            #     result["data"]["colbert"] = aos_hit['_source']['metadata']['additional_vecs']['colbert_vecs']
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
    def __get_knn_results(self, query_term, filter):
        opensearch_knn_response = aos_client.search(
            index_name=self.index,
            query_type="knn",
            query_term=query_term,
            field=self.vector_field,
            size=self.top_k,
            filter=filter,
        )
        opensearch_knn_results = self.organize_results(
            opensearch_knn_response,
            self.index,
            self.source_field,
            self.text_field,
            self.using_whole_doc,
            self.context_num,
        )[: self.top_k]
        return opensearch_knn_results

    @timeit
    def _get_relevant_documents(
        self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        query = question[self.query_key]
        if (
            "query_lang" in question
            and question["query_lang"] != self.lang
            and "translated_text" in question
        ):
            query = question["translated_text"]
        debug_info = question["debug_info"]
        query_repr = get_relevance_embedding(
            query,
            self.lang,
            self.embedding_model_endpoint,
            self.target_model,
            self.model_type,
        )
        # question["colbert"] = query_repr["colbert_vecs"][0]
        filter = get_filter_list(question)
        # 1. get AOS KNN results.
        opensearch_knn_results = self.__get_knn_results(query_repr, filter)
        final_results = opensearch_knn_results
        doc_list = []
        content_set = set()
        for result in final_results:
            if result["doc"] in content_set:
                continue
            content_set.add(result["content"])
            # TODO add jsonlans
            doc_list.append(
                Document(
                    page_content=result["doc"],
                    metadata={
                        "source": result["source"],
                        "retrieval_content": result["content"],
                        "retrieval_data": result["data"],
                        "retrieval_score": result["score"],
                        "knn_score": result["score"],
                        # "jsonlAnswer": result["detail"]["metadata"]["jsonlAnswer"],
                        #
                        # set common score for llm.
                        "score": result["score"],
                        "question": result["question"],
                        "answer": result["answer"],
                    },
                )
            )
        if self.enable_debug:
            debug_info[f"qd-knn-recall-{self.index}-{self.lang}"] = (
                remove_redundancy_debug_info(opensearch_knn_results)
            )
        return doc_list


class QueryDocumentBM25Retriever(BaseRetriever):
    index: Any
    vector_field: Any
    text_field: Any
    source_field: Any
    using_whole_doc: Any
    context_num: Any
    top_k: Any
    lang: Any
    model_type: Any
    query_key: str = "query"
    enable_debug: Any
    config: Dict = {"run_name": "BM25"}

    def __init__(
        self,
        workspace,
        using_whole_doc,
        context_num,
        top_k,
        query_key="query",
        enable_debug=False,
    ):
        super().__init__()
        self.index = workspace["open_search_index_name"]
        self.vector_field = "vector_field"
        self.source_field = "file_path"
        self.text_field = "text"
        self.lang = workspace["languages"][0]
        self.model_type = workspace["model_type"]
        self.using_whole_doc = using_whole_doc
        self.context_num = context_num
        self.top_k = top_k
        self.query_key = query_key
        self.enable_debug = enable_debug

    async def __ainvoke_get_context(self, aos_hit, window_size, loop):
        return await loop.run_in_executor(
            None, get_context, aos_hit, self.index, window_size
        )

    async def __spawn_task(self, aos_hits, context_size):
        loop = asyncio.get_event_loop()
        task_list = []
        for aos_hit in aos_hits:
            if context_size:
                task = asyncio.create_task(
                    self.__ainvoke_get_context(aos_hit, context_size, loop)
                )
                task_list.append(task)
        return await asyncio.gather(*task_list)

    @timeit
    def organize_results(
        self,
        response,
        aos_index=None,
        source_field="file_path",
        text_field="text",
        using_whole_doc=True,
        context_size=0,
    ):
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
            result = {"data": {}}
            source = aos_hit["_source"]["metadata"][source_field]
            source = (
                source.replace(
                    "s3://aws-chatbot-knowledge-base/aws-acts-knowledge/qd/zh_CN/",
                    "https://www.amazonaws.cn/",
                )
                .replace(
                    "s3://aws-chatbot-knowledge-base/aws-acts-knowledge/qd/en_US/",
                    "https://www.amazonaws.cn/en/",
                )
                .replace(
                    "s3://aws-chatbot-knowledge-base/aws-global-site-cn-knowledge/",
                    "https://aws.amazon.com/",
                )
            )
            result["source"] = source
            result["score"] = aos_hit["_score"]
            result["detail"] = aos_hit["_source"]
            # result["content"] = aos_hit['_source'][text_field]
            result["content"] = aos_hit["_source"][text_field]
            result["doc"] = result["content"]
            # if 'additional_vecs' in aos_hit['_source']['metadata'] and \
            #     'colbert_vecs' in aos_hit['_source']['metadata']['additional_vecs']:
            #     result["data"]["colbert"] = aos_hit['_source']['metadata']['additional_vecs']['colbert_vecs']
            if "jsonlAnswer" in aos_hit["_source"]["metadata"]:
                result["question"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "question"
                ]
                result["answer"] = aos_hit["_source"]["metadata"]["jsonlAnswer"][
                    "answer"
                ]
            else:
                result["question"] = ""
                result["answer"] = ""
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
    def __get_bm25_results(self, query_term, filter):
        opensearch_bm25_response = aos_client.search(
            index_name=self.index,
            query_type="fuzzy",
            query_term=query_term,
            field=self.text_field,
            size=self.top_k,
            filter=filter,
        )
        opensearch_bm25_results = self.organize_results(
            opensearch_bm25_response,
            self.index,
            self.source_field,
            self.text_field,
            self.using_whole_doc,
            self.context_num,
        )[: self.top_k]
        return opensearch_bm25_results

    @timeit
    def _get_relevant_documents(
        self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        query = question[self.query_key]
        if (
            "query_lang" in question
            and question["query_lang"] != self.lang
            and "translated_text" in question
        ):
            query = question["translated_text"]
        debug_info = question["debug_info"]
        # query_repr = get_relevance_embedding(query, self.lang, self.embedding_model_endpoint, self.model_type)
        # question["colbert"] = query_repr["colbert_vecs"][0]
        filter = get_filter_list(question)
        opensearch_bm25_results = self.__get_bm25_results(query, filter)
        final_results = opensearch_bm25_results
        doc_list = []
        content_set = set()
        for result in final_results:
            if result["doc"] in content_set:
                continue
            content_set.add(result["content"])
            doc_list.append(
                Document(
                    page_content=result["doc"],
                    metadata={
                        "source": result["source"],
                        "retrieval_content": result["content"],
                        "retrieval_data": result["data"],
                        "retrieval_score": result["score"],
                        "bm25_score": result["score"],
                        # set common score for llm.
                        "score": result["score"],
                        "question": result["question"],
                        "answer": result["answer"],
                    },
                )
            )
        if self.enable_debug:
            debug_info[f"qd-bm25-recall-{self.index}-{self.lang}"] = (
                remove_redundancy_debug_info(opensearch_bm25_results)
            )
        return doc_list


def index_results_format(docs: list, threshold=-1):
    results = []
    for doc in docs:
        if doc.metadata["score"] < threshold:
            continue
        results.append(
            {
                "score": doc.metadata["score"],
                "source": doc.metadata["source"],
                "answer": doc.metadata["answer"],
                "question": doc.metadata["question"],
            }
        )
    # output = {"answer": json.dumps(results, ensure_ascii=False), "sources": [], "contexts": []}
    output = {
        "answer": results,
        "sources": [],
        "contexts": [],
        "context_docs": [],
        "context_sources": [],
    }
    return output
