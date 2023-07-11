import json
import re

def enforce_stop_tokens(text, stop) -> str:
    """Cut off the text as soon as any stop words occur."""
    if stop is None:
        return text
    
    return re.split("|".join(stop), text)[0]

def get_vector_by_sm_endpoint(questions, sm_client, endpoint_name):
    parameters = {
        "max_new_tokens": 50,
        "temperature": 0,
        "min_length": 10,
        "no_repeat_ngram_size": 2,
    }

    response_model = sm_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": questions,
                "parameters": parameters
            }
        ),
        ContentType="application/json",
    )
    json_str = response_model['Body'].read().decode('utf8')
    json_obj = json.loads(json_str)
    embeddings = json_obj['sentence_embeddings']
    return embeddings

def generate_answer(smr_client, llm_endpoint, prompt, llm_name, stop=None, history=[]):
    answer = None
    if llm_name == "chatglm":
        parameters = {
        "max_length": 2048,
        "temperature": 0.01,
        "num_beams": 1, # >1可能会报错，"probability tensor contains either `inf`, `nan` or element < 0"； 即使remove_invalid_values=True也不能解决
        "do_sample": False,
        "top_p": 0.7,
        "logits_processor" : None,
        # "remove_invalid_values" : True
        }
        response_model = smr_client.invoke_endpoint(
            EndpointName=llm_endpoint,
            Body=json.dumps(
            {
                "inputs": prompt,
                "parameters": parameters,
                "history" : history
            }
            ),
            ContentType="application/json",
        )

        json_ret = json.loads(response_model['Body'].read().decode('utf8'))

        answer = json_ret['outputs']
    elif llm_name == "bloomz":
        parameters = {
            # "early_stopping": True,
            "length_penalty": 1.0,
            "max_new_tokens": 200,
            "temperature": 0,
            "min_length": 20,
            "no_repeat_ngram_size": 200,
            # "eos_token_id": ['\n']
        }

        response_model = smr_client.invoke_endpoint(
            EndpointName=llm_endpoint,
            Body=json.dumps(
                {
                    "inputs": prompt,
                    "parameters": parameters
                }
            ),
            ContentType="application/json",
        )
        
        json_ret = json.loads(response_model['Body'].read().decode('utf8'))
        answer = json_ret['outputs'][len(prompt):]

    return enforce_stop_tokens(answer, stop)