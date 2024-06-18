# tool calling chain
import json
from typing import List,Dict,Any
import re
from datetime import datetime 

from langchain.schema.runnable import (
    RunnableLambda,
)

from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate

from langchain_core.messages import AIMessage,SystemMessage,HumanMessage

from common_utils.constant import (
    LLMTaskType
)

from ..llm_chain_base import LLMChain
from ...llm_models import Model


GLM4_SYSTEM_PROMPT = """你是安踏的客服助理小安, 主要职责是处理用户售前和售后的问题。{date_prompt}
下面是当前用户正在浏览的商品信息:


## 商品信息
{goods_info}
"""



class GLM4Chat9BRetailToolCallingChain(LLMChain):
    model_id = "glm-4-9b-chat"
    intent_type = LLMTaskType.RETAIL_TOOL_CALLING
    default_model_kwargs = {
        "max_tokens": 1024,
        "timeout": 60,
        "temperature": 0.1,
    }
    DATE_PROMPT = "当前日期: %Y-%m-%d"
    
    @staticmethod
    def convert_openai_function_to_glm(tools:list[dict]):
        glm_tools = []
        for tool_def in tools:
            tool_name = tool_def['name']
            description = tool_def['description']
            params = []
            required = tool_def['parameters'].get("required",[])
            for param_name,param in tool_def['parameters'].get('properties',{}).items():
                params.append({
                    "name": param_name,
                    "description": param["description"],
                    "type": param["type"],
                    "required": param_name in required,             
                })  
            glm_tools.append({
                "name": tool_name,
                "description": description,
                "params": params
            })
        return glm_tools

    @classmethod
    def create_system_prompt(cls,goods_info:str,tools:list) -> str:
        value = GLM4_SYSTEM_PROMPT.format(
            goods_info=goods_info,
            date_prompt=datetime.now().strftime(cls.DATE_PROMPT)
        )
        return value

    @classmethod
    def create_chat_history(cls,x):
        _chat_history = x['chat_history'] + \
            [{"role": "user","content":x['query']}] + \
            x['agent_chat_history']
        
        chat_history = []
        for message in _chat_history:
            new_message = message 
            if message['role'] == "ai":
                new_message = {
                    "role": "assistant",
                    "content": message['content']
                }
                tool_calls = message.get('additional_kwargs',{}).get("tool_calls",[])
                if tool_calls:
                    new_message['metadata'] = tool_calls[0]['name']
                
            chat_history.append(new_message)
                
        return {"chat_history": chat_history}

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        tools:list = kwargs.get('tools',[])
        glm_tools = cls.convert_openai_function_to_glm(tools)
        system_prompt = cls.create_system_prompt(kwargs['goods_info'], glm_tools)
        
        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )

        chain = RunnableLambda(lambda x: cls.create_chat_history(x)) \
            | RunnableLambda(lambda x: llm.invoke({
                "chat_history": x['chat_history'],
                "system_prompt": system_prompt,
                "tools": glm_tools
            }))

        return chain

        





