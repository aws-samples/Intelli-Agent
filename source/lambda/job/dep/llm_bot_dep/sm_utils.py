"""
Helper functions for using Samgemaker Endpoint via LangChain
"""

import json
import logging
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.embeddings import SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain.llms.sagemaker_endpoint import SagemakerEndpoint
from langchain.llms.utils import enforce_stop_tokens

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)


# extend the SagemakerEndpointEmbeddings class from langchain to provide a custom embedding function, wrap the embedding & injection logic into a single class
class SagemakerEndpointEmbeddingsJumpStart(SagemakerEndpointEmbeddings):
    def embed_documents(
        self, texts: List[str], chunk_size: int = 500
    ) -> List[List[float]]:
        """Compute doc embeddings using a SageMaker Inference Endpoint.

        Args:
            texts: The list of texts to embed.
            chunk_size: The chunk size defines how many input texts will
                be grouped together as request. If None, will use the
                chunk size specified by the class.

        Returns:
            List of embeddings, one for each text.
        """
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


class SagemakerEndpointEmbeddingsJumpStartDGR(SagemakerEndpointEmbeddings):
    def embed_documents(
        self, texts: List[str], chunk_size: int = 5
    ) -> List[List[float]]:
        """Compute doc embeddings using a SageMaker Inference Endpoint.

        Args:
            texts: The list of texts to embed.
            chunk_size: The chunk size defines how many input texts will
                be grouped together as request. If None, will use the
                chunk size specified by the class.

        Returns:
            List of embeddings, one for each text.
        """
        results = []
        _chunk_size = len(texts) if chunk_size > len(texts) else chunk_size
        st = time.time()
        for i in range(0, len(texts), _chunk_size):
            embedding_texts = [
                text[: (512 - 56)] for text in texts[i : i + _chunk_size]
            ]
            try:
                response = self._embedding_func(embedding_texts)
            except Exception as error:
                traceback.print_exc()
                print(f"embedding endpoint error: {texts}", error)
            results.extend(response)
        time_taken = time.time() - st
        logger.debug(
            f"got results for {len(texts)} in {time_taken}s, length of embeddings list is {len(results)}"
        )
        return results


