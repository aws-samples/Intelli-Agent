# conversation summary chain
from typing import List 

from langchain.schema.runnable import (
    RunnableLambda,
    RunnablePassthrough,
)


from ..llm_models import Model
from .llm_chain_base import LLMChain
from common_utils.constant import (
    MessageType,
    LLMTaskType
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


CQR_TEMPLATE = """# CONTEXT # 
下面有一段客户和客服的对话数据(包含在<chat_history>里面)，以及当前客户的一个回复(包含在<current_user_reply>)。
<chat_history>
{chat_history}
<chat_history>

当前用户的回复:
<current_user_reply>
{query}
<current_user_reply>

#########

# OBJECTIVE #
请你站在客户的角度，结合上述对话数据对当前客户的回复内容进行改写，使得改写之后的内容可以作为一个独立的句子。

#########

# STYLE #
改写后的回复需要和<current_reply>里面的内容意思一致。

#########

# RESPONSE FORMAT #
请直接用中文进行回答
"""


class Claude2RetailConversationSummaryChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.1, "top_p": 0.9}
    CQR_TEMPLATE = CQR_TEMPLATE
    @staticmethod
    def create_conversational_context(chat_history:List[BaseMessage]):
        conversational_contexts = []
        for his in chat_history:
            role = his.type 
            content = his.content
            assert role in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE],(role,[HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE])
            if role == HUMAN_MESSAGE_TYPE:
                conversational_contexts.append(f"客户: {content}")
            else:
                conversational_contexts.append(f"客服: {content}")
        conversational_context = "\n".join(conversational_contexts)
        return conversational_context
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        cqr_template = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(cls.CQR_TEMPLATE),
            AIMessage(content="好的，站在客户的角度，我将当前用户的回复内容改写为: ")
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
            | RunnableLambda(lambda x: cqr_template.format(chat_history=x['conversational_context'],query=x['query'])) \
            | llm | RunnableLambda(lambda x: x.content)
        
        return cqr_chain


class Claude21RetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceRetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetRetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuRetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"



MIXTRAL_CQR_TEMPLATE = """下面有一段客户和客服的对话，以及当前客户的一个回复,请你站在客户的角度，结合上述对话数据对当前客户的回复内容进行改写，使得改写之后的内容可以作为一个独立的句子。下面是改写的要求:
- 改写后的回复需要和当前客户的一个回复的内容意思一致。
- 请直接用中文进行回答。

# 客户和客服的对话:
{chat_history}

# 当前客户的回复:
{query}
"""


class Mixtral8x7bRetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "mistral.mixtral-8x7b-instruct-v0:1"
    default_model_kwargs = {"max_tokens": 1000, "temperature": 0.01}
    CQR_TEMPLATE = MIXTRAL_CQR_TEMPLATE


class GLM4Chat9BRetailConversationSummaryChain(Claude2RetailConversationSummaryChain):
    model_id = "glm-4-9b-chat"
    intent_type = LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE
    CQR_TEMPLATE = MIXTRAL_CQR_TEMPLATE

    @classmethod
    def create_chat_history(cls,x):
        conversational_context = cls.create_conversational_context(
                    convert_to_messages(x["chat_history"])
        )
        prompt = cls.CQR_TEMPLATE.format(
            chat_history=conversational_context,
            query=x['query']
        )
        return {"chat_history": [
            {
                "role":"user",
                "content": prompt
            },
            {
                "role":"assistant",
                "content": "好的，站在客户的角度，我将当前用户的回复内容改写为: "
            }
            ]}


    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        cqr_chain = RunnableLambda(lambda x: cls.create_chat_history(x)) \
            | llm
        
        return cqr_chain

