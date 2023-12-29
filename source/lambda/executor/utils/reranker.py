import json
import os
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
        Compress documents using Cohere's rerank API.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        if len(documents) == 0:  # to avoid empty api call
            return []
        doc_list = list(documents)
        _docs = [d.page_content for d in doc_list]

        rerank_pair = []
        rerank_text_length = 1024 * 10
        for doc in _docs:
            rerank_pair.append([query["query"], doc[:rerank_text_length]])
        score_list = json.loads(
            SagemakerEndpointVectorOrCross(
                prompt=json.dumps(rerank_pair),
                endpoint_name=rerank_model_endpoint,
                region_name=region,
                model_type="rerank",
                stop=None,
            )
        )
        final_results = []
        for doc, score in zip(doc_list, score_list):
            doc.metadata["rerank_score"] = score
            final_results.append(doc)
        final_results.sort(key=lambda x: x.metadata["rerank_score"], reverse=True)
        return final_results