from __future__ import annotations

import copy
import math
import re
import traceback
import uuid
import warnings
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from langchain.schema import Document
from langchain.schema.embeddings import Embeddings
from langchain.schema.vectorstore import VectorStore
from langchain.utils import get_from_dict_or_env
from langchain.vectorstores.utils import maximal_marginal_relevance


IMPORT_OPENSEARCH_PY_ERROR = (
    "Could not import OpenSearch. Please install it with `pip install opensearch-py`."
)
SCRIPT_SCORING_SEARCH = "script_scoring"
PAINLESS_SCRIPTING_SEARCH = "painless_scripting"
MATCH_ALL_QUERY = {"match_all": {}}  # type: Dict


def _import_opensearch() -> Any:
    """Import OpenSearch if available, otherwise raise error."""
    try:
        from opensearchpy import OpenSearch
    except ImportError:
        raise ImportError(IMPORT_OPENSEARCH_PY_ERROR)
    return OpenSearch


def _import_bulk() -> Any:
    """Import bulk if available, otherwise raise error."""
    try:
        from opensearchpy.helpers import bulk
    except ImportError:
        raise ImportError(IMPORT_OPENSEARCH_PY_ERROR)
    return bulk


def _import_not_found_error() -> Any:
    """Import not found error if available, otherwise raise error."""
    try:
        from opensearchpy.exceptions import NotFoundError
    except ImportError:
        raise ImportError(IMPORT_OPENSEARCH_PY_ERROR)
    return NotFoundError


def _get_opensearch_client(opensearch_url: str, **kwargs: Any) -> Any:
    """Get OpenSearch client from the opensearch_url, otherwise raise error."""
    try:
        opensearch = _import_opensearch()
        client = opensearch(opensearch_url, **kwargs)
    except ValueError as e:
        raise ImportError(
            f"OpenSearch client string provided is not in proper format. "
            f"Got error: {e} "
        )
    return client


def _validate_embeddings_and_bulk_size(embeddings_length: int, bulk_size: int) -> None:
    """Validate Embeddings Length and Bulk Size."""
    if embeddings_length == 0:
        raise RuntimeError("Embeddings size is zero")
    if bulk_size < embeddings_length:
        raise RuntimeError(
            f"The embeddings count, {embeddings_length} is more than the "
            f"[bulk_size], {bulk_size}. Increase the value of [bulk_size]."
        )


def _validate_aoss_with_engines(is_aoss: bool, engine: str) -> None:
    """Validate AOSS with the engine."""
    if is_aoss and engine != "nmslib" and engine != "faiss":
        raise ValueError(
            "Amazon OpenSearch Service Serverless only "
            "supports `nmslib` or `faiss` engines"
        )


def _is_aoss_enabled(http_auth: Any) -> bool:
    """Check if the service is http_auth is set as `aoss`."""
    if (
        http_auth is not None
        and hasattr(http_auth, "service")
        and http_auth.service == "aoss"
    ):
        return True
    return False


def _bulk_ingest_embeddings(
    client: Any,
    index_name: str,
    embeddings: List[List[float]],
    texts: Iterable[str],
    metadatas: Optional[List[dict]] = None,
    ids: Optional[List[str]] = None,
    vector_field: str = "vector_field",
    text_field: str = "text",
    mapping: Optional[Dict] = None,
    max_chunk_bytes: Optional[int] = 1 * 1024 * 1024,
    is_aoss: bool = False,
    max_retry_time: int = 3,
) -> List[str]:
    """Bulk Ingest Embeddings into given index."""
    if not mapping:
        mapping = dict()

    bulk = _import_bulk()
    not_found_error = _import_not_found_error()
    requests = []
    return_ids = []
    mapping = mapping

    try:
        client.indices.get(index=index_name)
    except not_found_error:
        client.indices.create(index=index_name, body=mapping)

    for i, text in enumerate(texts):
        metadata = metadatas[i] if metadatas else {}
        _id = ids[i] if ids else str(uuid.uuid4())
        request = {
            "_op_type": "update",
            "_index": index_name,
            "doc": {
                vector_field: embeddings[i],
                text_field: text,
                "metadata": metadata,
            },
            "doc_as_upsert": True,
        }
        if is_aoss:
            request["id"] = _id
        else:
            request["_id"] = _id
        requests.append(request)
        return_ids.append(_id)
    retry_time = 0
    while retry_time < max_retry_time:
        try:
            bulk(client, requests, max_chunk_bytes=max_chunk_bytes)
            break
        except Exception as error:
            traceback.print_exc()
            print(f"retry bulk {retry_time}", error)
            retry_time += 1
    if not is_aoss:
        client.indices.refresh(index=index_name)
    return return_ids


