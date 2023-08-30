import json
import re
from langchain.llms.sagemaker_endpoint import LLMContentHandler, SagemakerEndpoint
from langchain.embeddings import SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from typing import Dict, List

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
