import json
import os
import time
import logging
import asyncio
import numpy as np
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from typing import Dict, Optional, Sequence, Any

from langchain.callbacks.manager import Callbacks
from langchain.schema import Document
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor

from sm_utils import SagemakerEndpointVectorOrCross

rerank_model_endpoint = os.environ.get("rerank_endpoint", "")

"""Document compressor that uses BGE reranker model."""
class BGEM3Reranker(BaseDocumentCompressor):

    """Number of documents to return."""
    def _colbert_score_np(self, q_reps, p_reps):
        token_scores = np.einsum('nik,njk->nij', q_reps, p_reps)
        scores = token_scores.max(-1)
        scores = np.sum(scores) / q_reps.shape[0]
        return scores

    async def __ainvoke_rerank_model(self, query_batch, doc_batch, loop):
        return await loop.run_in_executor(None,
                                          self._colbert_score_np,
                                          np.asarray(query_batch),
                                          np.asarray(doc_batch))

    async def __spawn_task(self, query_colbert_list, doc_colbert_list):
        batch_size = 1
        task_list = []
        loop = asyncio.get_event_loop()
        for batch_start in range(0, len(query_colbert_list), batch_size):
            task = asyncio.create_task(self.__ainvoke_rerank_model(
                query_colbert_list[batch_start:batch_start + batch_size],
                doc_colbert_list[batch_start:batch_start + batch_size], loop))
            task_list.append(task)
        return await asyncio.gather(*task_list)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: dict,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents using BGE M3 Colbert Score.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        start = time.time()
        if len(documents) == 0:  # to avoid empty api call
            return []
        doc_list = list(documents)
        _docs = [d.metadata["retrieval_data"]['colbert'] for d in doc_list]

        rerank_text_length = 1024 * 10
        query_colbert_list = []
        doc_colbert_list = []
        for doc in _docs:
            query_colbert_list.append(query["colbert"][:rerank_text_length])
            doc_colbert_list.append(doc[:rerank_text_length])
        score_list = []
        logger.info(f'rerank pair num {len(query_colbert_list)}, m3 method: colbert score')
        score_list = asyncio.run(self.__spawn_task(query_colbert_list, doc_colbert_list))
        final_results = []
        debug_info = query["debug_info"]
        debug_info["knowledge_qa_rerank"] = []
        for doc, score in zip(doc_list, score_list):
            doc.metadata["rerank_score"] = score
            # set common score for llm.
            doc.metadata["score"] = doc.metadata["rerank_score"]
            final_results.append(doc)
            debug_info["knowledge_qa_rerank"].append((doc.page_content, doc.metadata["retrieval_content"], doc.metadata["source"], score))
        final_results.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)
        debug_info["knowledge_qa_rerank"].sort(key=lambda x: x[-1], reverse=True)
        recall_end_time = time.time()
        elpase_time = recall_end_time - start
        logger.info(f"runing time of rerank: {elpase_time}s seconds")
        return final_results

"""Document compressor that uses BGE reranker model."""
class BGEReranker(BaseDocumentCompressor):

    """Number of documents to return."""
    query_key: str="query"
    config: Dict={"run_name": "BGEReranker"}
    enable_debug: Any
    target_model: Any
    rerank_model_endpoint: str=rerank_model_endpoint
    top_k: int=10

    def __init__(self, query_key='query', enable_debug=False, rerank_model_endpoint=rerank_model_endpoint, target_model=None, top_k=10):
        super().__init__()
        self.query_key = query_key
        self.enable_debug = enable_debug
        self.rerank_model_endpoint = rerank_model_endpoint
        self.target_model = target_model
        self.top_k = top_k

    async def __ainvoke_rerank_model(self, batch, loop):
        logging.info("invoke endpoint")
        return await loop.run_in_executor(None,
                                          SagemakerEndpointVectorOrCross,
                                          json.dumps(batch),
                                          self.rerank_model_endpoint,
                                          None,
                                          "rerank",
                                          None,
                                          self.target_model)

    async def __spawn_task(self, rerank_pair):
        batch_size = 128
        task_list = []
        loop = asyncio.get_event_loop()
        for batch_start in range(0, len(rerank_pair), batch_size):
            task = asyncio.create_task(self.__ainvoke_rerank_model(rerank_pair[batch_start:batch_start + batch_size], loop))
            task_list.append(task)
        return await asyncio.gather(*task_list)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents using BGE rerank model.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        start = time.time()
        if len(documents) == 0:  # to avoid empty api call
            return []
        doc_list = list(documents)
        _docs = [d.metadata["retrieval_content"] for d in doc_list]

        rerank_pair = []
        rerank_text_length = 1024 * 10
        for doc in _docs:
            rerank_pair.append([query[self.query_key], doc[:rerank_text_length]])
        score_list = []
        logger.info(f'rerank pair num {len(rerank_pair)}, endpoint_name: {self.rerank_model_endpoint}')
        response_list = asyncio.run(self.__spawn_task(rerank_pair))
        for response in response_list:
            score_list.extend(json.loads(response))
        final_results = []
        debug_info = query["debug_info"]
        debug_info["knowledge_qa_rerank"] = []
        for doc, score in zip(doc_list, score_list):
            doc.metadata["rerank_score"] = score
            # set common score for llm.
            doc.metadata["retrieval_score"] = doc.metadata["retrieval_score"]
            doc.metadata["score"] = doc.metadata["rerank_score"]
            final_results.append(doc)
            if self.enable_debug:
                debug_info["knowledge_qa_rerank"].append((doc.page_content, doc.metadata["retrieval_content"], doc.metadata["source"], score))
        final_results.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)
        debug_info["knowledge_qa_rerank"].sort(key=lambda x: x[-1], reverse=True)
        recall_end_time = time.time()
        elpase_time = recall_end_time - start
        logger.info(f"runing time of rerank: {elpase_time}s seconds")
        return final_results[:self.top_k]

"""Document compressor that uses retriever score."""
class MergeReranker(BaseDocumentCompressor):

    """Number of documents to return."""

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents using BGE rerank model.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        start = time.time()
        if len(documents) == 0:  # to avoid empty api call
            return []
        final_results = []
        debug_info = query["debug_info"]
        debug_info["knowledge_qa_rerank"] = []
        final_results = list(documents)
        final_results.sort(key=lambda x: x.metadata["score"], reverse=True)
        debug_info["knowledge_qa_rerank"].append([(doc.page_content, doc.metadata["retrieval_content"],
                                                  doc.metadata["source"], doc.metadata["score"]) for doc in final_results])
        recall_end_time = time.time()
        elpase_time = recall_end_time - start
        logger.info(f"runing time of rerank: {elpase_time}s seconds")
        return final_results