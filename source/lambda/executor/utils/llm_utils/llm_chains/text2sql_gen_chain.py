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

from ..llm_prompts import text2sql_table_prompts

support_funtions = ['gen']

support_model_ids_map = {
    "anthropic.claude-3-haiku-20240307-v1:0":"haiku-20240307v1-0",
    "anthropic.claude-3-sonnet-20240229-v1:0":"sonnet-20240229v1-0"
}

support_versions = ['20240407063835']

system_prompt_dict = {}

system_prompt_dict['gen_haiku-20240307v1-0_20240407063835'] = """
    Assume a database with the following tables and columns exists:

    Given the following database schema, transform the following natural language requests into valid SQL queries.

    <table_schema>

    {sql_schema}

    </table_schema>

    You ALWAYS follow these guidelines when writing your response:

    <guidelines>

    {sql_guidance}
    
    </guidelines> 


    Think about the sql question before continuing. If it's not about writing SQL statements, say 'Sorry, please ask something relating to querying tables'.

    Think about your answer first before you respond. Put your response in <query></query> tags.

    """

system_prompt_dict['gen_sonnet-20240229v1-0_20240407063835'] = """
    You are a Amazon Redshift expert. Assume a database with the following tables and columns exists:

    Given the following database schema, transform the following natural language requests into valid SQL queries.

    <table_schema>

    {sql_schema}

    </table_schema>

    You ALWAYS follow these guidelines when writing your response:

    <guidelines>

    {sql_guidance}
    
    </guidelines> 


    Think about the sql question before continuing. If it's not about writing SQL statements, say 'Sorry, please ask something relating to querying tables'.

    Think about your answer first before you respond. Put your response in <query></query> tags.

    """

class SystemPromptMapper:
    def __init__(self):
        self.variable_map = system_prompt_dict

    def get_variable(self, name):
        return self.variable_map.get(name)

system_prompt_mapper = SystemPromptMapper()
sql_prompt_mapper = text2sql_table_prompts.SQLPromptMapper()

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


def claude_text2sql_gen_func(chat_history, model_id, **kwargs):
    system_version = kwargs.get('system_version', '20240407063835')
    table_version = kwargs.get('table_version', '20240407063835')
    guidance_version = kwargs.get('guidance_version', '20240407063835')
    gen_table_with_version = f'gen_{support_model_ids_map[model_id]}_{system_version}'

    BASESYSTEM_PROMPT = f"{system_prompt_mapper.get_variable(gen_table_with_version)}"

    table_with_version = f'table_{support_model_ids_map[model_id]}_{table_version}'
    guidance_with_version = f'guidance_{support_model_ids_map[model_id]}_{guidance_version}'

    sql_schema = f"{sql_prompt_mapper.get_variable(table_with_version)}\n"
    sql_guidance = f"{sql_prompt_mapper.get_variable(guidance_with_version)}\n"
    
    UPDATE_SYSTEM_PROMPT = BASESYSTEM_PROMPT.format(sql_schema=sql_schema, sql_guidance=sql_guidance)
    chat_messages = [SystemMessagePromptTemplate.from_template(UPDATE_SYSTEM_PROMPT)]
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

class Claude3Text2SQLGenChain(LLMChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    intent_type = IntentType.TEXT2SQL_SQL_GEN.value

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)

        # history
        chat_history = kwargs.get('chat_history',[])
        chain = claude_text2sql_gen_func(chat_history, cls.model_id, **kwargs)

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

class Claude3HaikuText2SQLGenChain(Claude3Text2SQLGenChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

class Claude3SonnetText2SQLGenChain(Claude3Text2SQLGenChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"