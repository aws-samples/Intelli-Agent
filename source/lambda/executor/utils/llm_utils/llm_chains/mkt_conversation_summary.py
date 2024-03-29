import datetime
import json
import os
import sys
import threading
from functools import lru_cache
from random import Random

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

from ...constant import (
    AI_MESSAGE_TYPE,
    HUMAN_MESSAGE_TYPE,
    MKT_CONVERSATION_SUMMARY_TYPE,
    SYSTEM_MESSAGE_TYPE,
)
from ...prompt_template import CHIT_CHAT_SYSTEM_TEMPLATE, get_chit_chat_prompt
from ..llm_models import Model
from .chat_chain import Claude2ChatChain, Iternlm2Chat7BChatChain
from .llm_chain_base import LLMChain


class Iternlm2Chat7BMKTConversationSummaryChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = MKT_CONVERSATION_SUMMARY_TYPE

    @classmethod
    def create_prompt(cls, x):
        return x["prompt"]

    @classmethod
    def _create_prompt(cls, x):
        chat_history = x["chat_history"]
        assert len(chat_history) % 2 == 0, chat_history

        history = []
        questions = []
        for i in range(0, len(chat_history), 2):
            assert chat_history[i].type == HUMAN_MESSAGE_TYPE, chat_history
            assert chat_history[i + 1].type == AI_MESSAGE_TYPE, chat_history
            questions.append(
                {
                    "question": chat_history[i].content,
                    "create_time": chat_history[i].additional_kwargs["create_time"],
                }
            )
            history.append((chat_history[i].content, chat_history[i + 1].content))

        questions_str = ""
        for i, question in enumerate(questions):
            questions_str += f"问题{i+1}: {question['question']}\n提问时间: {question['create_time']}\n"
        # print(questions_str)
        query_input = """请总结上述对话中的内容,为每一轮对话单独做一个不超过50个字的简短总结。\n"""
        prompt = cls.build_prompt(
            meta_instruction=CHIT_CHAT_SYSTEM_TEMPLATE,
            history=history,
            query=query_input,
        )
        prompt_assist = f"好的，根据提供历史对话信息，共有{len(history)}段对话:\n{questions_str}\n对它们的总结如下(每一个总结要先复述一下问题):\n"
        prefix = f"问题1: {questions[0]['question']}\n提问时间: {questions[0]['create_time']}\n总结:"
        # thread_local.mkt_conversation_prefix = prefix
        # print(thread_local,thread_local.mkt_conversation_prefix)
        prompt = prompt + prompt_assist + prefix
        # prompt = prompt
        return {"prompt": prompt, "prefix": prefix}

    @staticmethod
    def stream_postprocess_fn(x):
        yield x["prefix"]
        yield from x["llm_output"]

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        stream = kwargs.get("stream", False)
        llm_chain = super().create_chain(model_kwargs=model_kwargs, **kwargs)
        chain = (
            RunnablePassthrough.assign(prompt_dict=lambda x: cls._create_prompt(x))
            | RunnablePassthrough.assign(
                prompt=lambda x: x["prompt_dict"]["prompt"],
                prefix=lambda x: x["prompt_dict"]["prefix"],
            )
            | RunnablePassthrough.assign(llm_output=llm_chain)
        )
        if stream:
            chain = chain | RunnableLambda(lambda x: cls.stream_postprocess_fn(x))
        else:
            chain = chain | RunnableLambda(lambda x: x["prefix"] + x["llm_output"])
        return chain


class Iternlm2Chat20BMKTConversationSummaryChain(
    Iternlm2Chat7BMKTConversationSummaryChain
):
    model_id = "internlm2-chat-20b"


class Claude2MKTConversationSummaryChain(Claude2ChatChain):
    model_id = "anthropic.claude-v2"
    intent_type = MKT_CONVERSATION_SUMMARY_TYPE

    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.1, "top_p": 0.9}

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        chain = super().create_chain(model_kwargs=model_kwargs, **kwargs)
        query_input = """请简要总结上述对话中的内容,每一个对话单独一个总结，并用 '- '开头。 每一个总结要先说明问题。\n"""
        chain = RunnablePassthrough.assign(query=lambda x: query_input) | chain
        return chain


class Claude21MKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceMKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetMKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuMKTConversationSummaryChain(Claude2MKTConversationSummaryChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
