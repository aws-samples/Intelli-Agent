from langchain_core.documents import Document
from langchain_community.vectorstores.opensearch_vector_search import (
    _is_aoss_enabled,
    _get_opensearch_client,
    _get_async_opensearch_client,
    _import_bulk
)
from langchain_core.retrievers import BaseRetriever
from typing import Optional,Iterable,List,Tuple
import uuid 
import pandas as pd 
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.pydantic_v1 import Field, root_validator
import hashlib 
from langchain_core.embeddings import Embeddings


from langchain_community.vectorstores.opensearch_vector_search import OpenSearchVectorSearch

from pydantic import dataclasses, Field
from typing import Any,Union



@dataclasses
class OpenSearceBase:
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
        raise NotImplemented

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        max_chunk_bytes: Optional[int] = 1 * 1024 * 1024,
        **kwargs
    ) -> List[str]:
        bulk = _import_bulk()
        requests,return_ids = self.create_injestion_requests(
            texts=texts,
            metadatas=metadatas,
            ids=ids,
            **kwargs
        )
        
        bulk(self.client, requests, max_chunk_bytes=max_chunk_bytes)
        if not self.is_aoss:
            self.client.indices.refresh(index=self.index_name)
        return return_ids 

    def search(self,query_dict:dict):
        res = self.client.search(index=self.index_name, body=query_dict)
        return res



class OpenSearchVectorSearch(OpenSearceBase):
    embedding_function: Embeddings
    dimension: int
    ef_search: int = 512
    refresh_interval: str = "60s"
    number_of_shards: int = 5
    number_of_replicas: int = 0
    


    @property
    def embeddings(self) -> Embeddings:
        return self.embedding_function

    def create_index(
        self
    ) -> Optional[str]:
        body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": self.ef_search,
                    "refresh_interval": self.refresh_interval,
                    "number_of_shards": self.number_of_shards,
                    # disable replica
                    "number_of_replicas": self.number_of_replicas,
                }
            },
            "mappings": {
                "properties": {
                    "vector_field": {
                        "type": "knn_vector",
                        "dimension": self.dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                            "parameters": {"ef_construction": 128, "m": 16},
                        },
                    }
                }
            },
        }
    




class OpenSearchBM25Search(OpenSearceBase):
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
                "content": {
                    "type":self.text_field,
                    "similarity": "custom_bm25",  # Use the custom BM25 similarity
                },
            }
        }
       
        self.client.indices.create(
            index=index_name,
            body={
                "settings":settings,
                "mappings":mappings
            })
        return index_name

    def create_injestion_requests(self, texts, metadatas = None, ids = None, **kwargs):
        requests = []
        return_ids = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "index",
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



    # def _get_relevant_documents(
    #     self, query: str, *, run_manager: CallbackManagerForRetrieverRun,**kwargs
    # ) -> List[Document]:
    #     query_dict = self._create_query_dict(query,**kwargs)
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
    #     return ret



class OpenSearchHybridSearch(OpenSearceBase):
    k1: float = 1.2
    b: float = 0.75
    analyzer_type: str = "standard"
    text_field: str = "text"
    vector_field: str = "vector"
    vector_dimension: int = 768
    vector_similarity: str = "cosine"
    vector_weight: float = 0.5
    text_weight: float = 0.5

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
                self.vector_field: {
                    "type": "knn_vector",
                    "dimension": self.vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": self.vector_similarity,
                        "engine": "nmslib",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16,
                        },
                    },
                },
                "content": {
                    "type":self.text_field,
                    "similarity": "custom_bm25",  # Use the custom BM25 similarity
                },
            }
        }

        self.client.indices.create(
            index=index_name,
            body={
                "settings":settings,
                "mappings":mappings
            })
        return index_name

    def create_injestion_requests(self, texts, metadatas = None, ids = None, **kwargs):
        requests = []
        return_ids = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas else {}
            _id = ids[i] if ids else str(uuid.uuid4())
            request = {
                "_op_type": "index",
                "_index": self.index_name,
                self.text_field: text,
                self.vector_field: self.get_vector(text),
                "metadata": metadata,
            }
            if self.is_aoss:
                request["id"] = _id
            else:
                request["_id"] = _id
            requests.append(request)
            return_ids.append(_id)
        return requests,return_ids

    def get_vector(self, text):
        return OpenSearchVectorSearch.get_vector(text, self.vector_dimension)

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

    


