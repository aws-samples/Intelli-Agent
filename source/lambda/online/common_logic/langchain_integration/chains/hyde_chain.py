# hyde

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
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

HYDE_TYPE = LLMTaskType.HYDE_TYPE

WEB_SEARCH_TEMPLATE = """Please write a passage to answer the question 
Question: {query}
Passage:"""
# hyde_web_search_template = PromptTemplate(template=WEB_SEARCH_TEMPLATE, input_variables=["query"])


class Claude2HydeChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = HYDE_TYPE

    default_model_kwargs = {
        "temperature": 0.5,
        "max_tokens": 1000,
        "stop_sequences": ["\n\nHuman:"],
    }

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        # query_key = kwargs.pop("query_key", "query")
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        llm = LLM_Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        prompt = ChatPromptTemplate.from_messages(
            [HumanMessagePromptTemplate.from_template(WEB_SEARCH_TEMPLATE)]
        )
        chain = RunnablePassthrough.assign(
            hyde_doc=prompt | llm | RunnableLambda(lambda x: x.content)
        )
        return chain


class Claude21HydeChain(Claude2HydeChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceHydeChain(Claude2HydeChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetHydeChain(Claude2HydeChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuHydeChain(Claude2HydeChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35SonnetHydeChain(Claude2HydeChain):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"


internlm2_meta_instruction = "You are a helpful AI Assistant."


class Internlm2Chat7BHydeChain(Internlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_7B
    intent_type = HYDE_TYPE

    default_model_kwargs = {"temperature": 0.1, "max_new_tokens": 200}

    @classmethod
    def create_prompt(cls, x):
        query = f"""Please write a brief passage to answer the question. \nQuestion: {prompt}"""
        prompt = (
            cls.build_prompt(
                query=query,
                meta_instruction=internlm2_meta_instruction,
            )
            + "Passage: "
        )
        return prompt


class Internlm2Chat20BHydeChain(Internlm2Chat7BHydeChain):
    model_id = LLMModelType.INTERNLM2_CHAT_20B
    intent_type = HYDE_TYPE


class NovaProHydeChain(Claude2HydeChain):
    model_id = LLMModelType.NOVA_PRO
