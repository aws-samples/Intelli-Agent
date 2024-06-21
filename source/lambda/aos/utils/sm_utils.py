"""
Helper functions for using Samgemaker Endpoint via LangChain
"""

# Imports
import json
import logging
import time
from typing import List

from langchain.embeddings import SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler

# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SagemakerEndpointEmbeddingsJumpStart(SagemakerEndpointEmbeddings):
    """Extend the SagemakerEndpointEmbeddings class from langchain to provide a custom embedding function, wrap the embedding & injection logic into a single class"""

    def embed_documents(
        self, texts: List[str], chunk_size: int = 500
    ) -> List[List[float]]:
        """Compute doc embeddings using a SageMaker Inference Endpoint."""
        results = []
        _chunk_size = len(texts) if chunk_size > len(texts) else chunk_size
        st = time.time()
        for i in range(0, len(texts), _chunk_size):
            response = self._embedding_func(texts[i : i + _chunk_size])
            results.extend(response)
        time_taken = time.time() - st
        logger.debug(
            f"got results for {len(texts)} in {time_taken}s, length of embeddings list is {len(results)}"
        )

        return results


class RelevanceM3ContentHandler(EmbeddingsContentHandler):
    """Content handler for the Relevance M3 model."""

    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        model_kwargs = {}
        model_kwargs["batch_size"] = 12
        model_kwargs["max_length"] = 512
        model_kwargs["return_type"] = "dense"
        input_str = json.dumps({"inputs": prompt, **model_kwargs})

        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]

        if len(embeddings) == 1:
            return [embeddings[0]]

        return [embeddings]


# Function definitions


def create_embeddings_with_m3_model(embeddings_model: str, aws_region: str):
    """Create embeddings with the M3 model."""
    # Implementation omitted for brevity
    embeddings_result = None

    content_handler = RelevanceM3ContentHandler()

    embeddings_result = create_sagemaker_embeddings_from_js_model(
        embeddings_model, aws_region, content_handler
    )

    return embeddings_result


def create_sagemaker_embeddings_from_js_model(
    embeddings_model_endpoint_name: str, aws_region: str, content_handler
) -> SagemakerEndpointEmbeddingsJumpStart:
    """Create SageMaker embeddings from a JumpStart model."""
    # Implementation omitted for brevity
    embeddings = SagemakerEndpointEmbeddingsJumpStart(
        endpoint_name=embeddings_model_endpoint_name,
        region_name=aws_region,
        content_handler=content_handler,
    )

    return embeddings
