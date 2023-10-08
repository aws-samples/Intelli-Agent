from djl_python import Input, Output
import torch
import logging
import math
import os
from sentence_transformers import SentenceTransformer

def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")

    model = SentenceTransformer(model_location)
    
    return model

model = None

def handle(inputs: Input):
    global model
    if not model:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    input_sentences = None
    inputs = data["inputs"]
    if isinstance(inputs, list):
        input_sentences = inputs
    else:
        input_sentences =  [inputs]
    logging.info(f"inputs: {input_sentences}")

    sentence_embeddings =  model.encode(input_sentences, normalize_embeddings=True)
        
    result = {"sentence_embeddings": sentence_embeddings}
    return Output().add_as_json(result)
