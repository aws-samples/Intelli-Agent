import time
import sys, os
os.environ['PYTHONUNBUFFERED'] = "1"
import traceback
import sys
import torch
import gc
from typing import List,Tuple
import logging
try:
    from transformers.generation.streamers import BaseStreamer
except:  # noqa # pylint: disable=bare-except
    BaseStreamer = None
import queue
import threading
import time 
from queue import  Empty
from djl_python import Input, Output
import torch
import json
import types
import threading 
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
# from transformers.generation.utils import GenerationConfig
import traceback
from transformers import AutoTokenizer,GPTQConfig,AutoModelForCausalLM

from exllamav2 import (
    ExLlamaV2,
    ExLlamaV2Config,
    ExLlamaV2Cache,
    ExLlamaV2Tokenizer,
)

from exllamav2.generator import (
    ExLlamaV2StreamingGenerator,
    ExLlamaV2Sampler
)
handle_lock = threading.Lock()
logger = logging.getLogger("sagemaker-inference")
logger.info(f'logger handlers: {logger.handlers}')

generator = None
tokenizer = None


def new_decode(self, ids, decode_special_tokens = False):
    ori_decode = tokenizer.decode
    return ori_decode(ids, decode_special_tokens = True)

def get_model(properties):
    model_dir =  properties['model_dir']
    model_path = os.path.join(model_dir, 'hf_model/')
    if "model_id" in properties:
        model_path = properties['model_id']
    logger.info(f'properties: {properties}')
    logger.info(f'model_path: {model_path}')
    # local_rank = int(os.getenv('LOCAL_RANK', '0'))
    model_directory = model_path

    config = ExLlamaV2Config()
    config.model_dir = model_directory
    config.prepare()

    model = ExLlamaV2(config)
    logger.info("Loading model: " + model_directory)

    cache = ExLlamaV2Cache(model, lazy = True)
    model.load_autosplit(cache)

    tokenizer = ExLlamaV2Tokenizer(config)

    generator = ExLlamaV2StreamingGenerator(model, cache, tokenizer)
        
    return tokenizer,generator

def _default_stream_output_formatter(token_texts):
    if isinstance(token_texts,Exception):
        token_texts = {'error_msg':str(token_texts)}
    else:
        token_texts = {"outputs": token_texts}
    json_encoded_str = json.dumps(token_texts) + "\n"
    return bytearray(json_encoded_str.encode("utf-8"))

def generate(**body):
    query = body.pop('query')
    stream = body.pop('stream',False)
    stop_words = body.pop('stop_tokens',None)
    
    stop_token_ids = [
        tokenizer.eos_token_id,
        tokenizer.encode('<|im_end|>',encode_special_tokens=True).tolist()[0][0]
    ]

    if stop_words:
        assert isinstance(stop_words,list), stop_words
        for stop_word in stop_words:
            stop_token_ids.append(tokenizer.encode(stop_word,encode_special_tokens=True).tolist()[0][0])
        
    # body.update({"do_preprocess": False})
    timeout = body.pop('timeout',60)
    settings = ExLlamaV2Sampler.Settings()
    settings.temperature = body.get('temperature',0.1)
    settings.top_k = body.get('top_k',50)
    settings.top_p = body.get('top_p',0.8) 
    settings.top_a = body.get('top_a',0.0)
    settings.token_repetition_penalty = 1.0
    # tokenizer.convert_tokens_to_ids(["<|im_end|>"])[0]
    # settings.disallow_tokens(tokenizer, [tokenizer.eos_token_id])
    max_new_tokens = body.get('max_new_tokens',500)
    input_ids = tokenizer.encode(query,encode_special_tokens=True,add_bos=True)
    prompt_tokens = input_ids.shape[-1] 
    generator.warmup()
    generator.set_stop_conditions(stop_token_ids)

    generator.begin_stream(input_ids, settings)

    def _generator_helper():
        try:
            generated_tokens = 0
            while True:
                chunk, eos, _ = generator.stream()
                generated_tokens += 1
                yield chunk
                if eos or generated_tokens == max_new_tokens: break
            
        finally: 
            traceback.clear_frames(sys.exc_info()[2])
            gc.collect()
            torch.cuda.empty_cache()

    stream_generator = _generator_helper()
    if stream:
        return stream_generator
    r = ""
    for i in stream_generator:
        r += i
    return r
    

def _handle(inputs) -> None:
    if inputs.is_empty():
        logger.info('inputs is empty')
        # Model server makes an empty call to warmup the model on startup
        return None
    torch.cuda.empty_cache()
    body = inputs.get_as_json()
    stream = body.get('stream',False)
    logger.info(f'body: {body}')
    response = generate(**body)
    if stream:
        return Output().add_stream_content(response,output_formatter=_default_stream_output_formatter)
    else:
        return Output().add_as_json(response)


def handle(inputs: Input) -> None:
    task_request_time = time.time()
    logger.info(f'recieve request task: {task_request_time},{inputs}')
    with handle_lock:
        global generator,tokenizer
        if generator is None:
            tokenizer, generator = get_model(inputs.get_properties())
            tokenizer.decode = types.MethodType(new_decode, tokenizer) 
        logger.info(f'executing request task, wait time: {time.time()-task_request_time}s')
        return _handle(inputs)
        
        
