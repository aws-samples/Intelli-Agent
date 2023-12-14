"""
Helper functions for using Samgemaker Endpoint via LangChain
"""
import io
import sys
import time
import json
import logging
import traceback
from typing import List, Dict, Any, Optional
from langchain.embeddings import SagemakerEndpointEmbeddings
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain.llms.sagemaker_endpoint import LLMContentHandler, SagemakerEndpoint
from langchain.callbacks.manager import CallbackManagerForLLMRun
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
            response = self._embedding_func(texts[i:i + _chunk_size])
            results.extend(response)
        time_taken = time.time() - st
        logger.info(f"got results for {len(texts)} in {time_taken}s, length of embeddings list is {len(results)}")

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
            embedding_texts = [text[:(512-56)] for text in texts[i:i + _chunk_size]]
            try:
                response = self._embedding_func(embedding_texts)
            except Exception as error:
                traceback.print_exc()
                print(f"embedding endpoint error: {texts}", error)
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

"""
Migrate the class from sm_utils.py in executor to here, there are 3 models including vector, cross and answer wrapper into class SagemakerEndpointVectorOrCross. TODO, to merge the class along with the previous class SagemakerEndpointEmbeddingsJumpStart

TODO, unify the sm_utils.py scattered in different folders (lambda/aos, lambda/executor, lambda/job/dep/llm_bot_dep)
"""
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
            if line and line[-1] == ord('\n'):
                self.read_pos += len(line)
                return line[:-1]
            try:
                chunk = next(self.byte_iterator)
            except StopIteration:
                if self.read_pos < self.buffer.getbuffer().nbytes:
                    continue
                raise
            if 'PayloadPart' not in chunk:
                print('Unknown event type:' + chunk)
                continue
            self.buffer.seek(0, io.SEEK_END)
            self.buffer.write(chunk['PayloadPart']['Bytes'])

class SagemakerEndpointStreaming(SagemakerEndpoint):
    # override the _call function to support streaming function with invoke_endpoint_with_response_stream
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call out to Sagemaker inference endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python

                response = se("Tell me a joke.")
        """
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}
        _endpoint_kwargs = self.endpoint_kwargs or {}

        body = self.content_handler.transform_input(prompt, _model_kwargs)
        # the content type should be application/json if we are using LMI container
        content_type = self.content_handler.content_type
        accepts = self.content_handler.accepts

        # send request
        try:
            response = self.client.invoke_endpoint_with_response_stream(
                EndpointName=self.endpoint_name,
                Body=body,
                ContentType=content_type,
                Accept=accepts,
                **_endpoint_kwargs,
            )
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

        # transform_output is not used here because the response is a stream
        for line in LineIterator(response['Body']):
            resp = json.loads(line)
            logging.info(resp.get("outputs")[0], end='')

        # enforce stop tokens if they are provided
        if stop is not None:
            # This is a bit hacky, but I can't figure out a better way to enforce
            # stop tokens when making calls to the sagemaker endpoint.
            text = enforce_stop_tokens(text, stop)

        return resp.get("outputs")[0]

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
    # TODO: replace with SagemakerEndpointStreaming
    genericModel = SagemakerEndpoint(
        endpoint_name = endpoint_name,
        region_name = region_name,
        content_handler = content_handler
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

        return input_str.encode('utf-8') 

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

        return input_str.encode('utf-8') 

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings

class SimilarityEnContentHandler(EmbeddingsContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt, model_kwargs={}) -> bytes:
        # add bge_prompt to each element in prompt
        new_prompt = [p for p in prompt]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})
        return input_str.encode('utf-8') 

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
        new_prompt = ["Represent this sentence for searching relevant passages:" + p for p in prompt]
        input_str = json.dumps({"inputs": new_prompt, **model_kwargs})

        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        embeddings = response_json["sentence_embeddings"]
        if len(embeddings) == 1:
            return [embeddings[0]]

        return embeddings

def create_sagemaker_embeddings_from_js_model_dgr(embeddings_model_endpoint_name: str, aws_region: str, lang: str = "zh", type: str = "similarity") -> SagemakerEndpointEmbeddingsJumpStartDGR:
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
    logger.info(f'content_handler: {content_handler}, embeddings_model_endpoint_name: {embeddings_model_endpoint_name}, aws_region: {aws_region}')
    # note the name of the LLM Sagemaker endpoint, this is the model that we would
    # be using for generating the embeddings
    embeddings = SagemakerEndpointEmbeddingsJumpStartDGR(
        endpoint_name = embeddings_model_endpoint_name,
        region_name = aws_region,
        content_handler = content_handler
    )
    return embeddings