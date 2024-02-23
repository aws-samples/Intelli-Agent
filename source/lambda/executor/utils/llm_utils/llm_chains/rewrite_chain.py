# query rewrite 
from .llm_chain_base import LLMChain
from ...constant import INTENT_RECOGNITION_TYPE,IntentType,QUERY_REWRITE_TYPE
from ..llm_models import Model
import json 
import os
import sys
from random import Random
from functools import lru_cache
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableBranch, RunnableLambda
from .chat_chain import Iternlm2Chat7BChatChain



class Iternlm2Chat7BIntentRecognitionChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = QUERY_REWRITE_TYPE

    @classmethod
    def create_prompt(cls,x):
        raise NotImplementedError

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        raise NotImplementedError