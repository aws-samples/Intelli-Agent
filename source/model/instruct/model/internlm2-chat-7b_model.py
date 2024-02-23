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
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from transformers.generation.utils import GenerationConfig
import traceback

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
            return _chat(
                model,
                tokenizer=tokenizer,
                query=query,
                streamer=ChatStreamer(tokenizer=tokenizer),
#                 history=history,
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
                raise TimeoutError(f'max generate time is set as: {timeout}s')
            if res is None:
                return 
            if isinstance(res,BaseException):
                raise res
            yield res
    return consumer()



def build_prompt(tokenizer, query: str, history: List[Tuple[str, str]] = [], meta_instruction=None):
    if tokenizer.add_bos_token:
        prompt = ""
    else:
        prompt = tokenizer.bos_token
    if meta_instruction:
        prompt += f"""<|im_start|>system\n{meta_instruction}<|im_end|>\n"""
    for record in history:
        prompt += f"""<|im_start|>user\n{record[0]}<|im_end|>\n<|im_start|>assistant\n{record[1]}<|im_end|>\n"""
    prompt += f"""<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"""
    return prompt


@torch.no_grad()
def _chat(
    self,
    tokenizer,
    query: str,
#     history: List[Tuple[str, str]] = [],
    streamer = None,
    max_new_tokens: int = 1024,
    do_sample: bool = True,
    temperature: float = 0.8,
    top_p: float = 0.8,
    stop_tokens:list[str] = None,
#     meta_instruction: str = "You are an AI assistant whose name is InternLM (书生·浦语).\n"
#     "- InternLM (书生·浦语) is a conversational language model that is developed by Shanghai AI Laboratory (上海人工智能实验室). It is designed to be helpful, honest, and harmless.\n"
#     "- InternLM (书生·浦语) can understand and communicate fluently in the language chosen by the user such as English and 中文.",
    **kwargs,
):
    inputs = tokenizer([query], return_tensors="pt")
    inputs = {k: v.to(self.device) for k, v in inputs.items() if torch.is_tensor(v)}
    # also add end-of-assistant token in eos token id to avoid unnecessary generation
    eos_token_id = [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids(["<|im_end|>"])[0]]
    if stop_tokens:
        assert isinstance(stop_tokens,list),stop_tokens
        for token in stop_tokens:
            token_ids = tokenizer.convert_tokens_to_ids([token])
            assert len(token_ids) == 1, f'invalid stop token: {token}'
            eos_token_id.append(token_ids[0])
        
        
    outputs = self.generate(
        **inputs,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=do_sample,
        temperature=temperature,
        top_p=top_p,
        eos_token_id=eos_token_id,
        **kwargs,
    )
    outputs = outputs[0].cpu().tolist()[len(inputs["input_ids"][0]) :]
    response = tokenizer.decode(outputs, skip_special_tokens=True)
    response = response.split("<|im_end|>")[0]
    history = history + [(query, response)]
    return response, history


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
        model_path, trust_remote_code=True,use_fast=False
        )
    model = model.eval()
    return tokenizer, model

def _default_stream_output_formatter(token_texts):
    if isinstance(token_texts,Exception):
        token_texts = {'error_msg':str(token_texts)}
    else:
        token_texts = {"outputs": token_texts}
    json_encoded_str = json.dumps(token_texts) + "\n"
    return bytearray(json_encoded_str.encode("utf-8"))

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
        return Output().add_stream_content(response,output_formatter=_default_stream_output_formatter)
    else:
        return Output().add_as_json(response)