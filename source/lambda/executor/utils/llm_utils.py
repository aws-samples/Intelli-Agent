import boto3 
import json 
import os 
import requests 
import re
import traceback

from sm_utils import SagemakerEndpointVectorOrCross
from llmbot_utils import concat_recall_knowledge
from typing import Any, List, Mapping, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.llms import Bedrock

from prompt_template import claude2_rag_template_render, \
    claude2_rag_api_postprocess, claude2_rag_stream_postprocess, \
        claude_chat_template_render
    
import prompt_template  

from response_utils import api_response, stream_response

from langchain.schema.runnable import RunnableLambda
from constant import IntentType


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if name == 'Model':
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls
    
class Model(metaclass=ModelMeta):
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

class CSDCDGRModel(Model):
    model_id = 'csdc-internlm-7b'
    @classmethod
    def generate(
        cls,
        query:str,
        contexts:list,
        history,
        llm_model_endpoint,
        region_name,
        parameters,
        context_trunc_length:int=2560,
        model_type="answer",
        context_num=2,
        **kwargs
        ):
    
        # generate_answer
        recall_knowledge_str = concat_recall_knowledge(contexts[:context_num])
        answer = SagemakerEndpointVectorOrCross(prompt=query,
                                                endpoint_name=llm_model_endpoint,
                                                region_name=region_name,
                                                model_type=model_type,
                                                stop=None,
                                                history=history,
                                                parameters=parameters,
                                                context=recall_knowledge_str[:context_trunc_length])
        ret = {"prompt": query, "context": recall_knowledge_str, "answer": answer}
    
        return ret



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
    template_render = claude2_rag_template_render
    stream_postprocess = claude2_rag_stream_postprocess
    api_postprocess = claude2_rag_api_postprocess

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        prompt = RunnableLambda(
            lambda x: cls.template_render(x['query'],x['contexts'])
            )
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        stream = kwargs.get('stream',False)
        if stream:
            llm_fn = RunnableLambda(llm.stream)
            postprocess_fn = RunnableLambda(cls.stream_postprocess)
        else:
            llm_fn = RunnableLambda(llm.predict)
            postprocess_fn = RunnableLambda(cls.api_postprocess)
        
        chain = prompt | llm_fn | postprocess_fn
        return chain 

class Claude21RagLLMChain(Claude2RagLLMChain):
    model_id = 'anthropic.claude-v2:1'
    template_render = prompt_template.claude21_rag_template_render 
    stream_postprocess = prompt_template.claude21_rag_stream_postprocess 
    api_postprocess = prompt_template.claude21_rag_api_postprocess


class ClaudeRagInstance(Claude2RagLLMChain):
    model_id = 'anthropic.claude-instant-v1'
    template_render = prompt_template.claude2_rag_template_render
    stream_postprocess = prompt_template.claude2_rag_stream_postprocess
    api_postprocess = prompt_template.claude2_rag_api_postprocess



class Claude2ChatChain(LLMChain):
    model_id = 'anthropic.claude-v2'
    intent_type = IntentType.CHAT.value
    template_render = prompt_template.claude_chat_template_render

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        prompt = RunnableLambda(
            lambda x: cls.template_render(x['query'])
            )
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )
        stream = kwargs.get('stream',False)
        if stream:
            llm_fn = RunnableLambda(llm.stream)
        else:
            llm_fn = RunnableLambda(llm.predict)
        chain = prompt | llm_fn
        return chain 

class Claude21ChatChain(Claude2ChatChain):
    model_id = 'anthropic.claude-v2:1'

class ClaudeInstanceChatChain(Claude2ChatChain):
    model_id = 'anthropic.claude-instant-v1'

def get_llm_chain(model_id, intent_type,model_kwargs=None, **kwargs):
    return LLMChain.get_chain(
        model_id,
        intent_type,
        model_kwargs=model_kwargs,
        **kwargs
    )
