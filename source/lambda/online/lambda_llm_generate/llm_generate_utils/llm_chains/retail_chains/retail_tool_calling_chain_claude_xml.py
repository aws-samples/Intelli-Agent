# tool calling chain
import json
from typing import List,Dict,Any
import re
from datetime import datetime 

from langchain.schema.runnable import (
    RunnableLambda,
)

from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate

from langchain_core.messages import AIMessage,SystemMessage,HumanMessage

from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType
)
from functions.tools import get_tool_by_name
from ..llm_chain_base import LLMChain
from ...llm_models import Model

tool_call_guidelines = """<guidlines>
- Don't forget to output <function_calls> </function_calls> when any tool is called.
- 每次回答总是先进行思考，并将思考过程写在<thinking>标签中。请你按照下面的步骤进行思考:
    1. 判断根据当前的上下文是否足够回答用户的问题。
    2. 如果当前的上下文足够回答用户的问题，请调用 `give_final_response` 工具。
    3. 如果当前的上下文不能支持回答用户的问题，你可以考虑调用<tools> 标签中列举的工具。
    4. 如果调用工具对应的参数不够，请调用反问工具 `give_rhetorical_question` 来让用户提供更加充分的信息。
    5. 最后给出你要调用的工具名称。
- Always output with "中文". 
</guidlines>
"""


SYSTEM_MESSAGE_PROMPT=("你是安踏的客服助理小安, 主要职责是处理用户售前和售后的问题。下面是当前用户正在浏览的商品信息:\n<goods_info>\n{goods_info}\n</goods_info>"
        "In this environment you have access to a set of tools you can use to answer the customer's question."
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
        f"\nHere are some guidelines for you:\n{tool_call_guidelines}"
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


class Claude2RetailToolCallingChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.RETAIL_TOOL_CALLING
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
    

    @staticmethod 
    def generate_chat_history(state:dict):
        chat_history = state['chat_history'] \
            + [{"role": "user","content":state['query']}] \
            + state['agent_chat_history']
        return {"chat_history":chat_history}

        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        tools:list[dict] = kwargs['tools']

        tool_names = [tool['name'] for tool in tools]

        # add two extral tools
        if "give_rhetorical_question" not in tool_names:
            tools.append(get_tool_by_name("give_rhetorical_question").tool_def)

        if "give_final_response" not in tool_names:
            tools.append(get_tool_by_name("give_final_response").tool_def)

        fewshot_examples = kwargs.get('fewshot_examples',[])
        
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        tools_formatted = convert_openai_tool_to_anthropic(tools)
        goods_info = kwargs['goods_info']

        if fewshot_examples:
            system_prompt = SYSTEM_MESSAGE_PROMPT_WITH_FEWSHOT_EXAMPLES.format(
                tools=tools_formatted,
                fewshot_examples=cls.format_fewshot_examples(
                    fewshot_examples
                    ),
                goods_info = goods_info
            )
        else:
            system_prompt = SYSTEM_MESSAGE_PROMPT.format(
                tools=tools_formatted,
                goods_info=goods_info
            )
         
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
        chain = RunnableLambda(cls.generate_chat_history) | tool_calling_template \
            | RunnableLambda(lambda x: x.messages ) \
            | llm | RunnableLambda(lambda message:cls.parse_function_calls_from_ai_message(
                message
            ))
        
        return chain


class Claude21RetailToolCallingChain(Claude2RetailToolCallingChain):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceRetailToolCallingChain(Claude2RetailToolCallingChain):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude3SonnetRetailToolCallingChain(Claude2RetailToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuRetailToolCallingChain(Claude2RetailToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


MIXTRAL8X7B_QUERY_TEMPLATE = """下面是客户和客服的历史对话信息:
{chat_history}

当前客户的问题是: {query}

请你从安踏客服助理小安的角度回答客户当前的问题。你需要使用上述提供的各种工具进行回答。"""


class Mixtral8x7bRetailToolCallingChain(Claude2RetailToolCallingChain):
    model_id = LLMModelType.MIXTRAL_8X7B_INSTRUCT
    default_model_kwargs = {"max_tokens": 1000, "temperature": 0.01,"stop":["</function_calls>"]}

    @classmethod
    def parse_function_calls_from_ai_message(cls,message:AIMessage):
        content = message.content.replace("\_","_")
        function_calls:List[str] = re.findall("<function_calls>(.*?)</function_calls>", content + "</function_calls>",re.S)
        if function_calls:
            function_calls = [function_calls[0]]
        if not function_calls:
            content = message.content
        return {
                "function_calls": function_calls,
                "content": content
            } 
    
    @staticmethod 
    def chat_history_to_string(chat_history:list[dict]):
        chat_history_lc = ChatPromptTemplate.from_messages([
             ("placeholder", "{chat_history}")
        ]).invoke({"chat_history":chat_history}).messages

        chat_history_strs = []
        for message in chat_history_lc:
            assert isinstance(message,(HumanMessage,AIMessage)),message
            if isinstance(message,HumanMessage):
                chat_history_strs.append(f"客户: {message.content}")
            else:
                chat_history_strs.append(f"客服: {message.content}")
        return "\n".join(chat_history_strs)     

    
    @classmethod
    def generate_chat_history(cls,state:dict):
        chat_history_str = cls.chat_history_to_string(state['chat_history'])

        chat_history = [{
            "role": "user",
            "content": MIXTRAL8X7B_QUERY_TEMPLATE.format(
                chat_history=chat_history_str,
                query = state['query']
            )
            }] + state['agent_chat_history']
        return {"chat_history": chat_history}

        




