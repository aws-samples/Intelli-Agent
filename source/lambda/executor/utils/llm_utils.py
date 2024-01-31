import boto3 
import json 
import os 
import requests 
import re
import traceback

from sm_utils import SagemakerEndpointVectorOrCross,SagemakerEndpointWithStreaming,SagemakerEndpointChat
from llmbot_utils import concat_recall_knowledge
from typing import Any, List, Mapping, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.llms.sagemaker_endpoint import LLMContentHandler
from langchain.llms import Bedrock

from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from constant import IntentType
from prompt_template import get_claude_chat_rag_prompt,get_chit_chat_prompt
from langchain_community.chat_models import BedrockChat


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
        model_kwargs  = model_kwargs or cls.default_model_kwargs

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
    # content_handler=None

    @classmethod
    def create_model(cls,model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs  = {**cls.default_model_kwargs,**model_kwargs}
        region_name = kwargs.get('region_name',None) \
            or os.environ.get('AWS_REGION', None) or None
        client = boto3.client(
            "sagemaker-runtime",
            region_name=region_name
        )
        endpoint_name = kwargs['endpoint_name']
        stream = kwargs.get('stream',False)
        # chat_history = kwargs.get('chat_history',[])
        model_kwargs['stream'] = stream
        model = SagemakerEndpointChat(
            client=client,
            endpoint_name=endpoint_name,
            # content_handler=cls.content_handler,
            streaming=stream,
            model_kwargs=model_kwargs,
            # chat_history=chat_history
        )
        return model

class Baichuan2ContentHandlerChat(LLMContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, prompt: str, chat_history:list, model_kwargs: dict) -> bytes:
            _messages = chat_history + [{
                "role":"user",
                "content": prompt
            }]

            messages = []
            system_messages = []
            for message in _messages:
                if message['role'] == 'system':
                    system_messages.append(message)
                else:
                    messages.append(message)
            
            if system_messages:
                system_prompt = "\n".join([s['content'] for s in system_messages])
                first_content = messages[0]['content']
                messages[0]['content'] = f'{system_prompt}\n{first_content}'

            input_str = json.dumps({
                "messages" : messages,
                "parameters" : {**model_kwargs}
            })


            return input_str.encode('utf-8')
        
        def transform_output(self, output: bytes) -> str: 
            response_json = json.loads(output.read().decode("utf-8"))
            return response_json

# class Baichuan2ContentHandlerRag(Baichuan2ContentHandlerChat):
#     def transform_input(self, prompt: str, chat_history:list, model_kwargs: dict) -> bytes:
#         assert len(chat_history) == 0
#         messages = chat_history + [{
#                 "role":"user",
#                 "content": prompt
#             }]
#         input_str = json.dumps({
#             "messages" : messages,
#             "parameters" : {**model_kwargs}
#         })
#         return input_str.encode('utf-8')

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
        }

class LLMChainMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == 'LLMChain':
            return new_cls
        new_cls.model_map[new_cls.get_chain_id()] = new_cls
        return new_cls
    
class LLMChain(metaclass=LLMChainMeta):
    model_map = {}
    @classmethod
    def get_chain_id(cls):
        return cls._get_chain_id(cls.model_id,cls.intent_type)
    
    @staticmethod
    def _get_chain_id(model_id,intent_type):
        return f"{model_id}__{intent_type}"


    @classmethod
    def get_chain(cls,model_id,intent_type,model_kwargs=None, **kwargs):
        return cls.model_map[cls._get_chain_id(model_id,intent_type)].create_chain(
            model_kwargs=model_kwargs, **kwargs
        )
    
class Claude2RagLLMChain(LLMChain):
    model_id = 'anthropic.claude-v2'
    intent_type = IntentType.KNOWLEDGE_QA.value
    # template_render = claude2_rag_template_render
    # stream_postprocess = claude2_rag_stream_postprocess
    # api_postprocess = claude2_rag_api_postprocess

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        chat_history = kwargs.get('chat_history',[])
        prompt = get_claude_chat_rag_prompt(chat_history)
        # prompt = RunnableLambda(
        #     lambda x: cls.template_render(x['query'],x['contexts'])
        #     )
        kwargs.update({'return_chat_model':True})
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )

        if stream:
            chain = prompt | RunnableLambda(lambda x: llm.stream(x.messages)) | RunnableLambda(lambda x:(i.content for i in x))
            # llm_fn = RunnableLambda(llm.stream)
        #     postprocess_fn = RunnableLambda(cls.stream_postprocess)
        else:
            chain = prompt | llm | RunnableLambda(lambda x:x.dict()['content'])
            # llm_fn = RunnableLambda(llm.predict)
        #     postprocess_fn = RunnableLambda(cls.api_postprocess)
        
        # chain = prompt | llm_fn | postprocess_fn
        return chain 

class Claude21RagLLMChain(Claude2RagLLMChain):
    model_id = 'anthropic.claude-v2:1'
    # template_render = prompt_template.claude21_rag_template_render 
    # stream_postprocess = prompt_template.claude21_rag_stream_postprocess 
    # api_postprocess = prompt_template.claude21_rag_api_postprocess

