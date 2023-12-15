from djl_python import Input, Output
import torch
import logging
import math
import os
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer, AutoModel

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f'--device={device}')


def load_model(properties):
    tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties['model_dir']
    if "model_id" in properties:
        model_location = properties['model_id']
    logging.info(f"Loading model in {model_location}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_location, trust_remote_code=True)
    # tokenizer.padding_side = 'right'
    # model = AutoModelForSequenceClassification.from_pretrained(
    #     model_location, 
    #     # device_map="balanced_low_0", 
    #     trust_remote_code=True
    # ).half()
    model = AutoModelForSequenceClassification.from_pretrained(
        model_location, 
        # device_map="balanced_low_0", 
        trust_remote_code=True
    )
    # load the model on GPU
    model.to(device) 
    # model.requires_grad_(False)
    model.eval()
    
    return model, tokenizer


model = None
tokenizer = None
generator = None

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0].to(device) #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float().to(device)
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def handle(inputs: Input):
    global model, tokenizer
    if not model:
        model, tokenizer = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    input_sentences = data["inputs"]
    logging.info(f"len of inputs: {len(input_sentences)}")
    
    # Compute token embeddings
    with torch.no_grad():
        encoded_input = tokenizer(input_sentences, padding=True, truncation=True, return_tensors='pt', max_length=512).to(device)
        scores = model(**encoded_input, return_dict=True).logits.view(-1, ).float()
        # model_output = model(**encoded_input)
        # sentence_embeddings = model_output[0][:, 0]

    output = scores.cpu().numpy()
    
    result = {"rerank_scores": output}
    return Output().add_as_json(result)