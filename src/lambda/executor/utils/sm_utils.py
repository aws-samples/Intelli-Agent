import json
import re
from langchain.llms.sagemaker_endpoint import LLMContentHandler, SagemakerEndpoint
from typing import Dict, List

def enforce_stop_tokens(text, stop) -> str:
    """Cut off the text as soon as any stop words occur."""
    if stop is None:
        return text
    
    return re.split("|".join(stop), text)[0]

class vectorContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt, **model_kwargs})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['sentence_embeddings']

class crossContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt["inputs"], "docs":prompt["docs"] **model_kwargs})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['scores'][0][1]

class crossContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt["inputs"], "docs":prompt["docs"] **model_kwargs})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['outputs']

class answerContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt["inputs"],
                                "history":prompt["history"],
                                "parameters":prompt["parameters"],
                                "context":prompt["context"],
                                 **model_kwargs})
        return input_str.encode('utf-8')

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json['scores'][0][1]

def SagemakerEndpointVectorOrCross(prompt: str, endpoint_name: str, region_name: str, model_type: str, stop: List[str]) -> SagemakerEndpoint:
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
    elif model_type == "cross":
        content_handler = crossContentHandler()
    elif model_type == "answer":
        content_handler = answerContentHandler()
    genericModel = SagemakerEndpoint(
        endpoint_name = endpoint_name,
        region_name = region_name,
        content_handler = content_handler
    )
    return genericModel(prompt=prompt, stop=stop)

# will be deprecated in the future
def get_vector_by_sm_endpoint(questions, sm_client, endpoint_name):
    '''
    Get the embedding vector of input question.
    '''
    response_model = sm_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": questions
            }
        ),
        ContentType="application/json",
    )
    json_str = response_model['Body'].read().decode('utf8')
    json_obj = json.loads(json_str)
    embeddings = json_obj['sentence_embeddings']
    return embeddings

# will be deprecated in the future
def get_cross_by_sm_endpoint(question, doc, sm_client, endpoint_name):
    '''
    Get the embedding vector of input question.
    '''
    response_model = sm_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": question,
                "docs": doc
            }
        ),
        ContentType="application/json",
    )
    json_str = response_model['Body'].read().decode('utf8')
    json_obj = json.loads(json_str)
    return json_obj['scores'][0][1]

# will be deprecated in the future
def generate_answer(smr_client, llm_endpoint, question, context, stop=None, history=[], parameters = {}, existing_answer=""):
    '''
    generate answer by passing question and parameters to LLM model
    :param llm_endpoint: model endpoint
    :param question: input question
    :param context: document got from opensearch
    :param history: session history
    :param existing_answer: existing answer used for refine
    '''
    answer = None
    response_model = smr_client.invoke_endpoint(
        EndpointName=llm_endpoint,
        Body=json.dumps(
        {
            "inputs": question,
            "history" : history,
            "parameters": parameters,
            "context": context
        }
        ),
        ContentType="application/json",
    )

    json_ret = json.loads(response_model['Body'].read().decode('utf8'))

    answer = json_ret['outputs']

    return enforce_stop_tokens(answer, stop)