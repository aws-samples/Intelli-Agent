from .llm_chain_base import LLMChain
from ...constant import MKT_CONVERSATION_SUMMARY_TYPE,HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE
from ..llm_models import Model
from ...prompt_template import get_chit_chat_prompt,CHIT_CHAT_SYSTEM_TEMPLATE
import json 
import os
import sys
from random import Random
from functools import lru_cache
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableBranch, RunnableLambda
from .chat_chain import Iternlm2Chat7BChatChain,Claude2ChatChain



class Iternlm2Chat7BMKTConversationSummaryChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = MKT_CONVERSATION_SUMMARY_TYPE

    @classmethod
    def create_prompt(cls,x):
        chat_history = x['chat_history']
        assert len(chat_history) % 2 == 0, chat_history
        
        history = []
        questions = []
        for i in range(0,len(chat_history),2):
            assert chat_history[i].type == HUMAN_MESSAGE_TYPE, chat_history
            assert chat_history[i+1].type == AI_MESSAGE_TYPE, chat_history
            questions.append(chat_history[i].content)
            history.append((chat_history[i].content,chat_history[i+1].content))
        

        questions_str = ''
        for i,question in enumerate(questions):
            questions_str += f"问题{i+1}: {question}\n"
        # print(questions_str)
        query_input = """请总结上述对话中的内容,每一轮对话单独一个总结。\n"""
        prompt = cls.build_prompt(
            meta_instruction=CHIT_CHAT_SYSTEM_TEMPLATE,
            history=history,
            query=query_input
        ) + f"好的，根据提供历史对话信息，共有{len(history)}段对话:\n{questions_str}\n对它们的总结如下(每一个总结要先复述一下问题):\n"
        # prompt = prompt
        return prompt

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        
        # model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        return super().create_chain(model_kwargs=model_kwargs,**kwargs)


class Claude2MKTConversationSummaryChain(Claude2ChatChain):
    model_id = 'anthropic.claude-v2'
    intent_type = MKT_CONVERSATION_SUMMARY_TYPE

    default_model_kwargs = {
            "max_tokens_to_sample": 2000,
            "temperature": 0.1,
            "top_p": 0.9
        }
    
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        chain = super().create_chain(model_kwargs=model_kwargs,**kwargs)
        query_input = """请简要总结上述对话中的内容,每一个对话单独一个总结，并用 '- '开头。 每一个总结要先说明问题。\n"""
        chain = RunnablePassthrough.assign(query=lambda x: query_input) | chain
        return chain 

class Claude21MKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = 'anthropic.claude-v2:1'

class ClaudeInstanceMKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = 'anthropic.claude-instant-v1'