from djl_python import Input, Output
import torch
import logging
import math
import os
import json
from transformers import AutoTokenizer, AutoModelForCausalLM

def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_location, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_location, trust_remote_code=True)
    model = model.eval().half().cuda()
    
    return model, tokenizer


model = None
tokenizer = None
generator = None

def stream_items(input_sentences, history, params):
    global model, tokenizer
    res_generator = model.stream_chat(tokenizer, input_sentences, history=history, **params)
    size = 0
    response = ""
    for response in res_generator:
        this_response = response[size:]
        size = len(response)
        stream_buffer = {"outputs":this_response, "finished": len(this_response)==0}
        yield stream_buffer

def handle(inputs: Input):
    global model, tokenizer
    if not model:
        model, tokenizer = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    input_sentences = data["inputs"]
    params = data["parameters"]
    history = data["history"]
    stream = data.get('stream', False)
    
    outputs = Output()
    if stream:
        outputs.add_property("content-type", "application/jsonlines")
        outputs.add_stream_content(stream_items(input_sentences, history, params))
    else:
        response = model.chat(tokenizer, input_sentences, history=history, **params)
        result = {"outputs": response}
        outputs.add_as_json(result)
    return outputs