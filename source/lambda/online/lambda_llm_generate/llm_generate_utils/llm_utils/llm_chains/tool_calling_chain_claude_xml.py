# tool calling chain
import json
import os
import sys
from functools import lru_cache
from random import Random
from typing import List,Dict,Any
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
    BaseMessage,
    ToolCall
) 
from langchain.prompts import ChatPromptTemplate,HumanMessagePromptTemplate,AIMessagePromptTemplate

from langchain_core.messages import HumanMessage,AIMessage,SystemMessage

from common_utils.constant import (
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
        "\nAnswer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided."
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


def _get_type(parameter: Dict[str, Any]) -> str:
    if "type" in parameter:
        return parameter["type"]
    if "anyOf" in parameter:
        return json.dumps({"anyOf": parameter["anyOf"]})
    if "allOf" in parameter:
        return json.dumps({"allOf": parameter["allOf"]})
    return json.dumps(parameter)


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

def convert_anthropic_xml_to_dict(function_calls:List[str], tools:list[dict]) -> List[dict]:
    # formatted_tools = [convert_to_openai_function(tool) for tool in tools]
    tool_calls:list[ToolCall] = []
    for function_call in function_calls:
        tool_names = re.findall(r'<tool_name>(.*?)</tool_name>', function_call, re.S)
        if not tool_names:
            return []
        assert len(tool_names) == 1, function_call 

        for tool_name in tool_names:
            tool_name = tool_names[0].strip()
            cur_tool = None
            formatted_tools = tools
            for tool, formatted_tool in zip(tools,formatted_tools):
                if formatted_tool['name'] == tool_name:
                    cur_tool = tool
                    break 
            
            assert cur_tool is not None,function_call
            # formatted_tool = convert_to_openai_function(cur_tool)
            arguments = {}
            for parameter_key in formatted_tool['parameters']['required']:
                value = re.findall(f'<{parameter_key}>(.*?)</{parameter_key}>', function_call, re.DOTALL)
                assert len(value) == 1,function_call
                arguments[parameter_key] = value[0].strip()
            
            tool_calls.append(dict(name=tool_name,args=arguments))
    
    return tool_calls


class Claude2ToolCallingChain(LLMChain):
    model_id = "anthropic.claude-v2"
    intent_type = LLMTaskType.TOOL_CALLING
    default_model_kwargs = {
        "max_tokens": 2000,
        "temperature": 0.1,
        "top_p": 0.9,
        "stop_sequences": ["\n\nHuman:", "\n\nAssistant","</function_calls>"],
        }
    
    @staticmethod
    def parse_tools_from_ai_message(message:AIMessage,tools:list[dict]):
        function_calls:List[str] = re.findall("<function_calls>(.*?)</function_calls>", message.content + "</function_calls>",re.S)
        if not function_calls:
            return []
        
        tool_calls = convert_anthropic_xml_to_dict(function_calls,tools)
        message.tool_calls = tool_calls
        return {"tool_calls":tool_calls,"content":message.content}
    
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
        chain = tool_calling_template | RunnableLambda(lambda x:x.messages) | llm | RunnableLambda(lambda message:cls.parse_tools_from_ai_message(message,tools=tools))
        
        return chain


class Claude21ToolCallingChain(Claude2ToolCallingChain):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceToolCallingChain(Claude2ToolCallingChain):
    model_id = "anthropic.claude-instant-v1"


class Claude3SonnetToolCallingChain(Claude2ToolCallingChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


class Claude3HaikuToolCallingChain(Claude2ToolCallingChain):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


