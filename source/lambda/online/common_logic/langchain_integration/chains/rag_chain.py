# rag llm chains
# from .chat_chain import Baichuan2Chat13B4BitsChatChain
# from .chat_chain import Qwen2Instruct7BChatChain
# from .chat_chain import GLM4Chat9BChatChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate
)
from langchain_core.output_parsers import StrOutputParser

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType
)
from ..models.model_config import (
    BEDROCK_MODEL_CONFIGS,
    OPENAI_MODEL_CONFIGS,
    QWEN25_MODEL_CONFIGS,
    SILICONFLOW_DEEPSEEK_MODEL_CONFIGS
)
from common_logic.common_utils.prompt_utils import get_prompt_template
from common_logic.common_utils.logger_utils import print_llm_messages
from ..models.chat_models import ReasonModelResult,ReasonModelStreamResult
# from ...prompt_template import convert_chat_history_from_fstring_format
from ..models import ChatModel
from . import LLMChain


def get_claude_rag_context(contexts: list):
    assert isinstance(contexts, list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i, context in enumerate(contexts):
        context_xml = context_template.format(index=i + 1, content=context)
        context_xmls.append(context_xml)

    context = "\n".join(context_xmls)
    return context


class RagBaseChain(LLMChain):
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chat_messages(self,system_prompt_template):
        chat_messages = [
            SystemMessagePromptTemplate.from_template(system_prompt_template),
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}")
        ]
        return chat_messages

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        system_prompt_template = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="system_prompt"
        ).prompt_template

        system_prompt_template = kwargs.get(
            "system_prompt", system_prompt_template)

        chat_messages = cls.create_chat_messages(system_prompt_template)

        context_chain = RunnablePassthrough.assign(
            context=RunnableLambda(
                lambda x: get_claude_rag_context(x["contexts"]))
        )
        llm = ChatModel.get_model(
            cls.model_id, model_kwargs=model_kwargs, **kwargs)
        
        chain = context_chain | ChatPromptTemplate.from_messages(chat_messages) | RunnableLambda(
            lambda x: print_llm_messages(f"rag messages: {x.messages}") or x)
        
        chain = chain | llm
        if not llm.is_reasoning_model:
            chain = chain | StrOutputParser()
            if stream:
                final_chain = RunnableLambda(lambda x: chain.stream(x))
            else:
                final_chain = RunnableLambda(lambda x: chain.invoke(x))

            return final_chain
        else:
            if stream:
                final_chain = RunnableLambda(lambda x: ReasonModelStreamResult(chain.stream(x)))
            else:
                final_chain = RunnableLambda(lambda x: ReasonModelResult(chain.invoke(x)))
            return final_chain

class DeepSeekR1RagBaseChain(RagBaseChain):
    @classmethod
    def create_chat_messages(self,system_prompt_template):
        chat_messages = [
            HumanMessagePromptTemplate.from_template(system_prompt_template),
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}")
        ]
        return chat_messages



RagBaseChain.create_for_chains(BEDROCK_MODEL_CONFIGS,LLMTaskType.RAG)
RagBaseChain.create_for_chains(OPENAI_MODEL_CONFIGS,LLMTaskType.RAG)
RagBaseChain.create_for_chains(QWEN25_MODEL_CONFIGS,LLMTaskType.RAG)
DeepSeekR1RagBaseChain.create_for_chains(SILICONFLOW_DEEPSEEK_MODEL_CONFIGS,LLMTaskType.RAG)

