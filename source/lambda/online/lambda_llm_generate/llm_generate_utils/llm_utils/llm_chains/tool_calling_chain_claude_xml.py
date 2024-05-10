# tool calling chain
import json
import os
import sys
from functools import lru_cache
from random import Random
from typing import List 
import re

from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

from langchain_core.messages import(
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage
) 
from langchain_anthropic.experimental import _get_type
from langchain.prompts import ChatPromptTemplate,HumanMessagePromptTemplate,AIMessagePromptTemplate

from langchain_core.messages import HumanMessage,AIMessage,SystemMessage

from utils.constant import (
    MessageType,
    LLMTaskType
)

from .llm_chain_base import LLMChain
from ..llm_models import Model


SYSTEM_MESSAGE_PROMPT =("In this environment you have access to a set of tools you can use to answer the user's question.\n"
        "\n"
        "You may call them like this:\n"
        "<function_calls>\n"
        "<invoke>\n"
        "<tool_name>$TOOL_NAME</tool_name>\n"
        "<parameters>\n"
        "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
        "...\n"
        "</parameters>\n"
        "</invoke>\n"
        "</function_calls>\n"
        "\n"
        "Here are the tools available:\n"
        "<tools>\n"
        "{tools}"
        "\n</tools>"
    )

TOOL_FORMAT = """<tool_description>
<tool_name>{tool_name}</tool_name>
<description>{tool_description}</description>
<parameters>
{formatted_parameters}
</parameters>
</tool_description>"""

TOOL_PARAMETER_FORMAT = """<parameter>
<name>{parameter_name}</name>
<type>{parameter_type}</type>
<description>{parameter_description}</description>
</parameter>"""

TOOL_EXECUTE_SUCCESS_TEMPLATE = """
<function_results>
<result>
<tool_name>{tool_name}</tool_name>
<stdout>
{result}
</stdout>
</result>
</function_results>
"""

TOOL_EXECUTE_FAIL_TEMPLATE = """
<function_results>
<error>
{error}
</error>
</function_results>
"""


def convert_openai_tool_to_anthropic(tools:list[dict])->str:
    formatted_tools = tools
    tools_data = [
        {
            "tool_name": tool["name"],
            "tool_description": tool["description"],
            "formatted_parameters": "\n".join(
                [
                    TOOL_PARAMETER_FORMAT.format(
                        parameter_name=name,
                        parameter_type=_get_type(parameter),
                        parameter_description=parameter.get("description"),
                    )
                    for name, parameter in tool["parameters"]["properties"].items()
                ]
            ),
        }
        for tool in formatted_tools
    ]
    tools_formatted = "\n".join(
        [
            TOOL_FORMAT.format(
                tool_name=tool["tool_name"],
                tool_description=tool["tool_description"],
                formatted_parameters=tool["formatted_parameters"],
            )
            for tool in tools_data
        ]
    )
    return tools_formatted

def convert_anthropic_xml_to_dict(xml_text:str,tools:list[dict]):
    # formatted_tools = [convert_to_openai_function(tool) for tool in tools]
    tool_names = re.findall(r'<tool_name>(.*?)</tool_name>', xml_text, re.DOTALL)
    assert len(tool_names) == 1, xml_text 
    tool_name = tool_names[0].strip()
    
    cur_tool = None
    formatted_tools = tools
    for tool, formatted_tool in zip(tools,formatted_tools):
        if formatted_tool['name'] == tool_name:
            cur_tool = tool
            break 
    
    assert cur_tool is not None,xml_text

    formatted_tool = convert_to_openai_function(cur_tool)
    
    arguments = {}
    for parameter_key in formatted_tool['parameters']['required']:
        value = re.findall(f'<{parameter_key}>(.*?)</{parameter_key}>', xml_text, re.DOTALL)
        assert len(value) == 1,xml_text
        arguments[parameter_key] = value[0].strip()
    return {'tool_name':tool_name,'arguments':arguments,"tool":cur_tool}


class Claude2ToolCallingChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = LLMTaskType.TOOL_CALLING
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.1, "top_p": 0.9}

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        tools:list = kwargs['tools']
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        tools_formatted = convert_openai_tool_to_anthropic(tools)
         
        tool_calling_template = ChatPromptTemplate.from_messages(
            [
            SystemMessage(content=SYSTEM_MESSAGE_PROMPT.format(
                tools=tools_formatted
                )),
            ("placeholder", "{chat_history}"),
            HumanMessagePromptTemplate.from_template("{query}"),
        ])


        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        chain = tool_calling_template | llm | 
        
        return chain
    
    @staticmethod
    def parse_tools_to_json(content):
