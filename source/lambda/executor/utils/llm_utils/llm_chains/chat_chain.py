# chat llm chains
from typing import Any, List, Mapping, Optional

from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from ...constant import IntentType,QUERY_TRANSLATE_TYPE,HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE
from ...prompt_template import get_chit_chat_prompt,CHIT_CHAT_SYSTEM_TEMPLATE
from ..llm_models import Model
from .llm_chain_base import LLMChain


class Claude2ChatChain(LLMChain):
    model_id = 'anthropic.claude-v2'
    intent_type = IntentType.CHAT.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        prompt = RunnableLambda(lambda x: get_chit_chat_prompt(x['chat_history']))
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
        return chain 
      

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
     
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        # chat_history = kwargs.pop('chat_history',[])
    
        model_kwargs = model_kwargs or {}
        model_kwargs.update({"stream": stream})
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        llm_chain =  RunnableLambda(lambda x:llm.invoke(x,stream=stream))
        return llm_chain


class Iternlm2Chat7BChatChain(LLMChain):
    model_id = "internlm2-chat-7b"
    intent_type = IntentType.CHAT.value

    default_model_kwargs = {
        "temperature":0.5,
        "max_new_tokens": 1000
    }

    @staticmethod
    def build_prompt(
            query: str, 
            history = [], 
            meta_instruction="You are an AI assistant whose name is InternLM (书生·浦语).\n"
            "- InternLM (书生·浦语) is a conversational language model that is developed by Shanghai AI Laboratory (上海人工智能实验室). It is designed to be helpful, honest, and harmless.\n"
            "- InternLM (书生·浦语) can understand and communicate fluently in the language chosen by the user such as English and 中文."
        ):
        prompt = ""
        if meta_instruction:
            prompt += f"""<|im_start|>system\n{meta_instruction}<|im_end|>\n"""
        for record in history:
            prompt += f"""<|im_start|>user\n{record[0]}<|im_end|>\n<|im_start|>assistant\n{record[1]}<|im_end|>\n"""
        prompt += f"""<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"""
        return prompt

    # @classmethod
    # def add_meta_instruction(cls,x):
    #     meta_instruction = CHIT_CHAT_SYSTEM_TEMPLATE
    #     return meta_instruction
        
    # @classmethod
    # def add_query(cls,x):
    #     return x['query']

    @classmethod
    def create_history(cls,x):
        chat_history = x.get('chat_history',[])
        assert len(chat_history) % 2 == 0, chat_history
        history = []
        for i in range(0,len(chat_history),2):
            user_message = chat_history[i]
            ai_message = chat_history[i+1]
            assert user_message.type == HUMAN_MESSAGE_TYPE \
                  and ai_message.type == AI_MESSAGE_TYPE , chat_history
            history.append((user_message.content,ai_message.content))
        return history
        
    @classmethod
    def create_prompt(cls,x):
        history = cls.create_history(x)
        prompt = cls.build_prompt(
            query=x['query'],
            history=history,
            meta_instruction=CHIT_CHAT_SYSTEM_TEMPLATE
        )
        return prompt
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        stream = kwargs.get('stream',False)
        llm = Model.get_model(
                cls.model_id,
                model_kwargs=model_kwargs,
                **kwargs
            )
        
        prompt_template = RunnablePassthrough.assign(
            prompt=RunnableLambda(lambda x:cls.create_prompt(x))
        ) 
        llm_chain = prompt_template | RunnableLambda(lambda x:llm.invoke(x,stream=stream))
        return llm_chain
    


class Iternlm2Chat20BChatChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-20b"