def _bulk_ingest_data(
    client: Any,
    index_name: str,
    data_list: List,
    ids: List,
    mapping: Optional[Dict] = None,
    max_chunk_bytes: Optional[int] = 1 * 1024 * 1024,
    is_aoss: bool = False,
) -> List[str]:
    """Bulk Ingest Embeddings into given index."""
    if not mapping:
        mapping = dict()

    bulk = _import_bulk()
    not_found_error = _import_not_found_error()
    requests = []
    return_ids = []
    mapping = mapping

    try:
        client.indices.get(index=index_name)
    except not_found_error:
        client.indices.create(index=index_name, body=mapping)

    for i, data in enumerate(data_list):
        _id = ids[i] if ids else str(uuid.uuid4())
        request = {
            "_op_type": "index",
            "_index": index_name,
        }
        request.update(data)
        if is_aoss:
            request["id"] = _id
        else:
            request["_id"] = _id
        requests.append(request)
        return_ids.append(_id)
    bulk(client, requests, max_chunk_bytes=max_chunk_bytes)
    if not is_aoss:
        client.indices.refresh(index=index_name)
    return return_ids


def _default_scripting_text_mapping(
    dim: int,
    vector_field: str = "vector_field",
) -> Dict:
    """For Painless Scripting or Script Scoring,the default mapping to create index."""
    return {
        "mappings": {
            "properties": {
                vector_field: {"type": "knn_vector", "dimension": dim},
            }
        }
    }


def _default_text_mapping(
    dim: int,
    engine: str = "nmslib",
    space_type: str = "l2",
    ef_search: int = 512,
    ef_construction: int = 512,
    m: int = 16,
    vector_field: str = "embedding",
) -> Dict:
    """For Approximate k-NN Search, this is the default mapping to create index."""
    return {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": ef_search}},
        "mappings": {
            "properties": {
                vector_field: {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
            }
        },
    }


def _faq_text_mapping(
    dim: int,
    engine: str = "nmslib",
    space_type: str = "l2",
    ef_search: int = 512,
    ef_construction: int = 512,
    m: int = 16,
) -> Dict:
    """For Approximate k-NN Search, this is the default mapping to create index."""
    text_field_list = ["content", "text", "answer", "title"]
    lang_list = ["zh", "en"]
    type_list = ["similarity", "relevance"]
    vector_field_mapping = {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": ef_search}},
        "mappings": {"properties": {}},
    }
    for text_field in text_field_list:
        for lang in lang_list:
            for type in type_list:
                vector_field_mapping["mappings"]["properties"][
                    f"{text_field}_{lang}_{type}_vector"
                ] = {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                }
    return vector_field_mapping


def _ug_text_mapping(
    dim: int,
    engine: str = "nmslib",
    space_type: str = "l2",
    ef_search: int = 512,
    ef_construction: int = 512,
    m: int = 16,
) -> Dict:
    """For Approximate k-NN Search, this is the default mapping to create index."""
    return {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": ef_search}},
        "mappings": {
            "properties": {
                "content_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
                "topic_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
                "service_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
                "abstract_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
                "title_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
                "source_vector": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": space_type,
                        "engine": engine,
                        "parameters": {"ef_construction": ef_construction, "m": m},
                    },
                },
            }
        },
    }


def _default_approximate_search_query(
    query_vector: List[float],
    k: int = 4,
    vector_field: str = "vector_field",
) -> Dict:
    """For Approximate k-NN Search, this is the default query."""
    return {
        "size": k,
        "query": {"knn": {vector_field: {"vector": query_vector, "k": k}}},
    }


def _approximate_search_query_with_boolean_filter(
    query_vector: List[float],
    boolean_filter: Dict,
    k: int = 4,
    vector_field: str = "vector_field",
    subquery_clause: str = "must",
) -> Dict:
    """For Approximate k-NN Search, with Boolean Filter."""
    return {
        "size": k,
        "query": {
            "bool": {
                "filter": boolean_filter,
                subquery_clause: [
                    {"knn": {vector_field: {"vector": query_vector, "k": k}}}
                ],
            }
        },
    }


def _approximate_search_query_with_efficient_filter(
    query_vector: List[float],
    efficient_filter: Dict,
    k: int = 4,
    vector_field: str = "vector_field",
) -> Dict:
    """For Approximate k-NN Search, with Efficient Filter for Lucene and
    Faiss Engines."""
    search_query = _default_approximate_search_query(
        query_vector, k=k, vector_field=vector_field
    )
    search_query["query"]["knn"][vector_field]["filter"] = efficient_filter
    return search_query


