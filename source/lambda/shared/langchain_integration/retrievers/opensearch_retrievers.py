from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import OpenSearchVectorSearch
from .databases.opensearch import OpenSearchBM25Search,OpenSearchHybridSearch
from langchain_core.embeddings import Embeddings
from langchain_core.documents import BaseDocumentCompressor
from ..models.embedding_models import EmbeddingModel
from typing import Any, Dict, List, Union,Tuple
from ..models.rerank_models import RerankModel
from pydantic import Field  
from langchain.docstore.document import Document
from langchain.callbacks.manager import (
    CallbackManagerForRetrieverRun,
    AsyncCallbackManagerForRetrieverRun
)
import traceback
from shared.utils.logger_utils import get_logger
from shared.constant import ContextExtendMethod
import asyncio
from shared.utils.asyncio_utils import run_coroutine_task
from langchain.retrievers.multi_query import MultiQueryRetriever

logger = get_logger(__name__)


class OpensearchHybridRetrieverBase(BaseRetriever):
    database: OpenSearchHybridSearch
    embeddings: Embeddings
    reranker: Union[BaseDocumentCompressor,None] = None
    bm25_search_context_extend_method: str = ContextExtendMethod.WHOLE_DOC
    bm25_search_whole_doc_max_size:int = 100
    bm25_search_chunk_window_size: int = 10
    enable_bm25_search:bool = True

    bm25_search_top_k:int = 5
    
    vector_search_context_extend_method: str = ContextExtendMethod.WHOLE_DOC
    vector_search_chunk_window_size: int = 10
    vector_search_top_k:int = 5 
    vector_search_whole_doc_max_size:int = 100
    enable_vector_search:bool = True

    rerank_top_k:Union[int,None] = None
    # search_params: dict = Field(default=dict)

    @classmethod
    def from_config(
        cls,
        embedding_config: dict = None,
        rerank_config: dict = None,
        **kwargs
    ):
        database = OpenSearchHybridSearch(
            embedding_dimension=embedding_config['embedding_dimension'],
            **kwargs,
        )
        embeddings = EmbeddingModel.get_model(
            **embedding_config
        )
        reranker = None
        if rerank_config is not None:
            reranker = RerankModel.get_model(
                **rerank_config
            )
        return cls(
            database=database,
            embeddings=embeddings,
            reranker=reranker,
            **kwargs
            # search_params=search_params
        )

    
    def create_bm25_search_query_dict(self,query:str,top_k=int,**kwargs):
        return {
            "size": top_k,
            "query": {"match": {self.database.text_field: query}},
            "_source": {"excludes": ["*.additional_vecs", "vector_field"]},
        }

    def create_vector_search_query_dict(self, embedding:List[float], top_k=int, **kwargs):
        query_dict = {
                "size": top_k,
                "query": {
                    "knn": {
                    self.database.vector_field: {
                        "vector": embedding,
                        "k": top_k
                    }
                }
            },
            "_source": {"excludes": ["*.additional_vecs", "vector_field"]},
        }
        
        return query_dict

    
    def _build_exact_search_query(
        self, query_term, field, size
    ):
        """
        Build basic search query

        :param index_name: Target Index Name
        :param query_term: query term
        :param field: search field
        :param size: number of results to return from aos

        :return: aos response json
        """
        query = {
            "size": size,
            "query": {
                "bool": {
                    "should": [{"match_phrase": {field: query_term}}],
                }
            },
            "sort": [{"_score": {"order": "desc"}}],
        }
        return query

    

    async def aextend_bm25_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:

        raise NotImplementedError
    
    async def aextend_vector_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:

        raise NotImplementedError

    async def abm25_search(self,query:str,**kwargs):
        top_k = kwargs.get("bm25_search_top_k",self.bm25_search_top_k)
        search_query_dict = self.create_bm25_search_query_dict(
            query=query, 
            top_k=top_k, 
            **kwargs
        )

        search_res = await self.database.asearch(search_query_dict)
        results = await self.aextend_bm25_search_results(search_res, **kwargs)
        for doc in results:
            doc.metadata['search_by'] = 'bm25'
        return results

    
    async def avector_search(self, query:str, **kwargs):
        top_k = kwargs.get("vector_search_top_k", self.vector_search_top_k)
        embedding = await self._aget_embedding(query)
        search_query_dict = self.create_vector_search_query_dict(
            embedding=embedding,
            top_k=top_k,
            **kwargs
        )
        print('vector search query: ',search_query_dict)
        search_res = await self.database.asearch(search_query_dict)
        print('vector search ret: ',search_res)
        results = await self.aextend_vector_search_results(search_res, **kwargs)
        for doc in results:
            doc.metadata['search_by'] = 'vector'
        return results

    async def _aget_embedding(self,query:str):
        return await self.embeddings.aembed_query(query)


    async def acompress_documents(self,query,output_docs:list[Document],**kwargs):
        rerank_top_k = kwargs.get('rerank_top_k',self.rerank_top_k)
        bm25_search_top_k = kwargs.get('bm25_search_top_k', self.bm25_search_top_k)
        vector_search_top_k = kwargs.get('vector_search_top_k', self.vector_search_top_k)
        rerank_top_k = rerank_top_k or bm25_search_top_k + vector_search_top_k
        compressed_output_docs = await self.reranker.acompress_documents(
            documents=output_docs, 
            query=query
        )
        
        compressed_output_docs = sorted(compressed_output_docs, key=lambda x: x.metadata['relevance_score'], reverse=True)
        compressed_output_docs = compressed_output_docs[:rerank_top_k]
        return compressed_output_docs



    async def __aget_relevant_documents(
        self, query: str, *, 
        run_manager: AsyncCallbackManagerForRetrieverRun,
        **kwargs
    ) -> List[Document]:
        # bm_25 search 
        enable_bm25_search = kwargs.get(
            "enable_bm25_search", 
            self.enable_bm25_search
        )
        enable_vector_search = kwargs.get(
            "enable_vector_search",
            self.enable_vector_search
        )
        bm25_search_results = []
        vector_search_results = []
        if not (enable_bm25_search or enable_vector_search):
            raise ValueError("At least one of enable_bm25_search or enable_vector_search must be True")
        
        if enable_bm25_search:
            bm25_search_results:List[Document] = await self.abm25_search(query,**kwargs)

        if enable_vector_search:
            vector_search_results: List[Document] = await self.avector_search(
                    query=query,
                    **kwargs
            )
        # rerank
        if self.reranker is not None:
            output_docs = bm25_search_results + vector_search_results
            return await self.acompress_documents(query,output_docs,**kwargs)
            # TODO 
            # rerank_top_k = kwargs.get("rerank_top_k", self.rerank_top_k) or self.bm25_search_top_k + self.vector_search_top_k
            # compressed_output_docs = await self.reranker.acompress_documents(
            #     documents=output_docs, 
            # )
            
            # compressed_output_docs = sorted(compressed_output_docs, key=lambda x: x.metadata['relevance_score'], reverse=True)
            # compressed_output_docs = compressed_output_docs[:rerank_top_k]
            # return compressed_output_docs
        else:
            # altertively to merge the retriverd docs
            print('bm25_search_results',bm25_search_results)
            print('vector_search_results',vector_search_results)
            merged_documents = []
            retriever_docs = [bm25_search_results,vector_search_results]
            max_docs = max(map(len, retriever_docs), default=0)
            for i in range(max_docs):
                for doc in retriever_docs:
                    if i < len(doc):
                        merged_documents.append(doc[i])
            return merged_documents
    

    async def _aget_relevant_documents(
        self, query: str, *, 
        run_manager: AsyncCallbackManagerForRetrieverRun,
        **kwargs
    ) -> List[Document]:
        current_config = {**self.model_dump(),**kwargs}
        logger.info(f"retriever config: {current_config}")
        result = await self.__aget_relevant_documents(query, run_manager=run_manager, **kwargs)
        logger.info(f"retrievered: {result}")
        return result

    
    def _get_relevant_documents(
            self, 
            query: str, *, 
            run_manager: AsyncCallbackManagerForRetrieverRun,
            **kwargs
        ) -> List[Document]:
        return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager, **kwargs))

        

