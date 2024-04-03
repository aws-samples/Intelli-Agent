# conversation summary chain
from .llm_chain_base import LLMChain
from ...constant import (
    CONVERSATION_SUMMARY_TYPE,
    HUMAN_MESSAGE_TYPE,
    AI_MESSAGE_TYPE,
    SYSTEM_MESSAGE_TYPE,
)
from ..llm_models import Model
import json
import os
import sys
from random import Random
from functools import lru_cache
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
)
from .chat_chain import Iternlm2Chat7BChatChain
from ...prompt_template import get_conversation_query_rewrite_prompt


class Iternlm2Chat7BConversationSummaryChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = CONVERSATION_SUMMARY_TYPE
    meta_instruction_prompt_template = """Given a question and its context, decontextualize the question by addressing coreference and omission issues. The resulting question should retain its original meaning and be as informative as possible, and should not duplicate any previously asked questions in the context.
Context: [Q: When was Born to Fly released?
A: Sara Evans’s third studio album, Born to Fly, was released on October 10, 2000.
]
Question: Was Born to Fly well received by critics?
Rewrite: Was Born to Fly well received by critics?

Context: [Q: When was Keith Carradine born?
A: Keith Ian Carradine was born August 8, 1949.
Q: Is he married?
A: Keith Carradine married Sandra Will on February 6, 1982. ]
Question: Do they have any children?
Rewrite: Do Keith Carradine and Sandra Will have any children?

Context: {conversational_context}
Question: {question}
"""
    default_model_kwargs = {
        "max_new_tokens": 300,
        "temperature": 0.1,
        "stop_tokens": ["\n\n"],
    }

    @classmethod
    def create_prompt(cls, x):
        chat_history = x["chat_history"]
        conversational_contexts = []
        for his in chat_history:
            assert his.type in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
            if his.type == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"Q: {his.content}")
            else:
                conversational_contexts.append(f"A: {his.content}")

        conversational_context = "[" + "\n".join(conversational_contexts) + "]"
        prompt = cls.build_prompt(
            cls.meta_instruction_prompt_template.format(
                conversational_context=conversational_context, question=x["query"]
            )
        )
        prompt = prompt + "Rewrite: "
        return prompt

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        return super().create_chain(model_kwargs=model_kwargs, **kwargs)


class Iternlm2Chat20BConversationSummaryChain(Iternlm2Chat7BConversationSummaryChain):
    model_id = "internlm2-chat-20b"
    meta_instruction_prompt_template = """Given the following conversation and a follow up question, rephrase the follow up \
question to be a standalone question.

Chat History:
{history}
Follow Up Input: {question}"""
    default_model_kwargs = {
        "max_new_tokens": 300,
        "temperature": 0.1,
        "stop_tokens": ["\n\n"],
    }

    @classmethod
    def create_prompt(cls, x):
        chat_history = x["chat_history"]
        conversational_contexts = []
        for his in chat_history:
            assert his.type in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
            if his.type == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"Q: {his.content}")
            else:
                conversational_contexts.append(f"A: {his.content}")

        conversational_context = "\n".join(conversational_contexts)
        prompt = cls.build_prompt(
            cls.meta_instruction_prompt_template.format(
                history=conversational_context, question=x["query"]
            )
        )
        prompt = prompt + "Standalone Question: "
        return prompt


class Claude2ConversationSummaryChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = CONVERSATION_SUMMARY_TYPE

    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.1, "top_p": 0.9}

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        # cqr_prompt = get_conversation_query_rewrite_prompt(chat_history)
        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        cqr_chain = (
            RunnableLambda(
                lambda x: get_conversation_query_rewrite_prompt(x["chat_history"])
            )
            | llm
            | RunnableLambda(lambda x: x.content)
        )
        return cqr_chain


class Claude21ConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
