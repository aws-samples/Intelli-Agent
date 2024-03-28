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
BACK_BEDROCK_TEXT2SQL_GEN_SYSTEM_PROMPT = """
Transform the following natural language requests into valid SQL queries. Assume a database with the following tables and columns exists:

<database_schema>
Products:
- product_id (INT, PRIMARY KEY)
- product_type_code (VARCHAR)
- product_name (VARCHAR)
</database_schema>

Some example pairs of question and corresponding SQL query are provided based on similar problems:

<examples>
{example_pairs}
</examples>

Think about your answer first before you respond. Put your response in <query></query> tags.

"""

BEDROCK_TEXT2SQL_GEN_SYSTEM_PROMPT = """

Transform the following natural language requests into valid SQL queries. Assume a database with the following database schema exists

<database_schema>
CREATE EXTERNAL TABLE IF NOT EXISTS `cf_log_database`.`product` (
  `product_id` int COMMENT '产品ID',
  `product_type_code` string COMMENT '产品类型，例如Clothes, Hardware',
  `product_name` string COMMENT '产品名称',
);
</database_schema>

Some example pairs of question and corresponding SQL query are provided based on similar problems:

<examples>
{contexts}
</examples>

Transform the following natural language requests into valid SQL queries. 

Think about your answer first before you respond. Put your response in <query></query> tags.

"""

BEDROCK_TEXT2SQL_RE_GEN_SYSTEM_PROMPT = """
Assume a database with the following tables and columns exists:

Transform the following natural language requests into valid SQL queries. 

<database_schema>
CREATE  TABLE  continents(
    ContId  int  primary key ,
    Continent  text ,
    foreign  key(ContId) references  countries(Continent)
);
CREATE  TABLE  countries(
    CountryId  int  primary key ,
    CountryName  text ,
    Continent  int ,
    foreign  key(Continent) references  continents(ContId)
);
</database_schema>

Some example pairs of question and corresponding SQL query are provided based on similar problems:

<examples>
{contexts}
</examples>

Think about your answer first before you respond. Put your response in <query></query> tags.

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
    chat_messages = [SystemMessagePromptTemplate.from_template(BEDROCK_TEXT2SQL_RE_GEN_SYSTEM_PROMPT)]
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
            chain = claude_text2sql_gen_func(chat_history)
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

class Claude3SonnetText2SQLChain(Claude3Text2SQLChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# class Claude3OpusText2SQLChain(Claude3Text2SQLChain):
#     model_id = "anthropic.claude-3-haiku-20240307-v1:0"
