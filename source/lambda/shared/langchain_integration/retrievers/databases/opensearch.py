import hashlib
import logging
import traceback
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple, Union

from langchain_community.vectorstores.opensearch_vector_search import (
    _get_async_opensearch_client,
    _get_opensearch_client,
    _import_bulk,
    _is_aoss_enabled,
)
from langchain_core.documents import Document
from langchain_core.pydantic_v1 import Field
from pydantic import Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


@dataclass
class OpenSearchBase:
    opensearch_url:Union[str,None]
    index_name:str
    client_kwargs: dict = Field(default_factory=dict)
    client: any = None
    async_client: any = None
    http_auth: Any = None
    

    def __post_init__(self):
        if self.opensearch_url is None:
            assert self.client is not None and self.async_client is not None, (self.client,self.async_client)
        else:
            assert self.client is  None and self.async_client is  None, (self.client,self.async_client)
            self.client = _get_opensearch_client(self.opensearch_url, **self.client_kwargs)
            self.async_client = _get_async_opensearch_client(self.opensearch_url, **self.client_kwargs)
        self.is_aoss = _is_aoss_enabled(http_auth=self.http_auth)
        self.create_index()
    
    def create_index(self):
        raise NotImplemented

    
    def delete_index(self, index_name: Optional[str] = None) -> Optional[bool]:
        """Deletes a given index from vectorstore."""
        if index_name is None:
            if self.index_name is None:
                raise ValueError("index_name must be provided.")
            index_name = self.index_name
        try:
            self.client.indices.delete(index=index_name)
            return True
        except Exception as e:
            raise e

    def delete(
        self,
        ids: Optional[List[str]] = None,
        refresh_indices: Optional[bool] = True,
        **kwargs: Any,
    ) -> Optional[bool]:
        """Delete documents from the Opensearch index.

        Args:
            ids: List of ids of documents to delete.
            refresh_indices: Whether to refresh the index
                            after deleting documents. Defaults to True.
        """
        bulk = _import_bulk()

        body = []

        if ids is None:
            raise ValueError("ids must be provided.")

        for _id in ids:
            body.append({"_op_type": "delete", "_index": self.index_name, "_id": _id})

        if len(body) > 0:
            try:
                bulk(self.client, body, refresh=refresh_indices, ignore_status=404)
                return True
            except Exception as e:
                raise e
        else:
            return False
    
    async def adelete(
        self, ids: Optional[List[str]] = None, **kwargs: Any
    ) -> Optional[bool]:
        """Asynchronously delete by vector ID or other criteria.

        Args:
            ids: List of ids to delete.
            **kwargs: Other keyword arguments that subclasses might use.

        Returns:
            Optional[bool]: True if deletion is successful,
            False otherwise, None if not implemented.
        """
        if ids is None:
            raise ValueError("No ids provided to delete.")

        actions = [{"delete": {"_index": self.index_name, "_id": id_}} for id_ in ids]
        response = await self.async_client.bulk(body=actions, **kwargs)
        return not any(
            item.get("delete", {}).get("error") for item in response["items"]
        )

    @staticmethod
    def get_md5(s):
        md5 = hashlib.md5()
        md5.update(s.encode('utf-8'))
        return md5.hexdigest()
    
    def index_exists(self, index_name: Optional[str] = None) -> Optional[bool]:
        """If given index present in vectorstore, returns True else False."""
        if index_name is None:
            if self.index_name is None:
                raise ValueError("index_name must be provided.")
            index_name = self.index_name

        return self.client.indices.exists(index=index_name)

    def create_injestion_requests(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        **kwargs   
    ) -> Tuple:
        raise NotImplementedError

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        max_chunk_bytes: Optional[int] = 1 * 1024 * 1024,
        max_retry_time: int = 3,
        **kwargs
    ) -> List[str]:
        bulk = _import_bulk()
        requests,return_ids = self.create_injestion_requests(
            texts=texts,
            metadatas=metadatas,
            ids=ids,
            **kwargs
        )
        retry_time = 0
        while retry_time < max_retry_time:
            try:
                bulk(self.client, requests, max_chunk_bytes=max_chunk_bytes)
                break
            except Exception:
                error = traceback.format_exc()
                logging.error(f"retry bulk {retry_time}，error: {error}")
                retry_time += 1
        
        if not self.is_aoss:
            self.client.indices.refresh(index=self.index_name)
        return return_ids 

    def search(self,query_dict:dict):
        res = self.client.search(index=self.index_name, body=query_dict)
        return res
    
    async def asearch(self,query_dict:dict):
        return await self.async_client.search(index=self.index_name, body=query_dict)
      


