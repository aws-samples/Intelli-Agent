"""
tool calling parse, convert content by llm to dict
"""
from typing import List
import re
from langchain_core.messages import(
    ToolCall
) 
from common_utils.exceptions import (
    ToolNotExistError,
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from functions.tool_execute_result_format import format_tool_call_results

class ToolCallingParseMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        if name == "ToolCallingParse":
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls
    

class ToolCallingParse(metaclass=ToolCallingParseMeta):
    model_map = {}

    @classmethod
    def parse_tool(cls,agent_output):
        target_cls = cls.model_map[agent_output['current_agent_model_id']]
        return target_cls.parse_tool(agent_output)
        

class Claude3SonnetFToolCallingParse(ToolCallingParse):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    @staticmethod
    def convert_anthropic_xml_to_dict(model_id,function_calls:List[str], tools:list[dict]) -> List[dict]:
        # formatted_tools = [convert_to_openai_function(tool) for tool in tools]
        tool_calls:list[ToolCall] = []
        tools_mapping = {tool['name']:tool for tool in tools}
        for function_call in function_calls:
            tool_names = re.findall(r'<tool_name>(.*?)</tool_name>', function_call, re.S)
            if len(tool_names) > 1:
                raise MultipleToolNameError(function_call_content=function_call)
           
            tool_name = tool_names[0].strip()

            if tool_name not in tools_mapping:
                raise ToolNotExistError(
                        tool_name=tool_name,
                        function_call_content=function_call
                        )
            cur_tool:dict = tools_mapping[tool_name]
            arguments = {}
            for parameter_key in cur_tool['parameters']['required']:
                value = re.findall(f'<{parameter_key}>(.*?)</{parameter_key}>', function_call, re.DOTALL)
                if not value:
                    raise ToolParameterNotExistError(
                        tool_name=tool_name,
                        parameter_key=parameter_key,
                        function_call_content=function_call
                        )
                # TODO, add too many parameters error
                assert len(value) == 1,(parameter_key,function_call)
                arguments[parameter_key] = value[0].strip()
            for parameter_key in cur_tool['parameters']['properties'].keys():
                value = re.findall(f'<{parameter_key}>(.*?)</{parameter_key}>', function_call, re.DOTALL)
                if value:
                    arguments[parameter_key] = value[0].strip()
            tool_calls.append(dict(name=tool_name,kwargs=arguments,model_id=model_id))
        return tool_calls

    @classmethod
    def tool_not_found(cls,agent_message):
        tool_format = ("<function_calls>\n"
            "<invoke>\n"
            "<tool_name>$TOOL_NAME</tool_name>\n"
            "<parameters>\n"
            "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
            "...\n"
            "</parameters>\n"
            "</invoke>\n"
            "</function_calls>\n"
            )
        e = ToolNotFound()
        e.agent_message = agent_message
        e.error_message = {
                    "role": "user",
                    "content": f"当前没有解析到tool,请检查tool调用的格式是否正确，并重新输出某个tool的调用。注意正确的tool调用格式应该为: {tool_format}。\n如果你认为当前不需要调用其他工具，请直接调用“give_final_response”工具进行返回。"
                }
        return e
    
    @classmethod
    def parse_tool(
        cls,
        agent_outout
    ) -> list:
        function_calls = agent_outout['agent_output']['function_calls']
        tools = agent_outout['current_agent_tools_def']
        agent_message = {
            "role": "ai",
            "content": agent_outout['agent_output']['content']
        }

        if not function_calls:
            raise cls.tool_not_found(agent_message=agent_message)
        try:
            tool_calls = cls.convert_anthropic_xml_to_dict(
                cls.model_id,
                function_calls=function_calls,
                tools=tools
            )
            if not tool_calls:
                raise cls.tool_not_found(agent_message=agent_message)
            return {"agent_message": agent_message,"tool_calls":tool_calls}
        except (ToolNotExistError,ToolParameterNotExistError,MultipleToolNameError) as e:
            e.agent_message = agent_message
            e.error_message = {
                "role": "user",
                "content": format_tool_call_results(
                    model_id = agent_outout['current_agent_model_id'],
                    tool_output=[{
                        "code": 1,
                        "result": e.to_agent(),
                        "tool_name": e.tool_name
                    }]
                )
        }


class Claude3HaikuToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


class Claude2ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-v2"


class Claude21ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-instant-v1"


class Mixtral8x7bToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "mistral.mixtral-8x7b-instruct-v0:1"


parse_tool_calling = ToolCallingParse.parse_tool



        






