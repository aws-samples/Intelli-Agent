
# from llmbot_utils import concat_recall_knowledge
from typing import Any, List, Mapping, Optional



from langchain.llms import Bedrock

from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from ..constant import IntentType
from ..prompt_template import (
    get_claude_chat_rag_prompt,get_chit_chat_prompt,
    CHIT_CHAT_SYSTEM_TEMPLATE
)
from .llm_models import Model
# from ..constant import HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE


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
        # chat_history = kwargs.get('chat_history',[])
        prompt = RunnableLambda(lambda x: get_claude_chat_rag_prompt(x['chat_history']))
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
    

class ClaudeRagInstance(Claude2RagLLMChain):
    model_id = 'anthropic.claude-instant-v1'
   

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
    

class Baichuan2Chat13B4BitsKnowledgeQaChain(Baichuan2Chat13B4BitsChatChain):
    model_id = "Baichuan2-13B-Chat-4bits"
    intent_type = IntentType.KNOWLEDGE_QA.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        llm_chain = super().create_chain(
            model_kwargs=model_kwargs,
            **kwargs
            )
        # chat_history = kwargs.pop('chat_history',[])

        def add_system_prompt(x):
            context = "\n".join(x['contexts'])
            _chat_history = x['chat_history'] +  [("system",f"给定下面的背景知识:\n{context}\n回答下面的问题:\n")]
            return _chat_history
    
        chat_history_chain = RunnablePassthrough.assign(
            chat_history=RunnableLambda(lambda x:add_system_prompt(x))
        ) 
        llm_chain = chat_history_chain | llm_chain
        return llm_chain

class Iternlm2Chat7BChatChain(LLMChain):
    model_id = "internlm2-chat-7b"
    intent_type = IntentType.CHAT.value

    @classmethod
    def add_meta_instruction(cls,x):
        meta_instruction = CHIT_CHAT_SYSTEM_TEMPLATE
        return meta_instruction
        
    @classmethod
    def add_query(cls,x):
        return x['query']

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)

        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        
        input_chain = RunnablePassthrough.assign(
            _query=RunnableLambda(lambda x:cls.add_query(x))
        ) | RunnablePassthrough.assign(
            meta_instruction=RunnableLambda(lambda x:cls.add_meta_instruction(x))
            )
        
        llm_chain = input_chain | RunnableLambda(lambda x:llm.invoke(x,stream=stream))
        
        return llm_chain

class Iternlm2Chat7BKnowledgeQaChain(Iternlm2Chat7BChatChain):
    mdoel_id = "internlm2-chat-7b"
    intent_type = IntentType.KNOWLEDGE_QA.value
    
    @classmethod
    def add_meta_instruction(cls,x):
        contexts = x['contexts']
        context = "\n".join(contexts)
        meta_instruction = f"请根据下面的背景知识回答问题.\n背景知识: {context}\n"
        return meta_instruction
        
    @classmethod
    def add_query(cls,x):
        return f"问题: {x['query']}\n答案:"