# class for serializing/deserializing requests/responses to/from the embeddings model
class ContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs={}) -> bytes:
        input_str = json.dumps({"inputs": prompt, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]
        return embeddings


def create_embeddings_with_single_model(
    embeddings_model: str, aws_region: str, file_type: str
):
    embeddings_result = None
    if file_type.lower() == "jsonl":
        if "zh" in embeddings_model.lower():
            content_handler = SimilarityZhContentHandler()
        elif "en" in embeddings_model.lower():
            content_handler = SimilarityEnContentHandler()
    else:
        if "zh" in embeddings_model.lower():
            content_handler = RelevanceZhContentHandler()
        elif "en" in embeddings_model.lower():
            content_handler = RelevanceEnContentHandler()

    embeddings_result = create_sagemaker_embeddings_from_js_model(
        embeddings_model, aws_region, content_handler
    )

    return embeddings_result


def create_embeddings_with_m3_model(embeddings_model: str, aws_region: str):
    embeddings_result = None

    content_handler = RelevanceM3ContentHandler()

    embeddings_result = create_sagemaker_embeddings_from_js_model(
        embeddings_model, aws_region, content_handler
    )

    return embeddings_result


def create_embedding_with_multiple_model(
    embeddings_model_list: List[str], aws_region: str, file_type: str
):
    embedding_dict = {}
    if file_type.lower() == "jsonl":
        for embedding_model in embeddings_model_list:
            if "zh" in embedding_model.lower():
                content_handler_zh = SimilarityZhContentHandler()
                embedding_zh = create_sagemaker_embeddings_from_js_model(
                    embedding_model, aws_region, content_handler_zh
                )
                embedding_dict["zh"] = embedding_zh
            elif "en" in embedding_model.lower():
                content_handler_en = SimilarityEnContentHandler()
                embedding_en = create_sagemaker_embeddings_from_js_model(
                    embedding_model, aws_region, content_handler_en
                )
                embedding_dict["en"] = embedding_en
    else:
        for embedding_model in embeddings_model_list:
            if "zh" in embedding_model.lower():
                content_handler_zh = RelevanceZhContentHandler()
                embedding_zh = create_sagemaker_embeddings_from_js_model(
                    embedding_model, aws_region, content_handler_zh
                )
                embedding_dict["zh"] = embedding_zh
            elif "en" in embedding_model.lower():
                content_handler_en = RelevanceEnContentHandler()
                embedding_en = create_sagemaker_embeddings_from_js_model(
                    embedding_model, aws_region, content_handler_en
                )
                embedding_dict["en"] = embedding_en

    return embedding_dict


def create_sagemaker_embeddings_from_js_model(
    embeddings_model_endpoint_name: str, aws_region: str, content_handler
) -> SagemakerEndpointEmbeddingsJumpStart:
    # all set to create the objects for the ContentHandler and
    # SagemakerEndpointEmbeddingsJumpStart classes
    logger.debug(
        f"content_handler: {content_handler}, embeddings_model_endpoint_name: {embeddings_model_endpoint_name}, aws_region: {aws_region}"
    )
    # note the name of the LLM Sagemaker endpoint, this is the model that we would
    # be using for generating the embeddings
    embeddings = SagemakerEndpointEmbeddingsJumpStart(
        endpoint_name=embeddings_model_endpoint_name,
        region_name=aws_region,
        content_handler=content_handler,
    )

    return embeddings


# Migrate the class from sm_utils.py in executor to here, there are 3 models including vector, cross and answer wrapper into class SagemakerEndpointVectorOrCross. TODO, to merge the class along with the previous class SagemakerEndpointEmbeddingsJumpStart
class vectorContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": inputs, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> List[List[float]]:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["sentence_embeddings"]


def SagemakerEndpointVectorOrCross(
    prompt: str,
    endpoint_name: str,
    region_name: str,
    model_type: str,
    stop: List[str],
    **kwargs,
) -> SagemakerEndpoint:
    """
    original class invocation:
        response = self.client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            Body=body,
            ContentType=content_type,
            Accept=accepts,
            **_endpoint_kwargs,
        )
    """
    if model_type == "vector":
        content_handler = vectorContentHandler()
        embeddings = SagemakerEndpointEmbeddings(
            endpoint_name=endpoint_name,
            region_name=region_name,
            content_handler=content_handler,
        )
        query_result = embeddings.embed_query(prompt)
        return query_result

    genericModel = SagemakerEndpoint(
        endpoint_name=endpoint_name,
        region_name=region_name,
        content_handler=content_handler,
    )
    return genericModel(prompt=prompt, stop=stop, **kwargs)


# Class for serializing/deserializing requests/responses to/from the embeddings model
class SimilarityZhContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = [p for p in prompt]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})

        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings


class RelevanceZhContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = ["为这个句子生成表示以用于检索相关文章：" + p for p in prompt]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})

        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings


class SimilarityZhContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = [p for p in prompt]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})

        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings


class RelevanceM3ContentHandler(EmbeddingsContentHandler):
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


class SimilarityM3ContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = [p for p in prompt]

        model_kwargs = {}
        model_kwargs["batch_size"] = 12
        model_kwargs["max_length"] = 512
        model_kwargs["return_type"] = "dense"
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings


class RelevanceEnContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = [
            "Represent this sentence for searching relevant passages:" + p
            for p in prompt
        ]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})

        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings


def create_sagemaker_embeddings_from_js_model_dgr(
    embeddings_model_endpoint_name: str,
    aws_region: str,
    lang: str = "zh",
    type: str = "similarity",
) -> SagemakerEndpointEmbeddingsJumpStartDGR:
    # all set to create the objects for the ContentHandler and
    # SagemakerEndpointEmbeddingsJumpStart classes
    if lang == "zh":
        if type == "similarity":
            content_handler = SimilarityZhContentHandler()
        elif type == "relevance":
            content_handler = RelevanceZhContentHandler()
    elif lang == "en":
        if type == "similarity":
            content_handler = SimilarityEnContentHandler()
        elif type == "relevance":
            content_handler = RelevanceEnContentHandler()
    logger.debug(
        f"content_handler: {content_handler}, embeddings_model_endpoint_name: {embeddings_model_endpoint_name}, aws_region: {aws_region}"
    )
    # note the name of the LLM Sagemaker endpoint, this is the model that we would
    # be using for generating the embeddings
    embeddings = SagemakerEndpointEmbeddingsJumpStartDGR(
        endpoint_name=embeddings_model_endpoint_name,
        region_name=aws_region,
        content_handler=content_handler,
    )
    return embeddings
