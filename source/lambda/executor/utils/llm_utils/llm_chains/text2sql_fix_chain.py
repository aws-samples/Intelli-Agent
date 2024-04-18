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

support_funtions = ['fix']

support_model_ids_map = {
    "anthropic.claude-3-haiku-20240307-v1:0":"haiku-20240307v1-0",
    "anthropic.claude-3-sonnet-20240229-v1:0":"sonnet-20240229v1-0"
}

system_prompt_dict = {}

system_prompt_dict['fix_haiku-20240307v1-0_20240407063835'] = """
This is error when running the generated sql:

<running_error>

{running_error}

</running_error>

"Given the following database schema, transform the following natural language requests into valid SQL queries. \n\n"

"<table_schema> \n"

"{sql_schema} \n"

"</table_schema> \n"

"You ALWAYS follow these guidelines when writing your response: \n"

"<guidelines> \n"

"{guidance} \n"
    
"</guidelines> \n"


"Think about the sql question before continuing. If it's not about writing SQL statements, say 'Sorry, please ask something relating to querying tables'. \n\n"

"Think about your answer first before you respond. Put your response in <query></query> tags. \n\n"

"""


def get_claude_rag_context(contexts:list, name='doc'):
    assert isinstance(contexts,list), contexts
    context_xmls = []
    context_template = """<{name} index="{index}">\n{content}\n</example>"""
    for i,context in enumerate(contexts):
        context_xml = context_template.format(
            name = name,
            index = i+1,
            content = context
        )
        context_xmls.append(context_xml)
    
    context = "\n".join(context_xmls)
    return context

def get_claude_text2sql_rag_prompt(chat_history:List[BaseMessage]):
    chat_messages = [
        SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_GEN_SYSTEM_PROMPT)
    ]
    
    chat_messages = chat_messages + chat_history 
    chat_messages += [
        HumanMessagePromptTemplate.from_template("{query}")
        ]
    context_chain = RunnablePassthrough.assign(
        context=RunnableLambda(
            lambda x: get_claude_rag_context(x['contexts'], name='example')
                )
        )
        
    return context_chain | ChatPromptTemplate.from_messages(chat_messages)

def claude_text2sql_gen_func(chat_history):
    chat_messages = [SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_GEN_SYSTEM_PROMPT)]
    chat_messages = chat_messages + chat_history 
    chat_messages += [
        HumanMessagePromptTemplate.from_template("{query}")
        ]
    context_chain = RunnablePassthrough.assign(
        context=RunnableLambda(
            lambda x: get_claude_rag_context(x['contexts'], name='example')
                )
        )
    chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
    
    return chain

def claude_text2sql_re_gen_func(chat_history):
    chat_messages = [SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_GEN_SYSTEM_PROMPT)]
    # chat_messages = chat_messages + chat_history 
    chat_messages += [
        HumanMessagePromptTemplate.from_template("{chat_history}\n\n{query}")
        ]
    context_chain = RunnablePassthrough.assign(
        context=RunnableLambda(
            lambda x: get_claude_rag_context(x['contexts'], name='example')
                )
        )
    chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
    
    return chain
class Claude3Text2SQLChain(LLMChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    intent_type = IntentType.TEXT2SQL_SQL_GEN.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)

        # history
        chat_history = kwargs.get('chat_history',[])
        if cls.intent_type == IntentType.TEXT2SQL_SQL_GEN.value:
            chain = claude_text2sql_gen_func(chat_history)
        elif cls.intent_type == IntentType.TEXT2SQL_SQL_RE_GEN.value:
            chain = claude_text2sql_re_gen_func(chat_history)
        # chat_messages = [SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_SYSTEM_PROMPT)]
        # chat_messages = chat_messages + chat_history 
        # chat_messages += [
        #     HumanMessagePromptTemplate.from_template("{query}")
        #     ]
        # context_chain = RunnablePassthrough.assign(
        #     context=RunnableLambda(
        #         lambda x: get_claude_rag_context(x['contexts'], name='example')
        #             )
        #     )
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
            )
        # chain = context_chain | ChatPromptTemplate.from_messages(chat_messages)
        if stream:
            chain = chain | RunnableLambda(lambda x: llm.stream(x.messages)) | RunnableLambda(lambda x:(i.content for i in x))
        else:
            chain = chain | llm | RunnableLambda(lambda x:x.content)
        return chain 

class Claude3HaikuText2SQLChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

class Claude3HaikuText2SQLReGenChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    intent_type = IntentType.TEXT2SQL_SQL_RE_GEN.value

class Claude3SonnetText2SQLChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

class Claude3SonnetText2SQLReGenChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    intent_type = IntentType.TEXT2SQL_SQL_RE_GEN.value
