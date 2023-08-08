from djl_python import Input, Output
import torch
import logging
import math
import os
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

    context = data.get('context', '')
    existing_answer = data.get('existing_answer', '')

    template_1 = '以下context xml tag内的文本内容为背景知识：\n<context>\n{context}\n</context>\n请根据背景知识, 回答这个问题：{question}'
    template_2 = '这是原始问题: {question}\n已有的回答: {existing_answer}\n\n现在context xml tag内的还有一些文本内容，（如果有需要）你可以根据它们完善现有的回答。\n<context>\n{context}\n</context>\n请根据新的文段，进一步完善你的回答。'
    
    if len(context) and len(existing_answer):
        prompt = template_2.format(context = context, question =input_sentences, existing_answer=existing_answer)
    elif len(context):
        prompt = template_1.format(context = context, question =input_sentences)
    else:
        prompt = input_sentences
    response, history = model.chat(tokenizer, prompt, history=history, **params)
    
    result = {"outputs": response, "history" : history}
    return Output().add_as_json(result)