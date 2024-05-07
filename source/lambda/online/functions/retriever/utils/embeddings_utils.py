# embeddings
import json
import os
from typing import Dict, List

import boto3
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain_community.embeddings.sagemaker_endpoint import (
    SagemakerEndpointEmbeddings,
)

from .sm_utils import SagemakerEndpointVectorOrCross

region = os.environ["AWS_REGION"]

boto3_bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name= region
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
            **kwargs,
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
            **kwargs,
        )
        return embedding

def get_similarity_embedding(
    query: str, embedding_model_endpoint: str, model_type: str = "vector"
) -> List[List[float]]:
    query_similarity_embedding_prompt = query
    response = SagemakerEndpointVectorOrCross(
        prompt=query_similarity_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        region_name=region,
        model_type=model_type,
        stop=None,
    )
    return response
    # if model_type in ["vector","m3"]:
    #     response = {"dense_vecs": response}
    # # elif model_type == "m3":
    # #     # response["dense_vecs"] = response["dense_vecs"]
    # #     response = {"dense_vecs": response}
    # return response

def get_relevance_embedding(
    query: str,
    query_lang: str,
    embedding_model_endpoint: str,
    model_type: str = "vector",
):
    if model_type == "vector":
        if query_lang == "zh":
            query_relevance_embedding_prompt = (
                "为这个句子生成表示以用于检索相关文章：" + query
            )
        elif query_lang == "en":
            query_relevance_embedding_prompt = (
                "Represent this sentence for searching relevant passages: " + query
            )
    elif model_type == "m3":
        query_relevance_embedding_prompt = query
    else:
        raise ValueError(f"invalid embedding model type: {model_type}")
    response = SagemakerEndpointVectorOrCross(
        prompt=query_relevance_embedding_prompt,
        endpoint_name=embedding_model_endpoint,
        region_name=region,
        model_type=model_type,
        stop=None,
    )
    return response
    # if model_type in ["vector",'m3']:
    #     response = {"dense_vecs": response}
    # # elif model_type == "m3":
    # #     response = {"dense_vecs": response}
    #     # response["dense_vecs"] = response["dense_vecs"]
    # return response

def get_embedding_bedrock(texts, model_id):
    provider = model_id.split(".")[0]
    if provider == "cohere":
        body = json.dumps({
            "texts": [texts] if isinstance(texts, str) else texts,
            "input_type": "search_document"
        })
    else:
        # includes common provider == "amazon"
        body = json.dumps({
            "inputText": texts if isinstance(texts, str) else texts[0],
        })
    bedrock_resp = boto3_bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
    response_body = json.loads(bedrock_resp.get('body').read())
    if provider == "cohere":
        embeddings = response_body['embeddings']
    else:
        embeddings = [response_body['embedding']]
    return embeddings