class OpensearchHybridQueryDocumentRetriever(OpensearchHybridRetrieverBase):
    
    async def aget_sibling_context(self, chunk_id, window_size)-> Tuple[List[Document],List[Document]]:
        next_content_list:List[Document] = []
        previous_content_list:List[Document] = []
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
            opensearch_query_response = await self.database.asearch(
                self._build_exact_search_query(
                    query_term=previous_chunk_id,
                    field="metadata.chunk_id",
                    size=1
                )
                # index_name=index_name,
                # query_type="basic",
                # query_term=previous_chunk_id,
                # field="metadata.chunk_id",
                # size=1,
            )
            if len(opensearch_query_response["hits"]["hits"]) > 0:
                r = opensearch_query_response["hits"]["hits"][0]
                previous_content_list.insert(0,Document(
                    page_content=r["_source"][self.database.text_field],
                    metadata={
                        **r["_source"]["metadata"]
                    },
                )
                )
                # previous_content_list.insert(0, r["_source"]["text"])
                previous_pos += 1
            else:
                break
        while next_pos < window_size:
            next_section_id += 1
            next_chunk_id = f"{chunk_id_prefix}-{next_section_id}"
            opensearch_query_response = await self.database.asearch(
                self._build_exact_search_query(
                    query_term=next_chunk_id,
                    field="metadata.chunk_id",
                    size=1
                )
            
                # index_name=index_name,
                # query_type="basic",
                # query_term=next_chunk_id,
                # field="metadata.chunk_id",
                # size=1,
            )
            if len(opensearch_query_response["hits"]["hits"]) > 0:
                r = opensearch_query_response["hits"]["hits"][0]
                next_content_list.append(Document(
                    page_content=r["_source"][self.database.text_field],
                    metadata={
                        **r["_source"]["metadata"],
                    },
                )
                )
                next_pos += 1
            else:
                break
        return [previous_content_list, next_content_list]


    async def aget_context(
            self,
            doc:Document, 
            window_size:int
        ) -> Tuple[List[Document],List[Document]]:
        previous_content_list = []
        next_content_list = []
        if "chunk_id" not in doc.metadata:
            return previous_content_list, next_content_list
        chunk_id = doc.metadata["chunk_id"]
        inner_previous_content_list, inner_next_content_list = await self.aget_sibling_context(
            chunk_id, window_size
        )
        if (
            len(inner_previous_content_list) == window_size
            and len(inner_next_content_list) == window_size
        ):
            return inner_previous_content_list, inner_next_content_list

        if "heading_hierarchy" not in doc.metadata:
            return [previous_content_list, next_content_list]
        if "previous" in doc.metadata["heading_hierarchy"]:
            previous_chunk_id = doc.metadata["heading_hierarchy"][
                "previous"
            ]
            previous_pos = 0
            while (
                previous_chunk_id
                and previous_chunk_id.startswith("$")
                and previous_pos < window_size
            ):
                opensearch_query_response = await self.database.asearch(
                    self._build_exact_search_query(
                        query_term=previous_chunk_id,
                        field="metadata.chunk_id",
                        size=1
                )
                )
                if len(opensearch_query_response["hits"]["hits"]) > 0:
                    r = opensearch_query_response["hits"]["hits"][0]
                    previous_chunk_id = r["_source"]["metadata"]["heading_hierarchy"][
                        "previous"
                    ]
                    previous_content_list.insert(0,Document(
                        page_content=r["_source"][self.database.text_field],
                        metadata={
                            **r["_source"]["metadata"],
                        },
                    )
                    )
                    previous_pos += 1
                else:
                    break
        if "next" in doc.metadata["heading_hierarchy"]:
            next_chunk_id = doc.metadata["heading_hierarchy"]["next"]
            next_pos = 0
            while (
                next_chunk_id and next_chunk_id.startswith(
                    "$") and next_pos < window_size
            ):
                opensearch_query_response = await self.database.asearch(
                    self._build_exact_search_query(
                        query_term=next_chunk_id,
                        field="metadata.chunk_id",
                        size=1
                )
                )
                if len(opensearch_query_response["hits"]["hits"]) > 0:
                    r = opensearch_query_response["hits"]["hits"][0]
                    next_chunk_id = r["_source"]["metadata"]["heading_hierarchy"]["next"]
                    next_content_list.append(Document(
                        page_content=r["_source"][self.database.text_field],
                        metadata={
                            **r["_source"]["metadata"],
                        })
                    )
                    next_pos += 1
                else:
                    break
        return [previous_content_list, next_content_list]

    
    async def aget_doc(self,file_path,size=100) -> list[Document]:
        """
        get whole doc according to file_path
        """
        query_dict = {
            "size": size,
            "query": {
                "bool": {
                    "should": [{"match_phrase": {f"metadata.{self.database.source_field}": file_path}}],
                }
            },
            "sort": [{"_score": {"order": "desc"}}],
        }
        opensearch_query_response = await self.database.asearch(
            query_dict
        )
       
        chunk_list:list[Document] = []
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
                Document(
                    page_content=r["_source"][self.database.text_field],
                    metadata={
                        **r["_source"]["metadata"],
                        # "chunk_id": chunk_id,
                        # "content_type": content_type,
                        # "source": file_path,
                        "chunk_group_id": chunk_group_id,
                        "chunk_section_id": chunk_section_id,
                    },
                )
            )
            # chunk_list.append(
            #     (
            #         chunk_id,
            #         chunk_group_id,
            #         content_type,
            #         chunk_section_id,
            #         r["_source"][self.database.text_field],
            #     )
            # )
        sorted_chunk_list = sorted(
            chunk_list, 
            key=lambda x: (
                x.metadata['chunk_group_id'], 
                x.metadata['content_type'], 
                x.metadata['chunk_section_id']
            )
        )
        # chunk_text_list = [x[4] for x in sorted_chunk_list]
        return sorted_chunk_list
    
    
    async def _aextend_search_results(
            self,
            search_response:dict,
            context_extend_method:str,
            whole_doc_max_size:int,
            chunk_window_size:int,
            **kwargs
        )->List[Document]:
        results:list[Document] = []
        if not search_response:
            return results
        hits = search_response["hits"]["hits"]
        if len(hits) == 0:
            return results
        
        for hit in hits:
            results.append(Document(
                page_content=hit["_source"][self.database.text_field],
                metadata={
                    **hit["_source"]["metadata"],
                    "retrieval_score": hit["_score"],
                    "detail": hit["_source"],
                }
            ))

            # result = {"data": {}}
            # source = hit["_source"]["metadata"][self.database.source_field]
            # result['chunk_id'] = hit["_source"]["metadata"]['chunk_id']
            # result["source"] = source
            # result["score"] = hit["_score"]
            # result["detail"] = hit["_source"]
            # result["content"] = hit["_source"][self.database.text_field]
            # result["doc"] = result["content"]
            # results.append(result)
        
        if context_extend_method == ContextExtendMethod.NONE:
            return results
        
        if context_extend_method == ContextExtendMethod.WHOLE_DOC:
            extend_chunks_list:list[list[Document]] = await asyncio.gather(
                    *[
                        self.aget_doc(
                            result.metadata[self.database.source_field], 
                            size=whole_doc_max_size
                        )
                        for result in results
                    ]
                )
            
            for result,extend_chunks in zip(results,extend_chunks_list):
                result.metadata['extend_chunks'] = extend_chunks
                # if whole_doc:
                #     if result["doc"] not in whole_doc:
                #         whole_doc += "\n" + result["doc"]
                #     result["doc"] = whole_doc
            return results
        
        if context_extend_method == ContextExtendMethod.NEIGHBOR:
            extend_chunks_list:list[list[Document]] = await asyncio.gather(
                    *[
                        self.aget_context(
                            result,
                            chunk_window_size
                        )
                        for result in results
                    ]
                )
                # self.get_context(
                #     results,
                #     chunk_window_size
                # )
            
            for result,extend_chunks in zip(results,extend_chunks_list):
                result.metadata['extend_chunks'] = extend_chunks
                # if whole_doc:
                #     if result["doc"] not in whole_doc:
                #         whole_doc += "\n" + result["doc"]
                #     result["doc"] = whole_doc
            return results
        
        raise ValueError(f"ContextExtendMethod {context_extend_method} not supported")
    
    async def aextend_bm25_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:

        bm25_search_context_extend_method = kwargs.get(
            "bm25_search_context_extend_method",self.bm25_search_context_extend_method
        )
        bm25_search_whole_doc_max_size = kwargs.get(
            "bm25_search_whole_doc_max_size",self.bm25_search_whole_doc_max_size
        )

        bm25_search_chunk_window_size = kwargs.get(
            "bm25_search_chunk_window_size",self.bm25_search_chunk_window_size
        )
        return await self._aextend_search_results(
            search_response=search_response,
            context_extend_method = bm25_search_context_extend_method,
            whole_doc_max_size = bm25_search_whole_doc_max_size,
            chunk_window_size = bm25_search_chunk_window_size,
            **kwargs
        )
    
    async def aextend_vector_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:

        vector_search_context_extend_method = kwargs.get(
            "vector_search_context_extend_method",self.vector_search_context_extend_method
        )
        vector_search_whole_doc_max_size = kwargs.get(
            "vector_search_whole_doc_max_size",self.vector_search_whole_doc_max_size
        )

        vector_search_chunk_window_size = kwargs.get(
            "vector_search_chunk_window_size",self.vector_search_chunk_window_size
        )
        return await self._aextend_search_results(
            search_response=search_response,
            context_extend_method = vector_search_context_extend_method,
            whole_doc_max_size = vector_search_whole_doc_max_size,
            chunk_window_size = vector_search_chunk_window_size,
            **kwargs
        )


