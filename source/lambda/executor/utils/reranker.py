import json
import os
import time
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from typing import TYPE_CHECKING, Dict, Optional, Sequence

from langchain.callbacks.manager import Callbacks
from langchain.schema import Document
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor

from sm_utils import SagemakerEndpointVectorOrCross

rerank_model_endpoint = os.environ.get("rerank_endpoint", "")
region = os.environ["AWS_REGION"]

"""Document compressor that uses BGE reranker model."""
class BGEReranker(BaseDocumentCompressor):

    """Number of documents to return."""
    top_n: int = 3

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
        # _docs = [d.metadata["retrieval_content"] for d in doc_list]
        _docs = [d.page_content for d in doc_list]

        rerank_pair = []
        rerank_text_length = 1024 * 10
        for doc in _docs:
            rerank_pair.append([query["query"], doc[:rerank_text_length]])
        batch_size = 64
        score_list = []
        for batch_start in range(0, len(rerank_pair), batch_size):
            batch = rerank_pair[batch_start:batch_start + batch_size]
            score_list.extend(json.loads(
                SagemakerEndpointVectorOrCross(
                    prompt=json.dumps(batch),
                    endpoint_name=rerank_model_endpoint,
                    region_name=region,
                    model_type="rerank",
                    stop=None,
                )
            )
        )
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

"""Document compressor that uses retriever score."""
class MergeReranker(BaseDocumentCompressor):

    """Number of documents to return."""
    top_n: int = 3

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