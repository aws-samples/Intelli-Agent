import io
import json
import logging
import os
from typing import Any, Dict, Iterator, List, Mapping, Optional

import boto3
from botocore.exceptions import ClientError
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain_community.embeddings import (
    BedrockEmbeddings,
    SagemakerEndpointEmbeddings,
)
from langchain_community.embeddings.sagemaker_endpoint import (
    EmbeddingsContentHandler,
)
from langchain_community.llms import SagemakerEndpoint
from langchain_community.llms.sagemaker_endpoint import LLMContentHandler
from langchain_community.llms.utils import enforce_stop_tokens
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import GenerationChunk
from langchain_core.pydantic_v1 import Extra, root_validator

logger = logging.getLogger()
logger.setLevel(logging.INFO)
region_name = os.environ["AWS_REGION"]
session = boto3.session.Session()
secret_manager_client = session.client(
    service_name="secretsmanager", region_name=region_name
)


def get_secret_value(secret_arn: str):
    """Get secret value from secret manager

    Args:
        secret_arn (str): secret arn

    Returns:
        str: secret value
    """
    try:
        get_secret_value_response = secret_manager_client.get_secret_value(
            SecretId=secret_arn
        )
    except ClientError as e:
        raise Exception("Fail to retrieve the secret value: {}".format(e))
    else:
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
            return secret
        else:
            raise Exception("Fail to retrieve the secret value")


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
            {"inputs": prompt, "docs": model_kwargs["context"]}
        )
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
                context=model_kwargs["context"], question=question
            )

        input_str = json.dumps(
            {
                "inputs": prompt,
                "history": model_kwargs["history"],
                "parameters": model_kwargs["parameters"],
            }
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


class SagemakerEndpointWithStreaming(SagemakerEndpoint):
    chat_history: List[Dict] = None

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}
        _endpoint_kwargs = self.endpoint_kwargs or {}

        body = self.content_handler.transform_input(
            prompt, self.chat_history, _model_kwargs
        )
        # content_type = self.content_handler.content_type
        # accepts = self.content_handler.accepts
        resp = self.client.invoke_endpoint_with_response_stream(
            EndpointName=self.endpoint_name,
            Body=body,
            ContentType=self.content_handler.content_type,
            **_endpoint_kwargs,
        )
        iterator = LineIterator(resp["Body"])

        for line in iterator:
            resp = json.loads(line)
            resp_output = resp.get("outputs")
            if stop is not None:
                # Uses same approach as below
                resp_output = enforce_stop_tokens(resp_output, stop)
            # run_manager.on_llm_new_token(resp_output)
            yield GenerationChunk(text=resp_output)


