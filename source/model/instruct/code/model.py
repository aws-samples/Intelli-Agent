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
import os
import torch
import json
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from transformers.generation.utils import GenerationConfig

@torch.no_grad()
def _stream_chat(
    self,
    tokenizer,
    query: str,
    history: List[Tuple[str, str]] = [],
    max_new_tokens: int = 1024,
    do_sample: bool = True,
    temperature: float = 0.8,
    top_p: float = 0.8,
    timeout=60,
    **kwargs,
):
    """
    Return a generator in format: (response, history)
    Eg.
    ('你好，有什么可以帮助您的吗', [('你好', '你好，有什么可以帮助您的吗')])
    ('你好，有什么可以帮助您的吗？', [('你好', '你好，有什么可以帮助您的吗？')])
    """
    if BaseStreamer is None:
        raise ModuleNotFoundError(
            "The version of `transformers` is too low. Please make sure "
            "that you have installed `transformers>=4.28.0`."
        )

    response_queue = queue.Queue(maxsize=20)

    class ChatStreamer(BaseStreamer):
        def __init__(self, tokenizer) -> None:
            super().__init__()
            self.tokenizer = tokenizer
            self.queue = response_queue
            self.query = query
            self.history = history
            self.response = ""
            self.cache = []
            self.received_inputs = False
            self.queue.put((self.response, history + [(self.query, self.response)]))

        def put(self, value):
            if len(value.shape) > 1 and value.shape[0] > 1:
                raise ValueError("ChatStreamer only supports batch size 1")
            elif len(value.shape) > 1:
                value = value[0]

            if not self.received_inputs:
                # The first received value is input_ids, ignore here
                self.received_inputs = True
                return

            self.cache.extend(value.tolist())
            token = self.tokenizer.decode(self.cache, skip_special_tokens=True)
            if token.strip() != "<|im_end|>":
                self.response = self.response + token
                history = self.history + [(self.query, self.response)]
                self.queue.put((self.response, history))
                self.cache = []
            else:
                self.end()

        def end(self):
            self.queue.put(None)

    def stream_producer():
        # new code added
        try:
            return self.chat(
                tokenizer=tokenizer,
                query=query,
                streamer=ChatStreamer(tokenizer=tokenizer),
                history=history,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature,
                top_p=top_p,
                **kwargs,
            )
        except BaseException as e:
            response_queue.put(e)
            return
            
    def consumer():
        producer = threading.Thread(target=stream_producer)
        producer.daemon = True
        producer.start()
        start_time = time.time()
        while True:
            try:
                res = response_queue.get(timeout=timeout-(time.time()-start_time))
            except queue.Empty:
                error = f'TimeoutError: exceed the max generation time {timeout}s.'
                print(error)
                error = json.dumps({"error_msg":error}) + "\n"
                raise RuntimeError(error)
                # raise TimeoutError(f'max generate time is set as: {timeout}s')
            if res is None:
                return 
            if isinstance(res,BaseException):
                raise res
            yield res
    return consumer()

def stream_chat(model,tokenizer,**kwargs):
    try:
        response = _stream_chat(
            model,
            tokenizer,
            **kwargs
        )
        history = ""
        for i in response:
            yield i[0][len(history):]
            history = i[0]
    finally: 
        traceback.clear_frames(sys.exc_info()[2])
        gc.collect()
        torch.cuda.empty_cache()
        if 'response' in locals():
            response.close()
              
def generate(model,tokenizer,stream=False,**kwargs):
    generator = stream_chat(model,tokenizer,**kwargs)
    if stream:
        return generator
    r = ''
    for rr in generator:
        r += rr 
    return r


tokenizer = None
model = None

attn_implementation = os.environ.get('attn_implementation','eager')

def get_model(properties):
    model_dir =  properties['model_dir']
    model_path = os.path.join(model_dir, 'hf_model/')
    if "model_id" in properties:
        model_path = properties['model_id']
    print('properties',properties)
    print('model_path',model_path)
    # local_rank = int(os.getenv('LOCAL_RANK', '0'))
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        load_in_4bit=True,
        attn_implementation=attn_implementation,
        device_map='auto',
        )
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True,use_fast=True
        )
    model = model.eval()
    return tokenizer, model

def handle(inputs: Input) -> None:
    torch.cuda.empty_cache()
    global tokenizer, model
    if tokenizer is None or model is None:
        tokenizer, model = get_model(inputs.get_properties())

    if inputs.is_empty():
        # Model server makes an empty call to warmup the model on startup
        return None
    body = inputs.get_as_json()
    print('body: ',body)
    stream = body.get('stream',False)
    response = generate(model,tokenizer,**body)
    if stream:
        return Output().add_stream_content(response,output_formatter=Output._default_stream_output_formatter)
    else:
        return Output().add_as_json(response)