class OpensearchHybridQueryQuestionRetriever(OpensearchHybridRetrieverBase):
    
    async def aget_faq_answer(self,file_path):
        opensearch_query_response = await self.database.asearch(
            self._build_exact_search_query(
                query_term=file_path,
                field=f"metadata.{self.database.source_field}",
                size=1
            )
        ) 
        #     index_name=index_name,
        #     query_type="basic",
        #     query_term=source,
        #     field=f"metadata.{source_field}",
        # )
        for r in opensearch_query_response["hits"]["hits"]:
            if (
                "field" in r["_source"]["metadata"]
                and "answer" == r["_source"]["metadata"]["field"]
            ):
                return r["_source"]["content"]
            elif "jsonlAnswer" in r["_source"]["metadata"]:
                return r["_source"]["metadata"]["jsonlAnswer"]["answer"]
        return ""

    
    async def _aextend_faq_results(
        self,
        search_response:dict,
        **kwargs
    )-> List[Document]:
        """
        Organize results from aos response
        :param query_type: query type
        :param response: aos response json
        """
        results = []
        if not search_response:
            return results
        hits = search_response["hits"]["hits"]
        for hit in hits:
            result = {}
            try:
                result["score"] = hit["_score"]
                data = hit["_source"]
                metadata = data["metadata"]
                if "field" in metadata:
                    result["answer"] = await self.aget_faq_answer(
                        result["source"]
                    )
                    result["content"] = hit["_source"]["content"]
                    result["question"] = hit["_source"]["content"]
                    result[self.database.source_field] = hit["_source"]["metadata"][self.database.source_field]
                elif "answer" in metadata:
                    # Intentions
                    result["answer"] = metadata["answer"]
                    result["question"] = data[self.database.text_field]
                    result["content"] = data[self.database.text_field]
                    result["source"] = metadata[self.database.source_field]
                    result["kwargs"] = metadata.get("kwargs", {})
                elif "jsonlAnswer" in hit["_source"]["metadata"] and "answer" in hit["_source"]["metadata"]["jsonlAnswer"]:
                    # Intention
                    result["answer"] = hit["_source"]["metadata"]["jsonlAnswer"]["answer"]
                    result["question"] = hit["_source"]["metadata"]["jsonlAnswer"]["question"]
                    result["content"] = hit["_source"][self.database.text_field]
                    if self.database.source_field in hit["_source"]["metadata"]["jsonlAnswer"].keys():
                        result[self.database.source_field] = hit["_source"]["metadata"]["jsonlAnswer"][self.database.source_field]
                    else:
                        result[self.database.source_field] = hit["_source"]["metadata"][self.database.source_field]
                elif "jsonlAnswer" in hit["_source"]["metadata"] and "answer" not in hit["_source"]["metadata"]["jsonlAnswer"]:
                    # QQ match
                    result["answer"] = hit["_source"]["metadata"]["jsonlAnswer"]
                    result["question"] = hit["_source"][self.database.text_field]
                    result["content"] = hit["_source"][self.database.text_field]
                    result[self.database.source_field] = hit["_source"]["metadata"][self.database.source_field]
                else:
                    result["answer"] = hit["_source"]["metadata"]
                    result["content"] = hit["_source"][self.database.text_field]
                    result["question"] = hit["_source"][self.database.text_field]
                    result[self.database.source_field] = hit["_source"]["metadata"][self.database.source_field]
            except Exception as e:
                logger.error(e)
                logger.error(traceback.format_exc())
                logger.error(hit)
                continue

            results.append(
                Document(
                    page_content=result["question"],
                    metadata={
                        **result,
                        "retrieval_score": hit["_score"],
                        "detail": hit["_source"],
                    }
                )
            )
            # results.append(result)
        return results

    
    async def avector_search(self, query:str, **kwargs):
        top_k = kwargs.get("vector_search_top_k", self.vector_search_top_k)
        embedding = await self._aget_embedding(query)
        search_query_dict = self.create_vector_search_query_dict(
            embedding=embedding,
            top_k=top_k,
            **kwargs
        )
        search_res = await self.database.asearch(search_query_dict)
        results = await self._aextend_faq_results(search_res, **kwargs)
        for doc in results:
            doc.metadata['search_by'] = 'vector'
        return results
    
    async def aextend_bm25_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:

        return await self._aextend_faq_results(search_response,**kwargs)

    async def aextend_vector_search_results(
            self,
            search_response:dict,
            **kwargs
        ) -> List[Document]:
        return await self._aextend_faq_results(search_response,**kwargs)
    