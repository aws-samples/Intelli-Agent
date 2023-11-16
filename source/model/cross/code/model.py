from djl_python import Input, Output
import torch
import logging
import math
import os
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, AutoModel

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'--device={device}')


def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_location, use_fast=False)
    model = AutoModel.from_pretrained(
        model_location, 
        # device_map="balanced_low_0", 
        trust_remote_code=True
    ).half()
    # load the model on GPU
    model.to(device) 
    model.requires_grad_(False)
    model.eval()
    
    return model, tokenizer


model = None
tokenizer = None
generator = None

def handle(inputs: Input):
    global model, tokenizer
    if not model:
        model, tokenizer = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    queries = data["inputs"]
    docs = data["docs"]
    
    encoded_input = tokenizer(text = [queries], text_pair=[docs], padding=True, truncation=True, max_length=2048, return_tensors='pt')['input_ids'].to(device)
    # Compute token embeddings
    with torch.no_grad():
        model_output = model(input_ids=encoded_input)

    # Perform pooling. In this case, max pooling.

#     # preprocess
#     input_ids = tokenizer(input_sentences, return_tensors="pt").input_ids
#     # pass inputs with all kwargs in data
#     if params is not None:
#         outputs = model.generate(input_ids, **params)
#     else:
#         outputs = model.generate(input_ids)

#     # postprocess the prediction
#     prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    result = {"scores": model_output.cpu().numpy()}
    return Output().add_as_json(result)