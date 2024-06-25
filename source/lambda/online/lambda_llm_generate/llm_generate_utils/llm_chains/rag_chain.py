# rag llm chains


from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from common_utils.constant import (
    LLMTaskType,
    LLMModelType
)
from common_utils.prompt_utils import get_prompt_template

# from ...prompt_template import convert_chat_history_from_fstring_format
from ..llm_models import Model
from .llm_chain_base import LLMChain


def get_claude_rag_context(contexts: list):
    assert isinstance(contexts, list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i, context in enumerate(contexts):
        context_xml = context_template.format(index=i + 1, content=context)
        context_xmls.append(context_xml)

    context = "\n".join(context_xmls)
    return context


class Claude2RagLLMChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get("stream", False)
        # history
        # chat_history = kwargs.get("chat_history", [])
        
        system_prompt_template = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="main"     
        ).prompt_template

        system_prompt_template = kwargs.get("system_prompt",system_prompt_template)

        chat_messages = [
            SystemMessagePromptTemplate.from_template(system_prompt_template),
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}")
        ]
        context_chain = RunnablePassthrough.assign(
            context=RunnableLambda(lambda x: get_claude_rag_context(x["contexts"]))
        )
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
        if stream:
            chain = (
                chain
                | RunnableLambda(lambda x: llm.stream(x.messages))
                | RunnableLambda(lambda x: (i.content for i in x))
            )
        else:
            chain = chain | llm | RunnableLambda(lambda x: x.content)
        return chain


class Claude21RagLLMChain(Claude2RagLLMChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceRAGLLMChain(Claude2RagLLMChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetRAGLLMChain(Claude2RagLLMChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuRAGLLMChain(Claude2RagLLMChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU

class Mixtral8x7bChatChain(Claude2RagLLMChain):
    model_id = LLMModelType.MIXTRAL_8X7B_INSTRUCT


from .chat_chain import GLM4Chat9BChatChain

class GLM4Chat9BRagChain(GLM4Chat9BChatChain):
    model_id = LLMModelType.GLM_4_9B_CHAT
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chat_history(cls,x, system_prompt=None):
        if system_prompt is None:
            system_prompt = get_prompt_template(
                model_id=cls.model_id,
                task_type=cls.intent_type,
                prompt_name="main"     
            ).prompt_template
        context = ("\n" + "="*50+ "\n").join(x['contexts'])
        system_prompt = system_prompt.format(context=context)

        return super().create_chat_history(x,system_prompt=system_prompt)
    

from .chat_chain import Qwen2Instruct7BChatChain

class Qwen2Instruct7BRagChain(Qwen2Instruct7BChatChain):
    model_id = LLMModelType.QWEN2INSTRUCT7B
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chat_history(cls,x, system_prompt=None):
        if system_prompt is None:
            system_prompt = get_prompt_template(
                model_id=cls.model_id,
                task_type=cls.intent_type,
                prompt_name="main"     
            ).prompt_template
        
        context = ("\n" + "="*50+ "\n").join(x['contexts'])
        system_prompt = system_prompt.format(context=context)
        return super().create_chat_history(x,system_prompt=system_prompt)


class Qwen2Instruct72BRagChain(Qwen2Instruct7BRagChain):
    model_id = LLMModelType.QWEN2INSTRUCT72B

from .chat_chain import Baichuan2Chat13B4BitsChatChain

class Baichuan2Chat13B4BitsKnowledgeQaChain(Baichuan2Chat13B4BitsChatChain):
    model_id = LLMModelType.BAICHUAN2_13B_CHAT
    intent_type = LLMTaskType.RAG

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        llm_chain = super().create_chain(model_kwargs=model_kwargs, **kwargs)

        def add_system_prompt(x):
            context = "\n".join(x["contexts"])
            _chat_history = x["chat_history"] + [
                ("system", f"给定下面的背景知识:\n{context}\n回答下面的问题:\n")
            ]
            return _chat_history

        chat_history_chain = RunnablePassthrough.assign(
            chat_history=RunnableLambda(lambda x: add_system_prompt(x))
        )
        llm_chain = chat_history_chain | llm_chain
        return llm_chain