class ClaudeRagInstance(Claude2RagLLMChain):
    model_id = 'anthropic.claude-instant-v1'
    # template_render = prompt_template.claude2_rag_template_render
    # stream_postprocess = prompt_template.claude2_rag_stream_postprocess
    # api_postprocess = prompt_template.claude2_rag_api_postprocess

class Claude2ChatChain(LLMChain):
    model_id = 'anthropic.claude-v2'
    intent_type = IntentType.CHAT.value
    # template_render = prompt_template.claude_chat_template_render

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        chat_history = kwargs.get('chat_history',[])
        prompt = get_chit_chat_prompt(chat_history)
        # prompt = RunnableLambda(
        #     lambda x: cls.template_render(x['query'])
        #     )
        kwargs.update({'return_chat_model':True})
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )
        chain = prompt | llm

        if stream:
            chain = prompt | RunnableLambda(lambda x: llm.stream(x.messages)) | RunnableLambda(lambda x:(i.content for i in x))
            # llm_fn = RunnableLambda(llm.stream)
        #     postprocess_fn = RunnableLambda(cls.stream_postprocess)
        else:
            chain = prompt | llm | RunnableLambda(lambda x:x.dict()['content'])
            # llm_fn = RunnableLambda(llm.predict)
        #     postprocess_fn = RunnableLambda(cls.api_postprocess)
        
        # chain = prompt | llm_fn | postprocess_fn
        return chain 
        # stream = kwargs.get('stream',False)
        # if stream:
        #     llm_fn = RunnableLambda(llm.stream)
        # else:
        #     llm_fn = RunnableLambda(llm.predict)
        # chain = prompt | llm_fn
        # return chain 

class Claude21ChatChain(Claude2ChatChain):
    model_id = 'anthropic.claude-v2:1'

class ClaudeInstanceChatChain(Claude2ChatChain):
    model_id = 'anthropic.claude-instant-v1'

class Baichuan2Chat13B4BitsChatChain(LLMChain):
    model_id = "Baichuan2-13B-Chat-4bits"
    intent_type = IntentType.CHAT.value
    default_model_kwargs = {
        "max_new_tokens": 2048,
        "temperature": 0.3,
        "top_k": 5,
        "top_p": 0.85,
        "repetition_penalty": 1.05,
        "do_sample": True
    }
    @staticmethod
    def create_messages(query,_chat_history:list[tuple]):
        chat_history = []
        for message in _chat_history:
            content = message['content']
            role = message['role']
            assert role in ['user','ai','system'],f'invalid role: {role}'
            if message['role'] == 'ai':
                role = 'assistant'        
            chat_history.append({
                "role":role,
                "content":content
            })  
        _messages = chat_history + [{
                "role":"user",
                "content": query
            }] 
        messages = []
        system_messages = []
        for message in _messages:
            if message['role'] == 'system':
                system_messages.append(message)
            else:
                messages.append(message)
        
        if system_messages:
            system_prompt = "\n".join([s['content'] for s in system_messages])
            first_content = messages[0]['content']
            messages[0]['content'] = f'{system_prompt}\n{first_content}'
           
        return messages
     
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        chat_history = kwargs.pop('chat_history',[])
    
        model_kwargs = model_kwargs or {}
        model_kwargs.update({"stream": stream})
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        
        message_chain = RunnablePassthrough.assign(
            messages=RunnableLambda(lambda x: cls.create_messages(x['query'],chat_history))
            )

        if stream:
            llm_chain = message_chain | RunnableLambda(lambda x:llm._stream(x['messages']))
        else:
            llm_chain = message_chain | RunnableLambda(lambda x:llm._generate(x['messages']))
        return llm_chain
    

class Baichuan2Chat13B4BitsKnowledgeQaChain(Baichuan2Chat13B4BitsChatChain):
    model_id = "Baichuan2-13B-Chat-4bits"
    intent_type = IntentType.KNOWLEDGE_QA.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        chat_history = kwargs.pop('chat_history',[])

        def add_system_prompt(x):
            context = "\n".join(x['contexts'])
            _chat_history = chat_history +  [{
                "role":"system",
                "content":f"给定下面的背景知识:\n{context}\n回答下面的问题:\n"
                }]
            return _chat_history
    
        model_kwargs = model_kwargs or {}
        model_kwargs.update({"stream": stream})
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        message_chain = RunnablePassthrough.assign(
            chat_history=RunnableLambda(lambda x:add_system_prompt(x))
        ) | RunnablePassthrough.assign(
            messages=RunnableLambda(lambda x: cls.create_messages(x['query'],x['chat_history']))
            )

        if stream:
            llm_chain = message_chain | RunnableLambda(lambda x:llm._stream(x['messages']))
        else:
            llm_chain = message_chain | RunnableLambda(lambda x:llm._generate(x['messages']))
        return llm_chain


def get_llm_chain(model_id, intent_type,model_kwargs=None, **kwargs):
    return LLMChain.get_chain(
        model_id,
        intent_type,
        model_kwargs=model_kwargs,
        **kwargs
    )
