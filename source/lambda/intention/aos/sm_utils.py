import io
import json
import logging
from typing import Dict, List

import boto3
from langchain_community.embeddings import BedrockEmbeddings, SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain.llms.sagemaker_endpoint import LLMContentHandler, SagemakerEndpoint

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class vectorContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": inputs, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> List[List[float]]:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["sentence_embeddings"]


class m3ContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": inputs, **model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> List[List[float]]:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["sentence_embeddings"]["dense_vecs"]


class crossContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps(
            {"inputs": prompt, "docs": model_kwargs["context"]})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["scores"][0][1]


class rerankContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, rerank_pairs: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": json.loads(rerank_pairs)})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return json.dumps(response_json["rerank_scores"])


class answerContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, question: str, model_kwargs: Dict) -> bytes:

        template_1 = "以下context xml tag内的文本内容为背景知识：\n<context>\n{context}\n</context>\n请根据背景知识, 回答这个问题：{question}"
        context = model_kwargs["context"]

        if len(context) == 0:
            prompt = question
        else:
            prompt = template_1.format(
                context=model_kwargs["context"], question=question)

        input_str = json.dumps(
            {"inputs": prompt,
                "history": model_kwargs["history"], "parameters": model_kwargs["parameters"]}
        )
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["outputs"]


class LineIterator:
    """
    A helper class for parsing the byte stream input.

    The output of the model will be in the following format:
    ```
    b'{"outputs": [" a"]}\n'
    b'{"outputs": [" challenging"]}\n'
    b'{"outputs": [" problem"]}\n'
    ...
    ```

    While usually each PayloadPart event from the event stream will contain a byte array
    with a full json, this is not guaranteed and some of the json objects may be split across
    PayloadPart events. For example:
    ```
    {'PayloadPart': {'Bytes': b'{"outputs": '}}
    {'PayloadPart': {'Bytes': b'[" problem"]}\n'}}
    ```

    This class accounts for this by concatenating bytes written via the 'write' function
    and then exposing a method which will return lines (ending with a '\n' character) within
    the buffer via the 'scan_lines' function. It maintains the position of the last read
    position to ensure that previous bytes are not exposed again.
    """

    def __init__(self, stream):
        self.byte_iterator = iter(stream)
        self.buffer = io.BytesIO()
        self.read_pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            self.buffer.seek(self.read_pos)
            line = self.buffer.readline()
            if line and line[-1] == ord("\n"):
                self.read_pos += len(line)
                return line[:-1]
            try:
                chunk = next(self.byte_iterator)
            except StopIteration:
                if self.read_pos < self.buffer.getbuffer().nbytes:
                    continue
                raise
            if "PayloadPart" not in chunk:
                print("Unknown event type:" + chunk)
                continue
            self.buffer.seek(0, io.SEEK_END)
            self.buffer.write(chunk["PayloadPart"]["Bytes"])


def SagemakerEndpointVectorOrCross(
    prompt: str, endpoint_name: str, region_name: str, model_type: str, stop: List[str], target_model=None, **kwargs
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
    if target_model:
        endpoint_kwargs = {"TargetModel": target_model}
    else:
        endpoint_kwargs = None
    client = boto3.client("sagemaker-runtime", region_name=region_name)
    if model_type == "vector" or model_type == "bce":
        content_handler = vectorContentHandler()
        embeddings = SagemakerEndpointEmbeddings(
            client=client, endpoint_name=endpoint_name, content_handler=content_handler, endpoint_kwargs=endpoint_kwargs
        )
        query_result = embeddings.embed_query(prompt)
        return query_result
    elif model_type == "cross":
        content_handler = crossContentHandler()
    elif model_type == "m3":
        content_handler = m3ContentHandler()
        model_kwargs = {}
        model_kwargs["batch_size"] = 12
        model_kwargs["max_length"] = 512
        model_kwargs["return_type"] = "dense"
        embeddings = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            content_handler=content_handler,
            model_kwargs=model_kwargs,
            endpoint_kwargs=endpoint_kwargs,
        )
        query_result = embeddings.embed_query(prompt)
        return query_result
    elif model_type == "answer":
        content_handler = answerContentHandler()
    elif model_type == "rerank":
        content_handler = rerankContentHandler()
    # TODO: replace with SagemakerEndpointStreaming
    genericModel = SagemakerEndpoint(
        client=client,
        endpoint_name=endpoint_name,
        # region_name = region_name,
        content_handler=content_handler,
        endpoint_kwargs=endpoint_kwargs,
    )
    return genericModel(prompt=prompt, stop=stop, **kwargs)


def getCustomEmbeddings(endpoint_name: str, region_name: str, model_type: str) -> SagemakerEndpointEmbeddings:
    client = boto3.client("sagemaker-runtime", region_name=region_name)
    bedrock_client = boto3.client("bedrock-runtime")
    embeddings = None
    if model_type == "bedrock":
        content_handler = BedrockEmbeddings()
        embeddings = BedrockEmbeddings(
            client=bedrock_client,
            region_name=region_name,
            model_id=endpoint_name,
        )
    elif model_type == "bce":
        content_handler = vectorContentHandler()
        embeddings = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            content_handler=content_handler,
            endpoint_kwargs={"TargetModel": "bce_embedding_model.tar.gz"},
        )
    # compatible with both m3 and bce.
    else:
        content_handler = m3ContentHandler()
        model_kwargs = {}
        model_kwargs["batch_size"] = 12
        model_kwargs["max_length"] = 512
        model_kwargs["return_type"] = "dense"
        embeddings = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            model_kwargs=model_kwargs,
            content_handler=content_handler,
        )
    return embeddings
