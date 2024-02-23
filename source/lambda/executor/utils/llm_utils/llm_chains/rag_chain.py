# rag llm chains

from typing import Any, List, Mapping, Optional

from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from ...constant import IntentType,QUERY_TRANSLATE_TYPE
from ...prompt_template import (
    get_claude_chat_rag_prompt,get_chit_chat_prompt,
    CHIT_CHAT_SYSTEM_TEMPLATE
)
from ..llm_models import Model
from .llm_chain_base import LLMChain

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



from .chat_chain import Baichuan2Chat13B4BitsChatChain

class Baichuan2Chat13B4BitsKnowledgeQaChain(Baichuan2Chat13B4BitsChatChain):
    model_id = "Baichuan2-13B-Chat-4bits"
    intent_type = IntentType.KNOWLEDGE_QA.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        llm_chain = super().create_chain(
            model_kwargs=model_kwargs,
            **kwargs
            )

        def add_system_prompt(x):
            context = "\n".join(x['contexts'])
            _chat_history = x['chat_history'] +  [("system",f"给定下面的背景知识:\n{context}\n回答下面的问题:\n")]
            return _chat_history
    
        chat_history_chain = RunnablePassthrough.assign(
            chat_history=RunnableLambda(lambda x:add_system_prompt(x))
        ) 
        llm_chain = chat_history_chain | llm_chain
        return llm_chain

from .chat_chain import Iternlm2Chat7BChatChain
class Iternlm2Chat7BKnowledgeQaChain(Iternlm2Chat7BChatChain):
    mdoel_id = "internlm2-chat-7b"
    intent_type = IntentType.KNOWLEDGE_QA.value

    @classmethod
    def create_prompt(cls,x):
        query = x['query']
        contexts = x['contexts']

        history = cls.create_history(x)
        
        context = "\n".join(contexts)
        meta_instruction = f"请根据下面的背景知识回答问题.\n背景知识: {context}\n"
        query = f"问题: {query}\n"
        prompt = cls.build_prompt(
            query=query,
            history=history,
            meta_instruction=meta_instruction
        ) 
        prompt = prompt + "答案:"
        return prompt