class OpenSearchBM25Search(OpenSearchBase):
    k1: float = 1.2
    b: float = 0.75
    analyzer_type: str = "standard"
    text_field: str = "text"

    def create_index(
        self
    ) -> Optional[str]:
        """Create a new Index with given arguments"""
        index_name = self.index_name
        k1 = self.k1
        b = self.b
        if self.index_exists(index_name):
            return index_name
        settings = {
            "analysis": {"analyzer": {"default": {"type": self.analyzer_type}}},
            "similarity": {
                "custom_bm25": {
                    "type": "BM25",
                    "k1": k1,
                    "b": b,
                }
            },
        }
        mappings = {
            "properties": {
                self.text_field: {
                    "type":"text",
                    "similarity": "custom_bm25", 
                }
            }
        }
       
        self.client.indices.create(
            index=index_name,
            body={
                "settings":settings,
                "mappings":mappings
            })
        return index_name

    def create_injestion_requests(
            self, 
            texts: Iterable[str], 
            metadatas: Optional[List[dict]] = None,
            ids: Optional[List[str]] = None,
            **kwargs
        ):
        requests = []
        return_ids = []

        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "update",
                "_index": self.index_name,
                self.text_field: text,
                "metadata": metadata,
            }
            if self.is_aoss:
                request["id"] = _id
            else:
                request["_id"] = _id
            requests.append(request)
            return_ids.append(_id)
        return requests,return_ids


def _get_hybrid_search_index_body( 
        embedding_dimension:int,
        engine="nmslib",
        space_type= "l2",
        ann_algrithm="hnsw",
        ef_construction=512,
        m=16,   
        analyzer_type="standard",
        text_field="text",
        vector_field: str = "vector",
        k1=1.2,
        b=0.75
    ):
    
    settings = {
            "analysis": {"analyzer": {"default": {"type": analyzer_type}}},
            "similarity": {
                "custom_bm25": {
                    "type": "BM25",
                    "k1": k1,
                    "b": b,
                }
            },
        }
    
    mapping = {
            "properties": {
                # "metadata": {
                #     "properties": {
                #     "chunk_id": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #             }
                #             }
                #         },
                #     "complete_heading": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #         }
                #         }
                #     },
                #     "content_type": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #         }
                #         }
                #     },
                #     "current_heading": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #         }
                #         }
                #     },
                #     "figure": {
                #         "properties": {
                #         "content_type": {
                #             "type": "text",
                #             "fields": {
                #             "keyword": {
                #                 "type": "keyword",
                #                 "ignore_above": 256
                #             }
                #             }
                #         },
                #         "figure_path": {
                #             "type": "text",
                #             "fields": {
                #             "keyword": {
                #                 "type": "keyword",
                #                 "ignore_above": 256
                #             }
                #             }
                #         }
                #         }
                #     },
                #     "file_path": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #         }
                #         }
                #     },
                #     "file_type": {
                #         "type": "text",
                #         "fields": {
                #         "keyword": {
                #             "type": "keyword",
                #             "ignore_above": 256
                #         }
                #         }
                #     },
                #     "heading_hierarchy": {
                #         "properties": {
                #         "level": {
                #             "type": "long"
                #         },
                #         "next": {
                #             "type": "text",
                #             "fields": {
                #             "keyword": {
                #                 "type": "keyword",
                #                 "ignore_above": 256
                #             }
                #             }
                #         },
                #         "previous": {
                #             "type": "text",
                #             "fields": {
                #             "keyword": {
                #                 "type": "keyword",
                #                 "ignore_above": 256
                #             }
                #             }
                #         },
                #         "size": {
                #             "type": "long"
                #         },
                #         "title": {
                #             "type": "text",
                #             "fields": {
                #             "keyword": {
                #                 "type": "keyword",
                #                 "ignore_above": 256
                #             }
                #             }
                #         }
                #         }
                #     }
                #     }
                # },
                text_field: {
                    "type":"text",
                    "similarity": "custom_bm25", 
                },
                vector_field: {
                    "type": "knn_vector",
                    "dimension": embedding_dimension,
                    "method": {
                    "engine": engine,
                    "space_type": space_type,
                    "name": ann_algrithm,
                    "parameters": {
                        "ef_construction": ef_construction,
                        "m": m
                    }
                 }
            }
            }
        }
    
    return {
        "settings":settings,
        "mappings":mapping
    }


