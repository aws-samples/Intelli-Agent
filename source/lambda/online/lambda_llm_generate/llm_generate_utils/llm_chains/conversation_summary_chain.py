# conversation summary chain
from typing import List 

from langchain.schema.runnable import (
    RunnableLambda,
    RunnablePassthrough,
)


from ..llm_models import Model
from .chat_chain import Iternlm2Chat7BChatChain
from .llm_chain_base import LLMChain
from common_utils.constant import (
    MessageType,
    LLMTaskType,
    LLMModelType
)

from langchain_core.messages import(
    AIMessage,
    BaseMessage,
    HumanMessage,
    convert_to_messages
) 
from langchain.prompts import (
    HumanMessagePromptTemplate,
    ChatPromptTemplate
)

from common_utils.prompt_utils import get_prompt_template

AI_MESSAGE_TYPE = MessageType.AI_MESSAGE_TYPE
HUMAN_MESSAGE_TYPE = MessageType.HUMAN_MESSAGE_TYPE
QUERY_TRANSLATE_TYPE = LLMTaskType.QUERY_TRANSLATE_TYPE
SYSTEM_MESSAGE_TYPE = MessageType.SYSTEM_MESSAGE_TYPE


class Iternlm2Chat20BConversationSummaryChain(Iternlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_20B
    default_model_kwargs = {
        "max_new_tokens": 300,
        "temperature": 0.1,
        "stop_tokens": ["\n\n"],
    }

    @classmethod
    def create_prompt(cls, x,system_prompt=None):
        chat_history = x["chat_history"]
        conversational_contexts = []
        for his in chat_history:
            role = his['role']
            assert role in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
            if role == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"USER: {his['content']}")
            else:
                conversational_contexts.append(f"AI: {his['content']}")
        if system_prompt is None:
            system_prompt  = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="main"     
        ).prompt_template

        conversational_context = "\n".join(conversational_contexts)
        prompt = cls.build_prompt(
            system_prompt.format(
                history=conversational_context, question=x["query"]
            )
        )
        prompt = prompt + "Standalone Question: "
        return prompt

class Iternlm2Chat7BConversationSummaryChain(Iternlm2Chat20BConversationSummaryChain):
    model_id = LLMModelType.INTERNLM2_CHAT_7B


class Claude2ConversationSummaryChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.CONVERSATION_SUMMARY_TYPE

    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.1, "top_p": 0.9}

    @staticmethod
    def create_conversational_context(chat_history:List[BaseMessage]):
        conversational_contexts = []
        for his in chat_history:
            assert isinstance(his,(AIMessage,HumanMessage)), his
            content = his.content
            if isinstance(his,HumanMessage):
                conversational_contexts.append(f"USER: {content}")
            else:
                conversational_contexts.append(f"AI: {content}")
        conversational_context = "\n".join(conversational_contexts)
        return conversational_context
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        prompt_template = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="main"     
        ).prompt_template

        prompt_template = kwargs.get("system_prompt",prompt_template)
        cqr_template = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(prompt_template),
            AIMessage(content="Standalone USER's reply: ")
        ])

        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        cqr_chain = RunnablePassthrough.assign(
                conversational_context=RunnableLambda(
                lambda x: cls.create_conversational_context(
                    convert_to_messages(x["chat_history"])
                )
            ))  \
            | RunnableLambda(lambda x: cqr_template.format(history=x["conversational_context"],question=x['query'])) \
            | llm | RunnableLambda(lambda x: x.content)
        
        return cqr_chain

class Claude21ConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Qwen2Instruct72BConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.QWEN2INSTRUCT72B


class Qwen2Instruct7BConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.QWEN2INSTRUCT7B


class GLM4Chat9BConversationSummaryChain(Claude2ConversationSummaryChain):
    model_id = LLMModelType.GLM_4_9B_CHAT


