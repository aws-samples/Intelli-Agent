import boto3 
import json 
import os 

# from llmbot_utils import concat_recall_knowledge
from typing import Any, List, Mapping, Optional

from langchain.llms.base import LLM
from langchain.llms.sagemaker_endpoint import LLMContentHandler
from langchain.llms import Bedrock

from langchain_community.chat_models import BedrockChat
from langchain_community.llms.sagemaker_endpoint import LineIterator
from ..constant import HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE

class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == 'Model' or new_cls.model_id is None:
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls
    
class Model(metaclass=ModelMeta):
    model_id = None
    model_map = {}
    @classmethod
    def get_model(cls,model_id,model_kwargs=None, **kwargs):
        return cls.model_map[model_id].create_model(
            model_kwargs=model_kwargs, **kwargs
        )

class Claude2(Model):
    model_id = 'anthropic.claude-v2'
    default_model_kwargs = {
            "max_tokens_to_sample": 2000,
            "temperature": 0.7,
            "top_p": 0.9
        }

    @classmethod
    def create_model(cls,model_kwargs=None, **kwargs
        ):
        model_kwargs  = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}

        credentials_profile_name = kwargs.get('credentials_profile_name',None) \
                    or os.environ.get('AWS_PROFILE',None) or None 
        region_name = kwargs.get('region_name',None) \
            or os.environ.get('AWS_REGION', None) or None
        return_chat_model=kwargs.get('return_chat_model',False)
        if return_chat_model:
            llm = BedrockChat(
                        credentials_profile_name=credentials_profile_name,
                        region_name=region_name,
                        model_id=cls.model_id,
                        model_kwargs=model_kwargs
            )
        else:
            llm = Bedrock(
                        credentials_profile_name=credentials_profile_name,
                        region_name=region_name,
                        model_id=cls.model_id,
                        model_kwargs=model_kwargs
            )

        return llm

class ClaudeInstance(Claude2):
    model_id = 'anthropic.claude-instant-v1'

class Claude21(Claude2):
    model_id = 'anthropic.claude-v2:1'


class SagemakerModelBase(Model):
    default_model_kwargs = None
    content_type = "application/json"
    accepts = "application/json"
    
    @classmethod
    def create_client(cls,region_name):
        client = boto3.client(
            "sagemaker-runtime",
            region_name=region_name
        )
        return client

    def __init__(self,model_kwargs=None,**kwargs) -> None:
        self.model_kwargs = model_kwargs or {}
        if self.default_model_kwargs is not None:
            self.model_kwargs = {**self.default_model_kwargs,**self.model_kwargs}
        
        self.region_name = kwargs.get('region_name',None) \
            or os.environ.get('AWS_REGION', None) or None
        self.kwargs = kwargs
        self.endpoint_name = kwargs['endpoint_name']
        self.client = self.create_client(self.region_name)
        
    @classmethod
    def create_model(cls,model_kwargs=None,**kwargs):
        return cls(model_kwargs=model_kwargs,**kwargs)

    def transform_input(self,x):
        raise NotImplementedError
    
    def transform_output(self,output):
        response = json.loads(output.read().decode("utf-8"))
        return response

    def _stream(self,x):
        body = self.transform_input(x)
        resp = self.client.invoke_endpoint_with_response_stream(
                    EndpointName=self.endpoint_name,
                    Body=body,
                    ContentType=self.content_type,
                )
        iterator = LineIterator(resp["Body"])
        for line in iterator:
            resp = json.loads(line)
            resp_output = resp.get("outputs")
            yield resp_output
    
    def _invoke(self,x):
        body = self.transform_input(x)
        try:
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                Body=body,
                ContentType=self.content_type,
                Accept=self.accepts,
            )
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")
        response = self.transform_output(response["Body"])
        return response
    def invoke(self,x,stream=False):
        x['stream'] = stream
        if stream:
            return self._stream(x)
        else:
            return self._invoke(x)

class Baichuan2Chat13B4Bits(SagemakerModelBase):
    model_id = "Baichuan2-13B-Chat-4bits"
    # content_handler=Baichuan2ContentHandlerChat()
    default_model_kwargs = {
            "max_new_tokens": 2048,
            "temperature": 0.3,
            "top_k": 5,
            "top_p": 0.85,
            "repetition_penalty": 1.05,
            "do_sample": True,
            "timeout":60
        }
    def transform_input(self, x):
        query = x['query']
        _chat_history = x['chat_history']
        _chat_history = [{"role":message.type,"content":message.content} for message in _chat_history]
        
        chat_history = []
        for message in _chat_history:
            content = message['content']
            role = message['role']
            assert role in [HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE],f'invalid role: {role}'
            if role == AI_MESSAGE_TYPE:
                role = 'assistant'  
            elif role == HUMAN_MESSAGE_TYPE:
                role = 'user'      
            
            chat_history.append({
                "role":role,
                "content":content
            })  
        _messages = chat_history + [{
                "role": "user",
                "content": query
            }] 
        messages = []
        system_messages = []
        for message in _messages:
            if message['role'] == SYSTEM_MESSAGE_TYPE:
                system_messages.append(message)
            else:
                messages.append(message)
        
        if system_messages:
            system_prompt = "\n".join([s['content'] for s in system_messages])
            first_content = messages[0]['content']
            messages[0]['content'] = f'{system_prompt}\n{first_content}'

        input_str = json.dumps({
            "messages" : messages,
            "parameters" : {"stream":x['stream'],**self.model_kwargs}
        })
        return input_str


class Internlm2Chat7B(SagemakerModelBase):
    model_id = "internlm2-chat-7b"
    default_model_kwargs = {
            "max_new_tokens": 1024,
            "timeout":60,
            "do_sample":True,
            "temperature": 0.1,
            "top_p": 0.8
        }
    
    def transform_input(self, x):
        chat_history = x['chat_history']
        assert len(chat_history) % 2 == 0, chat_history
        history = []
        for i in range(0,len(chat_history),2):
            user_message = chat_history[i]
            ai_message = chat_history[i+1]
            assert user_message.type == HUMAN_MESSAGE_TYPE \
                  and ai_message.type == AI_MESSAGE_TYPE , chat_history
            history.append((user_message.content,ai_message.content))
        body = {
            "query": x['_query'],
            "meta_instruction": x['meta_instruction'],
            "stream": x['stream'],
            "history": history
        }
        body.update(self.model_kwargs)
        input_str = json.dumps(body)
        return input_str