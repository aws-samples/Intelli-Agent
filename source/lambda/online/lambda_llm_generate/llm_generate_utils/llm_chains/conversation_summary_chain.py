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
    convert_to_messages
) 
from langchain.prompts import (
    HumanMessagePromptTemplate,
    ChatPromptTemplate
)

AI_MESSAGE_TYPE = MessageType.AI_MESSAGE_TYPE
HUMAN_MESSAGE_TYPE = MessageType.HUMAN_MESSAGE_TYPE
QUERY_TRANSLATE_TYPE = LLMTaskType.QUERY_TRANSLATE_TYPE
SYSTEM_MESSAGE_TYPE = MessageType.SYSTEM_MESSAGE_TYPE


# CQR_TEMPLATE = """Given a question and its context, decontextualize the question by addressing coreference and omission issues. The resulting question should retain its original meaning and be as informative as possible, and should not duplicate any previously asked questions in the context.
# Context: [Q: When was Born to Fly released?
# A: Sara Evans’s third studio album, Born to Fly, was released on October 10, 2000.
# ]
# Question: Was Born to Fly well received by critics?
# Rewrite: Was Born to Fly well received by critics?

# Context: [Q: When was Keith Carradine born?
# A: Keith Ian Carradine was born August 8, 1949.
# Q: Is he married?
# A: Keith Carradine married Sandra Will on February 6, 1982. ]
# Question: Do they have any children?
# Rewrite: Do Keith Carradine and Sandra Will have any children?

# Context: {conversational_context}
# Question: {query}
# """

CQR_TEMPLATE = """Given the following conversation and a follow up question, rephrase the follow up \
question to be a standalone question.

Chat History:
{history}
Follow Up Input: {question}
"""



class Iternlm2Chat20BConversationSummaryChain(Iternlm2Chat7BChatChain):
    model_id = LLMModelType.INTERNLM2_CHAT_20B
    meta_instruction_prompt_template = CQR_TEMPLATE
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
            role = his['role']
            assert role in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
            if role == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"Q: {his['content']}")
            else:
                conversational_contexts.append(f"A: {his['content']}")

        conversational_context = "\n".join(conversational_contexts)
        prompt = cls.build_prompt(
            cls.meta_instruction_prompt_template.format(
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
            role = his.type 
            content = his.content
            assert role in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE],(role,[HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE])
            if role == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"Q: {content}")
            else:
                conversational_contexts.append(f"A: {content}")
        conversational_context = "\n".join(conversational_contexts)
        return conversational_context
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        cqr_template = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(CQR_TEMPLATE),
            AIMessage(content="Standalone Question: ")
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
