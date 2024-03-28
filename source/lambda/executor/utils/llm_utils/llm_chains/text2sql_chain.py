# rag llm chains

from typing import Any, List, Mapping, Optional

from langchain.schema.runnable import RunnableLambda,RunnablePassthrough

from ...constant import IntentType,QUERY_TRANSLATE_TYPE
from ...prompt_template import (
    convert_chat_history_from_fstring_format
)
from ..llm_models import Model
from .llm_chain_base import LLMChain
from langchain.prompts import (
    PromptTemplate,ChatPromptTemplate,
    HumanMessagePromptTemplate,AIMessagePromptTemplate,SystemMessagePromptTemplate,
)
from langchain.schema.messages import (
    BaseMessage,_message_from_dict,SystemMessage
)



BEDROCK_TEXT2SQL_SYSTEM_PROMPT = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

Here are some documents for you to reference for your query:
<docs>
{context}
</docs>"""

def get_claude_rag_context(contexts:list):
    assert isinstance(contexts,list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i,context in enumerate(contexts):
        context_xml = context_template.format(
            index = i+1,
            content = context
        )
        context_xmls.append(context_xml)
    
    context = "\n".join(context_xmls)
    return context

def get_claude_chat_rag_prompt(chat_history:List[BaseMessage]):
    chat_messages = [
        SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_SYSTEM_PROMPT)
    ]
    
    chat_messages = chat_messages + chat_history 
    chat_messages += [
        HumanMessagePromptTemplate.from_template("{query}")
        ]
    context_chain = RunnablePassthrough.assign(
        context=RunnableLambda(
            lambda x: get_claude_rag_context(x['contexts'])
                )
        )
        
    return context_chain | ChatPromptTemplate.from_messages(chat_messages)

class Claude3Text2SQLChain(LLMChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    intent_type = IntentType.TEXT2SQL_SQL_GEN.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)

        # history
        chat_history = kwargs.get('chat_history',[])
        chat_messages = [SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_SYSTEM_PROMPT)]
        chat_messages = chat_messages + chat_history 
        chat_messages += [
            HumanMessagePromptTemplate.from_template("{query}")
            ]
        context_chain = RunnablePassthrough.assign(
            context=RunnableLambda(
                lambda x: get_claude_rag_context(x['contexts'])
                    )
            )
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
        if stream:
            chain = chain | RunnableLambda(lambda x: llm.stream(x.messages)) | RunnableLambda(lambda x:(i.content for i in x))
        else:
            chain = chain | llm | RunnableLambda(lambda x:x.content)
        return chain 

class Claude3HaikuText2SQLChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

class Claude3SonnetText2SQLChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# class Claude3OpusText2SQLChain(Claude3Text2SQLChain):
#     model_id = "anthropic.claude-3-haiku-20240307-v1:0"