def _default_script_query(
    query_vector: List[float],
    k: int = 4,
    space_type: str = "l2",
    pre_filter: Optional[Dict] = None,
    vector_field: str = "vector_field",
) -> Dict:
    """For Script Scoring Search, this is the default query."""

    if not pre_filter:
        pre_filter = MATCH_ALL_QUERY

    return {
        "size": k,
        "query": {
            "script_score": {
                "query": pre_filter,
                "script": {
                    "source": "knn_score",
                    "lang": "knn",
                    "params": {
                        "field": vector_field,
                        "query_value": query_vector,
                        "space_type": space_type,
                    },
                },
            }
        },
    }


def __get_painless_scripting_source(
    space_type: str, vector_field: str = "vector_field"
) -> str:
    """For Painless Scripting, it returns the script source based on space type."""
    source_value = (
        "(1.0 + " + space_type + "(params.query_value, doc['" + vector_field + "']))"
    )
    if space_type == "cosineSimilarity":
        return source_value
    else:
        return "1/" + source_value


def _default_painless_scripting_query(
    query_vector: List[float],
    k: int = 4,
    space_type: str = "l2Squared",
    pre_filter: Optional[Dict] = None,
    vector_field: str = "vector_field",
) -> Dict:
    """For Painless Scripting Search, this is the default query."""

    if not pre_filter:
        pre_filter = MATCH_ALL_QUERY

    source = __get_painless_scripting_source(space_type, vector_field=vector_field)
    return {
        "size": k,
        "query": {
            "script_score": {
                "query": pre_filter,
                "script": {
                    "source": source,
                    "params": {
                        "field": vector_field,
                        "query_value": query_vector,
                    },
                },
            }
        },
    }


def _get_kwargs_value(kwargs: Any, key: str, default_value: Any) -> Any:
    """Get the value of the key if present. Else get the default_value."""
    if key in kwargs:
        return kwargs.get(key)
    return default_value


