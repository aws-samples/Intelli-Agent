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
    default_model_kwargs = {
        "temperature":0.05,
        "max_new_tokens": 1000
    }

    @classmethod
    def create_prompt(cls,x):
        query = x['query']
        contexts = x['contexts']
        history = cls.create_history(x)
        context = "\n".join(contexts)
        meta_instruction = f"你是一个Amazon AWS的客服助理小Q，帮助的用户回答使用AWS过程中的各种问题。\n面对用户的问题，你需要给出中文回答。\n下面给出相关问题的背景知识, 需要注意的是如果你认为当前的问题不能在背景知识中找到答案, 你应该直接回答:\n“对不起我没有足够的知识回答您的问题”。\n 背景知识:\n{context}\n\n"
        # meta_instruction = f"You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use simplified Chinese to response the qustion. I’m going to tip $300K for a better answer! "
        # meta_instruction = f'You are an expert AI on a question and answer task. \nUse the "Following Context" when answering the question. If you don't know the answer, reply to the "Following Text" in the header and answer to the best of your knowledge, or if you do know the answer, answer without the "Following Text"'
#         meta_instruction = """You are an expert AI on a question and answer task. 
# Use the "Following Context" when answering the question. If you don't know the answer, reply to the "Following Text" in the header and answer to the best of your knowledge, or if you do know the answer, answer without the "Following Text". If a question is asked in Korean, translate it to English and always answer in Korean.
# Following Text: "I didn't find the answer in the context given, but here's what I know! **I could be wrong, so cross-verification is a must!**"""
#         meta_instruction = """You are an expert AI on a question and answer task. 
# Use the "Following Context" when answering the question. If you don't know the answer, reply to the "Sorry, I don't know". """
        # query = f"Question: {query}\nContext:\n{context}"
#         query = f"""Following Context: {context}
# Question: {query}"""
        query = f"问题: {query}"
        prompt = cls.build_prompt(
            query=query,
            history=history,
            meta_instruction=meta_instruction
        ) 
        # prompt = prompt + "回答: 让我先来判断一下问题的答案是否包含在背景知识中。"
        prompt = prompt + f"回答: 经过慎重且深入的思考, 根据背景知识, 对于问题: {query}, 我的回答如下:\n"
        return prompt

class Iternlm2Chat20BKnowledgeQaChain(Iternlm2Chat7BKnowledgeQaChain):
    model_id = "internlm2-chat-20b"