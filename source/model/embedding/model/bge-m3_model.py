import logging
import math
import os

import torch
from djl_python import Input, Output
from FlagEmbedding import BGEM3FlagModel
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer, pipeline

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"--device={device}")


def load_model(properties):
    # tensor_parallel = properties["tensor_parallel_degree"]
    model_location = properties["model_dir"]
    if "model_id" in properties:
        model_location = properties["model_id"]
    logging.info(f"Loading model in {model_location}")

    # tokenizer = AutoTokenizer.from_pretrained(model_location, trust_remote_code=True)
    # tokenizer.padding_side = 'right'
    # model = AutoModel.from_pretrained(
    #     model_location,
    #     # device_map="balanced_low_0",
    #     trust_remote_code=True
    # ).half()
    # # load the model on GPU
    # model.to(device)
    # model.requires_grad_(False)
    # model.eval()

    model = BGEM3FlagModel(
        model_location, use_fp16=True
    )  # Setting use_fp16 to True speeds up computation with a slight performance degradation

    return model


model = None
tokenizer = None
generator = None


def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0].to(
        device
    )  # First element of model_output contains all token embeddings
    input_mask_expanded = (
        attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float().to(device)
    )
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def handle(inputs: Input):
    global model
    if not model:
        model = load_model(inputs.get_properties())

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()

    input_sentences = data["inputs"]
    batch_size = data["batch_size"]
    max_length = data["max_length"]
    return_type = data["return_type"]

    logging.info(f"inputs: {input_sentences}")

    if return_type == "dense":
        encoding_results = model.encode(
            input_sentences, batch_size=batch_size, max_length=max_length
        )
    elif return_type == "sparse":
        encoding_results = model.encode(
            input_sentences,
            return_dense=False,
            return_sparse=True,
            return_colbert_vecs=False,
        )
    elif return_type == "colbert":
        encoding_results = model.encode(
            input_sentences,
            return_dense=False,
            return_sparse=False,
            return_colbert_vecs=True,
        )
    elif return_type == "all":
        encoding_results = model.encode(
            input_sentences,
            batch_size=batch_size,
            max_length=max_length,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True,
        )

    # encoding_results = [encoding_results]

    result = {"sentence_embeddings": encoding_results}
    return Output().add_as_json(result)
