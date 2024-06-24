from djl_python import Input, Output
import torch
import logging
import math
import time 
import os
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer, AutoModel
from FlagEmbedding import FlagReranker

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'--device={device}')


def load_model(properties):
    # tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")

    model = FlagReranker(model_location, use_fp16=True,device=str(device)) 
    
    return model

model = None

def handle(inputs: Input):
    global model
    if not model:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    sentence_pairs = data["inputs"]
    batch_size = data.get("batch_size", 32)
    max_length = data.get("max_length", 512)
    request_time = data.get('request_time', None)
    start_time = time.time()
    if request_time is not None:
        logging.info(f"id: {start_time}, inputs: {len(sentence_pairs)}, request  waiting time: {start_time-request_time}")
    else:
        logging.info(f"id: {start_time}, inputs: {len(sentence_pairs)}")

    embeddings = model.compute_score(sentence_pairs,batch_size=batch_size,max_length=max_length)

    result = {"rerank_scores": embeddings,'response_time':time.time()}
    logging.info(f"id: {start_time}, execute time: {time.time()-start_time}s")
    return Output().add_as_json(result)