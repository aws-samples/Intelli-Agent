import os
os.environ['PYTHONUNBUFFERED'] = "1"
import traceback
import sys
import torch
import gc
from typing import List,Tuple
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
import logging
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
# from transformers.generation.utils import GenerationConfig
import traceback
from lmdeploy import pipeline, TurbomindEngineConfig,GenerationConfig
from lmdeploy.model import ChatTemplateConfig
import lmdeploy 
logger = logging.getLogger("sagemaker-inference")
request_lock = threading.Lock()


pipe = None

def get_model(properties):
    model_dir =  properties['model_dir']
    model_path = os.path.join(model_dir, 'hf_model/')
    if "model_id" in properties:
        model_path = properties['model_id']
    logger.info(f'properties: {properties}')
    logger.info(f'model_path: {model_path}')
    # local_rank = int(os.getenv('LOCAL_RANK', '0'))
    engine_config = TurbomindEngineConfig(
        model_format='awq',
        rope_scaling_factor=2.0,
        session_len=160000,
        cache_max_entry_count=0.2
    )
    pipe = pipeline(
        model_path,
        model_name="internlm2-chat-20b",
        backend_config=engine_config
    )
    return pipe

def _default_stream_output_formatter(token_texts):
    if isinstance(token_texts,Exception):
        token_texts = {'error_msg':str(token_texts)}
    else:
        token_texts = {"outputs": token_texts}
    json_encoded_str = json.dumps(token_texts) + "\n"
    return bytearray(json_encoded_str.encode("utf-8"))

def generate(pipe,**body):
    query = body.pop('query')
    stream = body.pop('stream',False)
    stop_words = body.pop('stop_tokens',None)
    if stop_words:
        assert isinstance(stop_words,list), stop_words
        body['stop_words'] = stop_words + ['<|im_end|>', '<|action_end|>']
    # body.update({"do_preprocess": False})
    timeout = body.pop('timeout',60)
    gen_config = GenerationConfig(**body)

    stream_generator = pipe.stream_infer([query],gen_config=gen_config,do_preprocess=False)

    def _generator_helper(gen):
        try:
            for i in gen:
                yield i.text
        finally: 
            traceback.clear_frames(sys.exc_info()[2])
            gc.collect()
            torch.cuda.empty_cache()
    stream_generator = _generator_helper(stream_generator)
    if stream:
        return stream_generator
    r = ""
    for i in stream_generator:
        r += i
    return r
    

def _handle(inputs: Input) -> None:
    torch.cuda.empty_cache()
    global pipe
    if pipe is None:
        pipe = get_model(inputs.get_properties())
    
    if inputs.is_empty():
        # Model server makes an empty call to warmup the model on startup
        return None
    body = inputs.get_as_json()
    
    logger.info(f'body: {body}')
    stream = body.get('stream',False)
    response = generate(pipe,**body)
    if stream:
        return Output().add_stream_content(response,output_formatter=_default_stream_output_formatter)
    else:
        return Output().add_as_json(response)


def handle(inputs: Input) -> None:
    task_request_time = time.time()
    logger.info(f'recieve request task: {task_request_time},{inputs}')
    with request_lock:
        logger.info(f'executing request task, wait time: {time.time()-task_request_time}s')
        return _handle(inputs)
