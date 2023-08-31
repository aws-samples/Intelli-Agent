"""
Helper functions for using Samgemaker Endpoint via langchain
"""
import time
import json
import logging
import json
import re
from typing import List

from langchain.llms.sagemaker_endpoint import LLMContentHandler, SagemakerEndpoint
from langchain.embeddings import SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from typing import Dict, List

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# extend the SagemakerEndpointEmbeddings class from langchain to provide a custom embedding function
class SagemakerEndpointEmbeddingsJumpStart(SagemakerEndpointEmbeddings):
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
            response = self._embedding_func(texts[i:i + _chunk_size])
            results.extend(response)
        time_taken = time.time() - st
        logger.info(f"got results for {len(texts)} in {time_taken}s, length of embeddings list is {len(results)}")
        return results

# class for serializing/deserializing requests/responses to/from the embeddings model
class ContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs={}) -> bytes:
        input_str = json.dumps({"inputs": prompt, **model_kwargs})
        return input_str.encode('utf-8') 

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]
        return embeddings

def create_sagemaker_embeddings_from_js_model(embeddings_model_endpoint_name: str, aws_region: str) -> SagemakerEndpointEmbeddingsJumpStart:
    # all set to create the objects for the ContentHandler and 
    # SagemakerEndpointEmbeddingsJumpStart classes
    content_handler = ContentHandler()
    logger.info(f'content_handler: {content_handler}, embeddings_model_endpoint_name: {embeddings_model_endpoint_name}, aws_region: {aws_region}')
    # note the name of the LLM Sagemaker endpoint, this is the model that we would
    # be using for generating the embeddings
    embeddings = SagemakerEndpointEmbeddingsJumpStart( 
        endpoint_name = embeddings_model_endpoint_name,
        region_name = aws_region, 
        content_handler = content_handler
    )
    return embeddings

def enforce_stop_tokens(text, stop) -> str:
    """Cut off the text as soon as any stop words occur."""
    if stop is None:
        return text
    
    return re.split("|".join(stop), text)[0]

class vectorContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": inputs, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> List[List[float]]:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["sentence_embeddings"]

class crossContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt, "docs":model_kwargs["context"]})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['scores'][0][1]

class answerContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, question: str, model_kwargs: Dict) -> bytes:

        template_1 = '以下context xml tag内的文本内容为背景知识：\n<context>\n{context}\n</context>\n请根据背景知识, 回答这个问题：{question}'
        context = model_kwargs["context"]
        
        if len(context) == 0:
            prompt = question
        else:
            prompt = template_1.format(context = model_kwargs["context"], question = question)

        input_str = json.dumps({"inputs": prompt,
                                "history": model_kwargs["history"],
                                "parameters": model_kwargs["parameters"]})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['outputs']

def SagemakerEndpointVectorOrCross(prompt: str, endpoint_name: str, region_name: str, model_type: str, stop: List[str], **kwargs) -> SagemakerEndpoint:
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
    elif model_type == "cross":
        content_handler = crossContentHandler()
    elif model_type == "answer":
        content_handler = answerContentHandler()
    genericModel = SagemakerEndpoint(
        endpoint_name = endpoint_name,
        region_name = region_name,
        content_handler = content_handler
    )
    return genericModel(prompt=prompt, stop=stop, **kwargs)
