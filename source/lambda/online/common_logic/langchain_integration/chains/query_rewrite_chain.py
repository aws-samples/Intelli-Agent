# query rewrite
import re

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import (
    RunnableLambda,
    RunnablePassthrough,
)

from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType
)
from ..chains import LLMChain
from ..chat_models import Model as LLM_Model
from .chat_chain import Internlm2Chat7BChatChain
from . import LLMChain

QUERY_REWRITE_TYPE = LLMTaskType.QUERY_REWRITE_TYPE
query_expansion_template_claude = PromptTemplate.from_template("""You are an AI language model assistant. Your task is to generate 1 - 5 different sub questions OR alternate versions of the given user question to retrieve relevant documents from a vector database.

By generating multiple versions of the user question,
your goal is to help the user overcome some of the limitations
of distance-based similarity search.

By generating sub questions, you can break down questions that refer to multiple concepts into distinct questions. This will help you get the relevant documents for constructing a final answer

If multiple concepts are present in the question, you should break into sub questions, with one question for each concept

Provide these alternative questions separated by newlines between XML tags. For example:

<questions>
- Question 1
- Question 2
- Question 3
</questions>

Original question: {question}""")


class Claude2QueryRewriteChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = QUERY_REWRITE_TYPE

    default_model_kwargs = {
        "temperature": 0.7,
        "max_tokens": 100,
        "stop_sequences": ["\n\nHuman:"],
    }

    @staticmethod
    def query_rewrite_postprocess(r):
        ret = re.findall("<questions>.*?</questions>", r, re.S)[0]
        questions = re.findall("- (.*?)\n", ret, re.S)
        return questions

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        query_key = kwargs.pop("query_key", "query")
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        llm = LLM_Model.get_model(
            cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = (
            RunnablePassthrough.assign(question=lambda x: x[query_key])
            | query_expansion_template_claude
            | llm
            | RunnableLambda(cls.query_rewrite_postprocess)
        )
        return chain


class Claude21QueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceQueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3HaikuQueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude3SonnetQueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude35SonnetQueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.CLAUDE_3_5_SONNET


class Claude35SonnetV2QueryRewriteChain(Claude2QueryRewriteChain):
    mdoel_id = LLMModelType.CLAUDE_3_5_SONNET_V2


class Claude35HaikuQueryRewriteChain(Claude2QueryRewriteChain):
    mdoel_id = LLMModelType.CLAUDE_3_5_HAIKU


internlm2_meta_instruction = """You are an AI language model assistant. Your task is to generate 1 - 5 different sub questions OR alternate versions of the given user question to retrieve relevant documents from a vector database.

By generating multiple versions of the user question,
your goal is to help the user overcome some of the limitations
of distance-based similarity search.

By generating sub questions, you can break down questions that refer to multiple concepts into distinct questions. This will help you get the relevant documents for constructing a final answer

If multiple concepts are present in the question, you should break into sub questions, with one question for each concept

Provide these alternative questions separated by newlines between XML tags. For example:

<questions>
- Question 1
- Question 2
- Question 3
</questions>"""


class Internlm2Chat7BQueryRewriteChain(Internlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_7B
    intent_type = QUERY_REWRITE_TYPE

    default_model_kwargs = {"temperature": 0.5, "max_new_tokens": 100}

    @classmethod
    def create_prompt(cls, x):
        query = f'Original question: {x["query"]}'
        prompt = cls.build_prompt(
            query=query,
            meta_instruction=internlm2_meta_instruction,
        )
        return prompt

    @staticmethod
    def query_rewrite_postprocess(r):
        ret = re.findall("<questions>.*?</questions>", r, re.S)[0]
        questions = re.findall("- (.*?)\n", ret, re.S)
        return questions

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        chain = super().create_chain(model_kwargs=model_kwargs, **kwargs)
        chain = chain | RunnableLambda(
            lambda x: cls.query_rewrite_postprocess(x))
        return chain


class Internlm2Chat20BQueryRewriteChain(Internlm2Chat7BQueryRewriteChain):
    model_id = LLMModelType.INTERNLM2_CHAT_20B
    intent_type = QUERY_REWRITE_TYPE


class NovaProQueryRewriteChain(Claude2QueryRewriteChain):
    model_id = LLMModelType.NOVA_PRO

