from djl_python import Input, Output
import torch
import logging
import math
import os
import time
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, AutoModel

from transformers import AutoModel, AutoTokenizer
from BCEmbedding import EmbeddingModel

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'--device={device}')

def load_model(properties):
    # tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    # model = EmbeddingModel(model_location,  use_fp16=True,device=device) # Setting use_fp16 to True speeds up computation with a slight performance degradation
    # init model and tokenizer
    model = EmbeddingModel(model_name_or_path=model_location,use_fp16=True,device=str(device))
    return model

model = None

def handle(inputs: Input):
    global model, tokenizer
    if not model:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    input_sentences = data["inputs"]
    batch_size = data.get("batch_size", 100)
    max_length = data.get("max_length", 512)
    request_time = data.get('request_time', None)
    start_time = time.time()
    if request_time is not None:
        logging.info(f"id: {start_time}, inputs: {input_sentences}, request  waiting time: {start_time-request_time}")
    else:
        logging.info(f"id: {start_time}, inputs: {input_sentences}")

    embeddings = model.encode(input_sentences,batch_size=batch_size,max_length=max_length)

    result = {"sentence_embeddings": embeddings,'response_time':time.time()}
    logging.info(f"id: {start_time}, execute time: {time.time()-start_time}s")
    return Output().add_as_json(result)