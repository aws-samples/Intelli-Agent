# tool calling chain
import json
from typing import List,Dict,Any
import re

from langchain.schema.runnable import (
    RunnableLambda,
    RunnablePassthrough
)
from common_logic.common_utils.prompt_utils import get_prompt_template

from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate

from langchain_core.messages import AIMessage,SystemMessage

from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType,
    MessageType
)
from common_logic.common_utils.time_utils import get_china_now

from .llm_chain_base import LLMChain
from ..llm_models import Model

incorrect_tool_call_example = """Here is an example of an incorrectly formatted tool call, which you should avoid.
<incorrect_tool_calling>
<function_calls>
<invoke>
<tool_name>tool_name</tool_name>
<parameters>
<parameter>
<name>question</name>
<type>string</type>
<value>value</value>
</parameter>
</parameters>
</invoke>
</function_calls>
</incorrect_tool_calling>

In this incorrect tool calling example, the parameter `name` should form a <name> XLM tag. 
"""


SYSTEM_MESSAGE_PROMPT =(f"In this environment you have access to a set of tools you can use to answer the user's question.\n"
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
        "\nHere are some guidelines for you:\n{tool_call_guidelines}."
        f"\n{incorrect_tool_call_example}"
    )

SYSTEM_MESSAGE_PROMPT_WITH_FEWSHOT_EXAMPLES = SYSTEM_MESSAGE_PROMPT + (
    "Some examples of tool calls are given below, where the content within <query></query> represents the most recent reply in the dialog."
    "\n{fewshot_examples}"
)

TOOL_FORMAT = """<tool_description>
<tool_name>{tool_name}</tool_name>
<description>{tool_description}</description>
<required_parameters>
{formatted_required_parameters}
</required_parameters>
<optional_parameters>
{formatted_optional_parameters}
</optional_parameters>
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

AGENT_SYSTEM_PROMPT = "你是一个亚马逊云科技的AI助理，你的名字是亚麻小Q。今天是{date_str},{weekday}. "


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
            "formatted_required_parameters": "\n".join(
                [
                    TOOL_PARAMETER_FORMAT.format(
                        parameter_name=name,
                        parameter_type=_get_type(parameter),
                        parameter_description=parameter.get("description"),
                    ) for name, parameter in tool["parameters"]["properties"].items()
                    if name in tool["parameters"].get("required", [])
                ]
            ),
            "formatted_optional_parameters": "\n".join(
                [
                    TOOL_PARAMETER_FORMAT.format(
                        parameter_name=name,
                        parameter_type=_get_type(parameter),
                        parameter_description=parameter.get("description"),
                    ) for name, parameter in tool["parameters"]["properties"].items()
                    if name not in tool["parameters"].get("required", [])
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
                formatted_required_parameters=tool["formatted_required_parameters"],
                formatted_optional_parameters=tool["formatted_optional_parameters"],
            )
            for tool in tools_data
        ]
    )
    return tools_formatted


class Claude2ToolCallingChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.TOOL_CALLING
    default_model_kwargs = {
        "max_tokens": 2000,
        "temperature": 0.1,
        "top_p": 0.9,
        "stop_sequences": ["\n\nHuman:", "\n\nAssistant","</function_calls>"],
        }

    @staticmethod
    def format_fewshot_examples(fewshot_examples:list[dict]):
        fewshot_example_strs = []
        for fewshot_example in fewshot_examples:
            param_strs = []
            for p,v in fewshot_example['kwargs'].items():
                param_strs.append(f"<{p}>{v}</{p}")
            param_str = "\n".join(param_strs)
            if param_strs:
                param_str += "\n"

            fewshot_example_str = (
                "<example>\n"
                f"<query>{fewshot_example['query']}</query>\n"
                f"<output>\n"
                "<function_calls>\n"
                "<invoke>\n"
                f"<tool_name>{fewshot_example['name']}</tool_name>\n"
                "<parameters>\n"
                f"{param_str}"
                "</parameters>\n"
                "</invoke>\n"
                "</function_calls>\n"
                "</output>\n"
                "</example>"
            )
            fewshot_example_strs.append(fewshot_example_str)
        fewshot_example_str = '\n'.join(fewshot_example_strs)
        return f"<examples>\n{fewshot_example_str}\n</examples>"
    
    @classmethod
    def parse_function_calls_from_ai_message(cls,message:AIMessage):
        content = "<thinking>" + message.content + "</function_calls>"
        function_calls:List[str] = re.findall("<function_calls>(.*?)</function_calls>", content,re.S)
        if not function_calls:
            content = "<thinking>" +  message.content

        return {
                "function_calls": function_calls,
                "content": content
            } 

    @classmethod
    def create_chat_history(cls,x):
        chat_history = x['chat_history'] + \
            [{"role": MessageType.HUMAN_MESSAGE_TYPE,"content": x['query']}] + \
            x['agent_tool_history']

            
        return chat_history

    @classmethod
    def get_common_system_prompt(cls,system_prompt_template:str):
        now = get_china_now()
        date_str = now.strftime("%Y年%m月%d日")
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[now.weekday()]
        system_prompt = system_prompt_template.format(date=date_str,weekday=weekday)
        return system_prompt
    
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        tools:list = kwargs['tools']
        fewshot_examples = kwargs.get('fewshot_examples',[])

        user_system_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="system_prompt"     
        ).prompt_template

        user_system_prompt = kwargs.get("system_prompt",None) or user_system_prompt

        user_system_prompt = cls.get_common_system_prompt(
            user_system_prompt
        )
        guidelines_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="guidelines_prompt"     
        ).prompt_template

        guidelines_prompt = kwargs.get("guidelines_prompt",None) or guidelines_prompt
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        tools_formatted = convert_openai_tool_to_anthropic(tools)

        if fewshot_examples:
            system_prompt = SYSTEM_MESSAGE_PROMPT_WITH_FEWSHOT_EXAMPLES.format(
                tools=tools_formatted,
                fewshot_examples=cls.format_fewshot_examples(fewshot_examples),
                tool_call_guidelines=guidelines_prompt
            )
        else:
            system_prompt = SYSTEM_MESSAGE_PROMPT.format(
                tools=tools_formatted,
                tool_call_guidelines=guidelines_prompt
            )
        
        system_prompt = user_system_prompt + system_prompt 
        tool_calling_template = ChatPromptTemplate.from_messages(
            [
            SystemMessage(content=system_prompt),
            ("placeholder", "{chat_history}"),
            AIMessage(content="<thinking>")
        ])

        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )
        chain = RunnablePassthrough.assign(chat_history=lambda x: cls.create_chat_history(x)) | tool_calling_template \
            | RunnableLambda(lambda x: print(x.messages) or x.messages ) \
            | llm | RunnableLambda(lambda message:cls.parse_function_calls_from_ai_message(
                message
            ))
        
        return chain


class Claude21ToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35SonnetToolCallingChain(Claude2ToolCallingChain):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
