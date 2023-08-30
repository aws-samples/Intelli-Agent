from djl_python import Input, Output
import torch
import logging
import math
import os
import json
from vllm import LLM, SamplingParams


def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    llm = LLM(model=str(model_location), trust_remote_code=True)
    
    return llm


llm = None
generator = None


def handle(inputs: Input):
    global llm
    if not llm:
        llm = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    query = data["inputs"]
    params = data["parameters"]
    params["stop"] = params.get('stop', []) + ['<eoa>']
    params["max_tokens"] = params.get('max_tokens', 2048)
    history = data["history"]
    
    prompt = ""
    for record in history:
        prompt += f"""<s><|User|>:{record[0]}<eoh>\n<|Bot|>:{record[1]}<eoa>\n"""
    if len(prompt) == 0:
        prompt += "<s>"
    prompt += f"""<|User|>:{query}<eoh>\n<|Bot|>:"""
    sampling_params = SamplingParams(**params)
    outputs = llm.generate(prompt, sampling_params, use_tqdm=False)
    response = outputs[0].outputs[0].text
    
    result = {"outputs": response}
    return Output().add_as_json(result)