class OpenSearchVectorSearch(VectorStore):
    """`Amazon OpenSearch Vector Engine` vector store.

    Example:
        .. code-block:: python

            from langchain.vectorstores import OpenSearchVectorSearch
            opensearch_vector_search = OpenSearchVectorSearch(
                "http://localhost:9200",
                "embeddings",
                embedding_function
            )

    """

    def __init__(
        self,
        opensearch_url: str,
        index_name: str,
        embedding_function: Embeddings,
        **kwargs: Any,
    ):
        """Initialize with necessary components."""
        self.embedding_function = embedding_function
        self.index_name = index_name
        http_auth = _get_kwargs_value(kwargs, "http_auth", None)
        self.is_aoss = _is_aoss_enabled(http_auth=http_auth)
        self.client = _get_opensearch_client(opensearch_url, **kwargs)
        self.engine = _get_kwargs_value(kwargs, "engine", None)

    @property
    def embeddings(self) -> Embeddings:
        return self.embedding_function

    def add_documents(
        self, documents: List[Dict], ids: List[int], **kwargs: Any
    ) -> List[str]:
        """Run more documents through the embeddings and add to the vectorstore.

        Args:
            documents (List[Dict]: Documents to add to the vectorstore.

        Returns:
            List[str]: List of IDs of the added texts.
        """
        # TODO: Handle the case where the user doesn't provide ids on the Collection
        titles = []
        contents = []
        answers = []
        texts = []
        metadatas = []
        dim = 1024
        space_type = _get_kwargs_value(kwargs, "space_type", "l2")
        ef_search = _get_kwargs_value(kwargs, "ef_search", 512)
        ef_construction = _get_kwargs_value(kwargs, "ef_construction", 512)
        m = _get_kwargs_value(kwargs, "m", 16)
        engine = _get_kwargs_value(kwargs, "engine", "nmslib")
        lang = _get_kwargs_value(kwargs, "lang", "zh")
        type = _get_kwargs_value(kwargs, "type", "similarity")
        _validate_aoss_with_engines(self.is_aoss, engine)
        mapping = _faq_text_mapping(
            dim, engine, space_type, ef_search, ef_construction, m
        )
        for doc in documents:
            raw_content = doc["content"].replace("\n", " ")
            field_match = re.match("Title\:(.*)Content\:(.*)Answer\:(.*)", raw_content)
            if not field_match:
                print(f"doc format no match {doc['source']}")
                continue
            titles.append(field_match.group(1))
            contents.append(field_match.group(2))
            answers.append(field_match.group(3))
            texts.append(doc["content"])
            if type(doc["source"]) is float and math.isnan(doc["source"]):
                doc["source"] = ""
            metadatas.append({"source": doc["source"]})
        if len(texts) > 0:
            self.add_texts(
                texts,
                metadatas,
                text_field="text",
                vector_field=f"text_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                titles,
                text_field="title",
                vector_field=f"title_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                contents,
                text_field="content",
                vector_field=f"content_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                answers,
                text_field="answer",
                vector_field=f"answer_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )

    def add_faq_documents_v2(
        self, documents: List[Dict], ids: List[int], **kwargs: Any
    ) -> List[str]:
        """Run more documents through the embeddings and add to the vectorstore.

        Args:
            documents (List[Dict]: Documents to add to the vectorstore.

        Returns:
            List[str]: List of IDs of the added texts.
        """
        # TODO: Handle the case where the user doesn't provide ids on the Collection
        texts = []
        metadatas = []
        dim = 1024
        space_type = _get_kwargs_value(kwargs, "space_type", "l2")
        ef_search = _get_kwargs_value(kwargs, "ef_search", 512)
        ef_construction = _get_kwargs_value(kwargs, "ef_construction", 512)
        m = _get_kwargs_value(kwargs, "m", 16)
        engine = _get_kwargs_value(kwargs, "engine", "nmslib")
        embedding_lang = _get_kwargs_value(kwargs, "embedding_lang", "zh")
        embedding_type = _get_kwargs_value(kwargs, "embedding_type", "similarity")
        _validate_aoss_with_engines(self.is_aoss, engine)
        mapping = _default_text_mapping(
            dim, engine, space_type, ef_search, ef_construction, m, "embedding"
        )
        for doc in documents:
            if type(doc["source"]) is float and math.isnan(doc["source"]):
                doc["source"] = "dgr-oncall"
            base_metadata = {
                "source": doc["source"],
                "embedding_lang": embedding_lang,
                "embedding_type": embedding_type,
            }
            raw_content = doc["content"].replace("\n", " ")
            field_match = re.match("Title\:(.*)Content\:(.*)Answer\:(.*)", raw_content)
            if not field_match:
                print(f"doc format no match {doc['source']}")
                continue
            # question
            texts.append(field_match.group(1))
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "question"
            metadatas.append(metadata)
            # question detail
            texts.append(field_match.group(2))
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "question_detail"
            metadatas.append(metadata)
            # answer
            texts.append(field_match.group(3))
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "answer"
            metadatas.append(metadata)
            # all_text
            texts.append(doc["content"])
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "all_text"
            metadatas.append(metadata)
        if len(texts) > 0:
            self.add_texts(
                texts,
                metadatas,
                text_field="content",
                vector_field=f"embedding",
                mapping=mapping,
                **kwargs,
            )

    def add_ug_documents(
        self, documents: List[Dict], ids: List[int], **kwargs: Any
    ) -> List[str]:
        """Run more documents through the embeddings and add to the vectorstore.

        Args:
            documents (List[Dict]: Documents to add to the vectorstore.

        Returns:
            List[str]: List of IDs of the added texts.
        """
        # TODO: Handle the case where the user doesn't provide ids on the Collection
        services = []
        abstracts = []
        topics = []
        contents = []
        metadatas = []
        titles = []
        sources = []
        dim = 1024
        space_type = _get_kwargs_value(kwargs, "space_type", "l2")
        ef_search = _get_kwargs_value(kwargs, "ef_search", 512)
        ef_construction = _get_kwargs_value(kwargs, "ef_construction", 512)
        m = _get_kwargs_value(kwargs, "m", 16)
        engine = _get_kwargs_value(kwargs, "engine", "nmslib")
        _validate_aoss_with_engines(self.is_aoss, engine)
        mapping = _ug_text_mapping(
            dim, engine, space_type, ef_search, ef_construction, m
        )
        for doc in documents:
            services.append(doc["service"])
            abstracts.append(doc["abstract"])
            topics.append(doc["topic"])
            contents.append(doc["content"])
            titles.append(f"{doc['service']} {doc['abstract']} {doc['topic']}")
            sources.append(doc["url"])
            metadatas.append(
                {"source": doc["url"], "lang": doc["lang"], "type": doc["type"]}
            )
        if len(topics) > 0:
            self.add_texts(
                topics,
                metadatas,
                text_field="topic",
                vector_field="topic_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                contents,
                text_field="content",
                vector_field="content_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                abstracts,
                text_field="abstract",
                vector_field="abstract_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                services,
                text_field="service",
                vector_field="service_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                titles,
                text_field="title",
                vector_field="title_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )
            self.add_texts(
                sources,
                text_field="source",
                vector_field="source_{lang}_{type}_vector",
                ids=ids,
                mapping=mapping,
                **kwargs,
            )

    def add_ug_documents_v2(
        self, documents: List[Dict], ids: List[int], **kwargs: Any
    ) -> List[str]:
        """Run more documents through the embeddings and add to the vectorstore.

        Args:
            documents (List[Dict]: Documents to add to the vectorstore.

        Returns:
            List[str]: List of IDs of the added texts.
        """
        # TODO: Handle the case where the user doesn't provide ids on the Collection
        texts = []
        metadatas = []
        dim = 1024
        space_type = _get_kwargs_value(kwargs, "space_type", "l2")
        ef_search = _get_kwargs_value(kwargs, "ef_search", 512)
        ef_construction = _get_kwargs_value(kwargs, "ef_construction", 512)
        m = _get_kwargs_value(kwargs, "m", 16)
        engine = _get_kwargs_value(kwargs, "engine", "nmslib")
        embedding_lang = _get_kwargs_value(kwargs, "embedding_lang", "zh")
        embedding_type = _get_kwargs_value(kwargs, "embedding_type", "similarity")
        _validate_aoss_with_engines(self.is_aoss, engine)
        mapping = _default_text_mapping(
            dim, engine, space_type, ef_search, ef_construction, m, "embedding"
        )
        for doc in documents:
            base_metadata = {
                "source": doc["url"],
                "embedding_lang": embedding_lang,
                "embedding_type": embedding_type,
                "content_lang": doc["lang"],
                "content_type": doc["type"],
                "is_api": doc["is_api"],
            }
            # service
            texts.append(doc["service"])
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "service"
            metadatas.append(metadata)
            # abstract
            texts.append(doc["abstract"])
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "abstract"
            metadatas.append(metadata)
            # topic
            texts.append(doc["topic"])
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "topic"
            metadatas.append(metadata)
            # content
            texts.append(doc["content"])
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "content"
            metadatas.append(metadata)
            # title
            texts.append(f"{doc['service']} {doc['topic']}")
            metadata = copy.deepcopy(base_metadata)
            metadata["field"] = "title"
            metadatas.append(metadata)
        if len(texts) > 0:
            self.add_texts(
                texts,
                metadatas,
                text_field="content",
                vector_field=f"embedding",
                mapping=mapping,
                **kwargs,
            )

    def __add(
        self,
        texts: Iterable[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        bulk_size: int = 500,
        **kwargs: Any,
    ) -> List[str]:
        _validate_embeddings_and_bulk_size(len(embeddings), bulk_size)
        index_name = _get_kwargs_value(kwargs, "index_name", self.index_name)
        text_field = _get_kwargs_value(kwargs, "text_field", "text")
        vector_field = _get_kwargs_value(kwargs, "vector_field", "vector_field")
        max_chunk_bytes = _get_kwargs_value(kwargs, "max_chunk_bytes", 1 * 1024 * 1024)
        mapping = _get_kwargs_value(kwargs, "mapping", None)

        return _bulk_ingest_embeddings(
            self.client,
            index_name,
            embeddings,
            texts,
            metadatas=metadatas,
            ids=ids,
            vector_field=vector_field,
            text_field=text_field,
            mapping=mapping,
            max_chunk_bytes=max_chunk_bytes,
            is_aoss=self.is_aoss,
        )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        bulk_size: int = 500,
        **kwargs: Any,
    ) -> List[str]:
        """Run more texts through the embeddings and add to the vectorstore.

        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            bulk_size: Bulk API request count; Default: 500

        Returns:
            List of ids from adding the texts into the vectorstore.

        Optional Args:
            vector_field: Document field embeddings are stored in. Defaults to
            "vector_field".

            text_field: Document field the text of the document is stored in. Defaults
            to "text".
        """
        max_retry_time = 3
        retry_time = 0
        embeddings = None
        while retry_time < max_retry_time:
            try:
                embeddings = self.embedding_function.embed_documents(list(texts))
                break
            except Exception as error:
                traceback.print_exc()
                print(f"retry embedding {retry_time} {texts}", error)
                retry_time += 1
        if embeddings is None:
            return
        return self.__add(
            texts,
            embeddings,
            metadatas=metadatas,
            ids=ids,
            bulk_size=bulk_size,
            **kwargs,
        )

    def add_embeddings(
        self,
        text_embeddings: Iterable[Tuple[str, List[float]]],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        bulk_size: int = 500,
        **kwargs: Any,
    ) -> List[str]:
        """Add the given texts and embeddings to the vectorstore.

        Args:
            text_embeddings: Iterable pairs of string and embedding to
                add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            bulk_size: Bulk API request count; Default: 500

        Returns:
            List of ids from adding the texts into the vectorstore.

        Optional Args:
            vector_field: Document field embeddings are stored in. Defaults to
            "vector_field".

            text_field: Document field the text of the document is stored in. Defaults
            to "text".
        """
        texts, embeddings = zip(*text_embeddings)
        return self.__add(
            list(texts),
            list(embeddings),
            metadatas=metadatas,
            ids=ids,
            bulk_size=bulk_size,
            kwargs=kwargs,
        )

    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """Return docs most similar to query.

        By default, supports Approximate Search.
        Also supports Script Scoring and Painless Scripting.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query.

        Optional Args:
            vector_field: Document field embeddings are stored in. Defaults to
            "vector_field".

            text_field: Document field the text of the document is stored in. Defaults
            to "text".

            metadata_field: Document field that metadata is stored in. Defaults to
            "metadata".
            Can be set to a special value "*" to include the entire document.

        Optional Args for Approximate Search:
            search_type: "approximate_search"; default: "approximate_search"

            boolean_filter: A Boolean filter is a post filter consists of a Boolean
            query that contains a k-NN query and a filter.

            subquery_clause: Query clause on the knn vector field; default: "must"

            lucene_filter: the Lucene algorithm decides whether to perform an exact
            k-NN search with pre-filtering or an approximate search with modified
            post-filtering. (deprecated, use `efficient_filter`)

            efficient_filter: the Lucene Engine or Faiss Engine decides whether to
            perform an exact k-NN search with pre-filtering or an approximate search
            with modified post-filtering.

        Optional Args for Script Scoring Search:
            search_type: "script_scoring"; default: "approximate_search"

            space_type: "l2", "l1", "linf", "cosinesimil", "innerproduct",
            "hammingbit"; default: "l2"

            pre_filter: script_score query to pre-filter documents before identifying
            nearest neighbors; default: {"match_all": {}}

        Optional Args for Painless Scripting Search:
            search_type: "painless_scripting"; default: "approximate_search"

            space_type: "l2Squared", "l1Norm", "cosineSimilarity"; default: "l2Squared"

            pre_filter: script_score query to pre-filter documents before identifying
            nearest neighbors; default: {"match_all": {}}
        """
        docs_with_scores = self.similarity_search_with_score(query, k, **kwargs)
        return [doc[0] for doc in docs_with_scores]

    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """Return docs and it's scores most similar to query.

        By default, supports Approximate Search.
        Also supports Script Scoring and Painless Scripting.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents along with its scores most similar to the query.

        Optional Args:
            same as `similarity_search`
        """

        text_field = _get_kwargs_value(kwargs, "text_field", "text")
        metadata_field = _get_kwargs_value(kwargs, "metadata_field", "metadata")

        hits = self._raw_similarity_search_with_score(query=query, k=k, **kwargs)

        documents_with_scores = [
            (
                Document(
                    page_content=hit["_source"][text_field],
                    metadata=hit["_source"]
                    if metadata_field == "*" or metadata_field not in hit["_source"]
                    else hit["_source"][metadata_field],
                ),
                hit["_score"],
            )
            for hit in hits
        ]
        return documents_with_scores

    def _raw_similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[dict]:
        """Return raw opensearch documents (dict) including vectors,
        scores most similar to query.

        By default, supports Approximate Search.
        Also supports Script Scoring and Painless Scripting.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of dict with its scores most similar to the query.

        Optional Args:
            same as `similarity_search`
        """
        embedding = self.embedding_function.embed_query(query)
        search_type = _get_kwargs_value(kwargs, "search_type", "approximate_search")
        vector_field = _get_kwargs_value(kwargs, "vector_field", "vector_field")
        index_name = _get_kwargs_value(kwargs, "index_name", self.index_name)
        filter = _get_kwargs_value(kwargs, "filter", {})

        if (
            self.is_aoss
            and search_type != "approximate_search"
            and search_type != SCRIPT_SCORING_SEARCH
        ):
            raise ValueError(
                "Amazon OpenSearch Service Serverless only "
                "supports `approximate_search` and `script_scoring`"
            )

        if search_type == "approximate_search":
            boolean_filter = _get_kwargs_value(kwargs, "boolean_filter", {})
            subquery_clause = _get_kwargs_value(kwargs, "subquery_clause", "must")
            efficient_filter = _get_kwargs_value(kwargs, "efficient_filter", {})
            # `lucene_filter` is deprecated, added for Backwards Compatibility
            lucene_filter = _get_kwargs_value(kwargs, "lucene_filter", {})

            if boolean_filter != {} and efficient_filter != {}:
                raise ValueError(
                    "Both `boolean_filter` and `efficient_filter` are provided which "
                    "is invalid"
                )

            if lucene_filter != {} and efficient_filter != {}:
                raise ValueError(
                    "Both `lucene_filter` and `efficient_filter` are provided which "
                    "is invalid. `lucene_filter` is deprecated"
                )

            if lucene_filter != {} and boolean_filter != {}:
                raise ValueError(
                    "Both `lucene_filter` and `boolean_filter` are provided which "
                    "is invalid. `lucene_filter` is deprecated"
                )

            if (
                efficient_filter == {}
                and boolean_filter == {}
                and lucene_filter == {}
                and filter != {}
            ):
                if self.engine in ["faiss", "lucene"]:
                    efficient_filter = filter
                else:
                    boolean_filter = filter

            if boolean_filter != {}:
                search_query = _approximate_search_query_with_boolean_filter(
                    embedding,
                    boolean_filter,
                    k=k,
                    vector_field=vector_field,
                    subquery_clause=subquery_clause,
                )
            elif efficient_filter != {}:
                search_query = _approximate_search_query_with_efficient_filter(
                    embedding, efficient_filter, k=k, vector_field=vector_field
                )
            elif lucene_filter != {}:
                warnings.warn(
                    "`lucene_filter` is deprecated. Please use the keyword argument"
                    " `efficient_filter`"
                )
                search_query = _approximate_search_query_with_efficient_filter(
                    embedding, lucene_filter, k=k, vector_field=vector_field
                )
            else:
                search_query = _default_approximate_search_query(
                    embedding, k=k, vector_field=vector_field
                )
        elif search_type == SCRIPT_SCORING_SEARCH:
            space_type = _get_kwargs_value(kwargs, "space_type", "l2")
            pre_filter = _get_kwargs_value(kwargs, "pre_filter", MATCH_ALL_QUERY)
            search_query = _default_script_query(
                embedding, k, space_type, pre_filter, vector_field
            )
        elif search_type == PAINLESS_SCRIPTING_SEARCH:
            space_type = _get_kwargs_value(kwargs, "space_type", "l2Squared")
            pre_filter = _get_kwargs_value(kwargs, "pre_filter", MATCH_ALL_QUERY)
            search_query = _default_painless_scripting_query(
                embedding, k, space_type, pre_filter, vector_field
            )
        else:
            raise ValueError("Invalid `search_type` provided as an argument")

        response = self.client.search(index=index_name, body=search_query)

        return [hit for hit in response["hits"]["hits"]]

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        **kwargs: Any,
    ) -> list[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
                     Defaults to 20.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
        Returns:
            List of Documents selected by maximal marginal relevance.
        """

        vector_field = _get_kwargs_value(kwargs, "vector_field", "vector_field")
        text_field = _get_kwargs_value(kwargs, "text_field", "text")
        metadata_field = _get_kwargs_value(kwargs, "metadata_field", "metadata")

        # Get embedding of the user query
        embedding = self.embedding_function.embed_query(query)

        # Do ANN/KNN search to get top fetch_k results where fetch_k >= k
        results = self._raw_similarity_search_with_score(query, fetch_k, **kwargs)

        embeddings = [result["_source"][vector_field] for result in results]

        # Rerank top k results using MMR, (mmr_selected is a list of indices)
        mmr_selected = maximal_marginal_relevance(
            np.array(embedding), embeddings, k=k, lambda_mult=lambda_mult
        )

        return [
            Document(
                page_content=results[i]["_source"][text_field],
                metadata=results[i]["_source"][metadata_field],
            )
            for i in mmr_selected
        ]

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        bulk_size: int = 500,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> OpenSearchVectorSearch:
        """Construct OpenSearchVectorSearch wrapper from raw texts.

        Example:
            .. code-block:: python

                from langchain.vectorstores import OpenSearchVectorSearch
                from langchain.embeddings import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings()
                opensearch_vector_search = OpenSearchVectorSearch.from_texts(
                    texts,
                    embeddings,
                    opensearch_url="http://localhost:9200"
                )

        OpenSearch by default supports Approximate Search powered by nmslib, faiss
        and lucene engines recommended for large datasets. Also supports brute force
        search through Script Scoring and Painless Scripting.

        Optional Args:
            vector_field: Document field embeddings are stored in. Defaults to
            "vector_field".

            text_field: Document field the text of the document is stored in. Defaults
            to "text".

        Optional Keyword Args for Approximate Search:
            engine: "nmslib", "faiss", "lucene"; default: "nmslib"

            space_type: "l2", "l1", "cosinesimil", "linf", "innerproduct"; default: "l2"

            ef_search: Size of the dynamic list used during k-NN searches. Higher values
            lead to more accurate but slower searches; default: 512

            ef_construction: Size of the dynamic list used during k-NN graph creation.
            Higher values lead to more accurate graph but slower indexing speed;
            default: 512

            m: Number of bidirectional links created for each new element. Large impact
            on memory consumption. Between 2 and 100; default: 16

        Keyword Args for Script Scoring or Painless Scripting:
            is_appx_search: False

        """
        embeddings = embedding.embed_documents(texts)
        return cls.from_embeddings(
            embeddings,
            texts,
            embedding,
            metadatas=metadatas,
            bulk_size=bulk_size,
            ids=ids,
            **kwargs,
        )

    @classmethod
    def from_embeddings(
        cls,
        embeddings: List[List[float]],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        bulk_size: int = 500,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> OpenSearchVectorSearch:
        """Construct OpenSearchVectorSearch wrapper from pre-vectorized embeddings.

        Example:
            .. code-block:: python

                from langchain.vectorstores import OpenSearchVectorSearch
                from langchain.embeddings import OpenAIEmbeddings
                embedder = OpenAIEmbeddings()
                embeddings = embedder.embed_documents(["foo", "bar"])
                opensearch_vector_search = OpenSearchVectorSearch.from_embeddings(
                    embeddings,
                    texts,
                    embedder,
                    opensearch_url="http://localhost:9200"
                )

        OpenSearch by default supports Approximate Search powered by nmslib, faiss
        and lucene engines recommended for large datasets. Also supports brute force
        search through Script Scoring and Painless Scripting.

        Optional Args:
            vector_field: Document field embeddings are stored in. Defaults to
            "vector_field".

            text_field: Document field the text of the document is stored in. Defaults
            to "text".

        Optional Keyword Args for Approximate Search:
            engine: "nmslib", "faiss", "lucene"; default: "nmslib"

            space_type: "l2", "l1", "cosinesimil", "linf", "innerproduct"; default: "l2"

            ef_search: Size of the dynamic list used during k-NN searches. Higher values
            lead to more accurate but slower searches; default: 512

            ef_construction: Size of the dynamic list used during k-NN graph creation.
            Higher values lead to more accurate graph but slower indexing speed;
            default: 512

            m: Number of bidirectional links created for each new element. Large impact
            on memory consumption. Between 2 and 100; default: 16

        Keyword Args for Script Scoring or Painless Scripting:
            is_appx_search: False

        """
        opensearch_url = get_from_dict_or_env(
            kwargs, "opensearch_url", "OPENSEARCH_URL"
        )
        # List of arguments that needs to be removed from kwargs
        # before passing kwargs to get opensearch client
        keys_list = [
            "opensearch_url",
            "index_name",
            "is_appx_search",
            "vector_field",
            "text_field",
            "engine",
            "space_type",
            "ef_search",
            "ef_construction",
            "m",
            "max_chunk_bytes",
            "is_aoss",
        ]
        _validate_embeddings_and_bulk_size(len(embeddings), bulk_size)
        dim = len(embeddings[0])
        # Get the index name from either from kwargs or ENV Variable
        # before falling back to random generation
        index_name = get_from_dict_or_env(
            kwargs, "index_name", "OPENSEARCH_INDEX_NAME", default=uuid.uuid4().hex
        )
        is_appx_search = _get_kwargs_value(kwargs, "is_appx_search", True)
        vector_field = _get_kwargs_value(kwargs, "vector_field", "vector_field")
        text_field = _get_kwargs_value(kwargs, "text_field", "text")
        max_chunk_bytes = _get_kwargs_value(kwargs, "max_chunk_bytes", 1 * 1024 * 1024)
        http_auth = _get_kwargs_value(kwargs, "http_auth", None)
        is_aoss = _is_aoss_enabled(http_auth=http_auth)
        engine = None

        if is_aoss and not is_appx_search:
            raise ValueError(
                "Amazon OpenSearch Service Serverless only "
                "supports `approximate_search`"
            )

        if is_appx_search:
            engine = _get_kwargs_value(kwargs, "engine", "nmslib")
            space_type = _get_kwargs_value(kwargs, "space_type", "l2")
            ef_search = _get_kwargs_value(kwargs, "ef_search", 512)
            ef_construction = _get_kwargs_value(kwargs, "ef_construction", 512)
            m = _get_kwargs_value(kwargs, "m", 16)

            _validate_aoss_with_engines(is_aoss, engine)

            mapping = _default_text_mapping(
                dim, engine, space_type, ef_search, ef_construction, m, vector_field
            )
        else:
            mapping = _default_scripting_text_mapping(dim)

        [kwargs.pop(key, None) for key in keys_list]
        client = _get_opensearch_client(opensearch_url, **kwargs)
        _bulk_ingest_embeddings(
            client,
            index_name,
            embeddings,
            texts,
            ids=ids,
            metadatas=metadatas,
            vector_field=vector_field,
            text_field=text_field,
            mapping=mapping,
            max_chunk_bytes=max_chunk_bytes,
            is_aoss=is_aoss,
        )
        kwargs["engine"] = engine
        return cls(opensearch_url, index_name, embedding, **kwargs)