class OpenSearchHybridSearch(OpenSearchBase):
    k1: float = 1.2
    b: float = 0.75
    analyzer_type="standard"
    source_field="file_path"
    text_field: str = "text"
    vector_field: str = "vector"
    embedding_dimension: int
    space_type= "l2"
    m=16
    ef_construction=512
    ann_algrithm="hnsw"
    engine="nmslib"
    
    def create_index(
        self
    ) -> Optional[str]:
        """Create a new Index with given arguments"""
        index_name = self.index_name
        if self.index_exists(index_name):
            return index_name
        index_body = _get_hybrid_search_index_body(
            embedding_dimension=self.embedding_dimension,
            engine=self.engine,
            space_type=self.space_type,
            ann_algrithm=self.ann_algrithm,
            ef_construction=self.ef_construction,
            m=self.m,
            analyzer_type=self.analyzer_type,
            text_field=self.text_field,
            vector_field=self.vector_field,
            k1=self.k1,
            b=self.b
        )

        self.client.indices.create(
            index=index_name,
            body=index_body
        )
        return index_name

    
    @staticmethod
    def _validate_embeddings_and_bulk_size(embeddings_length: int, bulk_size: int) -> None:
        """Validate Embeddings Length and Bulk Size."""
        if embeddings_length == 0:
            raise RuntimeError("Embeddings size is zero")
        if bulk_size < embeddings_length:
            raise RuntimeError(
                f"The embeddings count, {embeddings_length} is more than the "
                f"[bulk_size], {bulk_size}. Increase the value of [bulk_size]."
            )
    
    @staticmethod
    def _validate_aoss_with_engines(is_aoss: bool, engine: str) -> None:
        """Validate AOSS with the engine."""
        if is_aoss and engine != "nmslib" and engine != "faiss":
            raise ValueError(
                "Amazon OpenSearch Service Serverless only "
                "supports `nmslib` or `faiss` engines"
            )

    def create_injestion_requests(
            self,
            texts: Iterable[str],
            embeddings: List[List[float]],
            metadatas: Optional[List[dict]] = None,
            ids: Optional[List[str]] = None,
            bulk_size: int = 500,
            **kwargs: Any
        ):
    
        self._validate_embeddings_and_bulk_size(len(embeddings), bulk_size)
        self._validate_aoss_with_engines(self.is_aoss, self.engine)
        
        requests = []
        return_ids = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "update",
                "_index": self.index_name,
                "doc":{
                    self.text_field: text,
                    self.vector_field: embeddings[i],
                    "metadata": metadata
                },
                "doc_as_upsert": True,
            }
            if self.is_aoss:
                request["id"] = _id
            else:
                request["_id"] = _id
            requests.append(request)
            return_ids.append(_id)
        return requests,return_ids
    

    # def _get_relevant_documents(
    #     self, query: str, *, run_manager: CallbackManagerForRetrieverRun,**kwargs
    # ) -> List[Document]:
    #     query_dict = self._create_query_dict(query, **kwargs)
    #     res = self.client.search(index=self.index_name, body=query_dict)
    #     ret = []
    #     for hit in res["hits"]["hits"]:
    #         page_content = hit['_source']['text']
    #         metadata = hit['_source']['metadata']
    #         metadata['score'] = hit['_score']
    #         ret.append(Document(
    #             page_content=page_content,
    #             metadata=metadata
    #         ))

    