class SagemakerEndpointChat(BaseChatModel):
    client: Any = None
    """Boto3 client for sagemaker runtime"""

    endpoint_name: str = ""
    """The name of the endpoint from the deployed Sagemaker model.
    Must be unique within an AWS Region."""

    region_name: str = ""
    """The aws region where the Sagemaker model is deployed, eg. `us-west-2`."""

    credentials_profile_name: Optional[str] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    content_handler: LLMContentHandler = None
    """The content handler class that provides an input and
    output transform functions to handle formats between LLM
    and the endpoint.
    """

    streaming: bool = False
    """Whether to stream the results."""

    """
     Example:
        .. code-block:: python

        from langchain_community.llms.sagemaker_endpoint import LLMContentHandler

        class ContentHandler(LLMContentHandler):
                content_type = "application/json"
                accepts = "application/json"

                def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
                    input_str = json.dumps({prompt: prompt, **model_kwargs})
                    return input_str.encode('utf-8')
                
                def transform_output(self, output: bytes) -> str:
                    response_json = json.loads(output.read().decode("utf-8"))
                    return response_json[0]["generated_text"]
    """

    model_kwargs: Optional[Dict] = None
    """Keyword arguments to pass to the model."""

    endpoint_kwargs: Optional[Dict] = None
    """Optional attributes passed to the invoke_endpoint
    function. See `boto3`_. docs for more info.
    .. _boto3: <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
    """
    content_type: str = "application/json"
    accepts: str = "application/json"

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid.value

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Dont do anything if client provided externally"""
        if values.get("client") is not None:
            return values

        """Validate that AWS credentials to and python package exists in environment."""
        try:
            import boto3

            try:
                if values["credentials_profile_name"] is not None:
                    session = boto3.Session(
                        profile_name=values["credentials_profile_name"]
                    )
                else:
                    # use default credentials
                    session = boto3.Session()

                values["client"] = session.client(
                    "sagemaker-runtime", region_name=values["region_name"]
                )

            except Exception as e:
                raise ValueError(
                    "Could not load credentials to authenticate with AWS client. "
                    "Please check that credentials in the specified "
                    "profile name are valid."
                ) from e

        except ImportError:
            raise ImportError(
                "Could not import boto3 python package. "
                "Please install it with `pip install boto3`."
            )
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        _model_kwargs = self.model_kwargs or {}
        return {
            **{"endpoint_name": self.endpoint_name},
            **{"model_kwargs": _model_kwargs},
        }

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "sagemaker_endpoint"

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}
        _endpoint_kwargs = self.endpoint_kwargs or {}

        # body = self.content_handler.transform_input(prompt, self.chat_history, _model_kwargs)
        body = json.dumps(
            {"messages": messages, "parameters": {**_model_kwargs}}
        )
        # print(body)
        # # print(sdg)
        # content_type = self.content_handler.content_type
        # accepts = self.content_handler.accepts
        resp = self.client.invoke_endpoint_with_response_stream(
            EndpointName=self.endpoint_name,
            Body=body,
            ContentType=self.content_type,
            **_endpoint_kwargs,
        )
        iterator = LineIterator(resp["Body"])

        for line in iterator:
            resp = json.loads(line)
            resp_output = resp.get("outputs")
            if stop is not None:
                # Uses same approach as below
                resp_output = enforce_stop_tokens(resp_output, stop)
            # run_manager.on_llm_new_token(resp_output)
            yield resp_output

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}
        _endpoint_kwargs = self.endpoint_kwargs or {}

        # body = self.content_handler.transform_input(prompt, self.chat_history, _model_kwargs)
        body = json.dumps(
            {"messages": messages, "parameters": {**_model_kwargs}}
        )
        try:
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                Body=body,
                ContentType=self.content_type,
                Accept=self.accepts,
                **_endpoint_kwargs,
            )
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

        # text = self.content_handler.transform_output(response["Body"])
        text = json.loads(response["Body"].read().decode("utf-8"))

        if stop is not None:
            # This is a bit hacky, but I can't figure out a better way to enforce
            # stop tokens when making calls to the sagemaker endpoint.
            text = enforce_stop_tokens(text, stop)
        return text


def SagemakerEndpointVectorOrCross(
    prompt: str,
    endpoint_name: str,
    region_name: str,
    model_type: str,
    stop: List[str],
    target_model=None,
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
    if target_model:
        endpoint_kwargs = {"TargetModel": target_model}
    else:
        endpoint_kwargs = None
    client = boto3.client("sagemaker-runtime", region_name=region_name)
    if model_type == "vector" or model_type == "bce":
        content_handler = vectorContentHandler()
        embeddings = SagemakerEndpointEmbeddings(
            client=client,
            endpoint_name=endpoint_name,
            content_handler=content_handler,
            endpoint_kwargs=endpoint_kwargs,
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


def getCustomEmbeddings(
    endpoint_name: str, region_name: str, bedrock_region: str, model_type: str, bedrock_api_key_arn: str = None
) -> SagemakerEndpointEmbeddings:
    client = boto3.client("sagemaker-runtime", region_name=region_name)
    bedrock_client = boto3.client("bedrock-runtime", region_name=bedrock_region)
    embeddings = None
    if model_type == "bedrock":
        content_handler = BedrockEmbeddings()
        embeddings = BedrockEmbeddings(
            client=bedrock_client,
            model_id=endpoint_name,
            normalize=True,
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
