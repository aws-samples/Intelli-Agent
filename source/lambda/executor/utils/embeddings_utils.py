# embeddings
import json
import os
from typing import Dict, List

import boto3
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain_community.embeddings.sagemaker_endpoint import (
    SagemakerEndpointEmbeddings,
)


class BGEEmbeddingSagemakerEndpoint:
    class vectorContentHandler(EmbeddingsContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
            input_str = json.dumps({"inputs": inputs, **model_kwargs})
            return input_str.encode("utf-8")

        def transform_output(self, output: bytes) -> List[List[float]]:
            response_json = json.loads(output.read().decode("utf-8"))
            return response_json["sentence_embeddings"]

    def __new__(cls, endpoint_name, region_name=os.environ["AWS_REGION"], **kwargs):
        client = boto3.client("sagemaker-runtime", region_name=region_name)
        content_handler = cls.vectorContentHandler()
        embedding = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            content_handler=content_handler,
            **kwargs
        )
        return embedding


class BGEM3EmbeddingSagemakerEndpoint:
    class vectorContentHandler(EmbeddingsContentHandler):
        content_type = "application/json"
        accepts = "application/json"
        default_model_kwargs = {
            "batch_size": 12,
            "max_length": 512,
            "return_type": "dense",
        }

        def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
            model_kwargs = {**self.default_model_kwargs, **model_kwargs}
            input_str = json.dumps({"inputs": inputs, **model_kwargs})
            return input_str.encode("utf-8")

        def transform_output(self, output: bytes) -> List[List[float]]:
            response_json = json.loads(output.read().decode("utf-8"))

            sentence_embeddings = response_json["sentence_embeddings"]["dense_vecs"]
            return sentence_embeddings

    def __new__(cls, endpoint_name, region_name=os.environ["AWS_REGION"], **kwargs):
        client = boto3.client("sagemaker-runtime", region_name=region_name)
        content_handler = cls.vectorContentHandler()
        embedding = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            content_handler=content_handler,
            **kwargs
        )
        return embedding
