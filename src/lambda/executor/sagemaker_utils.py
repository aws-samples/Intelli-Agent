import json
import re

def enforce_stop_tokens(text, stop) -> str:
    """Cut off the text as soon as any stop words occur."""
    if stop is None:
        return text
    
    return re.split("|".join(stop), text)[0]

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

def generate_answer(smr_client, llm_endpoint, question, context, stop=None, history=[], existing_answer=""):
    '''
    generate answer by passing quesiton and parameters to LLM model
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
            "parameters": {},
            "context": context
        }
        ),
        ContentType="application/json",
    )

    json_ret = json.loads(response_model['Body'].read().decode('utf8'))

    answer = json_ret['outputs']

    return enforce_stop_tokens(answer, stop)