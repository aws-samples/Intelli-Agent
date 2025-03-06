from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import OpenSearchVectorSearch
from .databases.opensearch import OpenSearchBM25Search,OpenSearchHybridSearch
from langchain_core.embeddings import Embeddings
from langchain_core.documents import BaseDocumentCompressor
from ..models.embedding_models import EmbeddingModel
from typing import Any, Dict, List, Union
from ..models.rerank_models import RerankModel
from pydantic import Field  
from langchain.docstore.document import Document
from langchain.callbacks.manager import (
    CallbackManagerForRetrieverRun,
    AsyncCallbackManagerForRetrieverRun
)


class OpensearchHybridRetriever(BaseRetriever):
    database: OpenSearchHybridSearch
    embeddings: Embeddings
    reranker: Union[BaseDocumentCompressor,None] = None
    search_params: dict = Field(default=dict)

    @classmethod
    def from_config(
        cls,
        embedding_config: dict = None,
        rerank_config: dict = None,
        search_params:dict = None,
        **kwargs
    ):
        search_params = search_params or {}
        database = OpenSearchHybridSearch(
            **kwargs 
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
            search_params=search_params
        )


    async def _aget_embedding(self,query:str):
        return await self.embeddings.aembed_query(query)

    async def _aget_relevant_documents(
        self, query: str, *, 
        run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> List[Document]:
        embedding = await self._aget_embedding(query)
        # bm_25 search 
        self.database.asearch(

        )

        # vector search
        self.database.asearch(

        )

        # rerank



        response = self.client.search(index=self.index_name, body={"query": {"match": {"text": query}}, "size": self.k})
        hits = response['hits']['hits']
        return [hit['_source'] for hit in hits]