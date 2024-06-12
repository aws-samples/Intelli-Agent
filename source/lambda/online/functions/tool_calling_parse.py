"""
tool calling parse, convert content by llm to dict
"""
from typing import List
import re
from langchain_core.messages import(
    ToolCall
) 
from common_utils.exceptions import ToolNotExistError,ToolParameterNotExistError

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
    def parse_tool(cls,model_id,*args,**kwargs):
        target_cls = cls.model_map[model_id]
        return target_cls.parse_tool(*args,**kwargs)
        

class Claude3SonnetFToolCallingParse(ToolCallingParse):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    @staticmethod
    def convert_anthropic_xml_to_dict(model_id,function_calls:List[str], tools:list[dict]) -> List[dict]:
        # formatted_tools = [convert_to_openai_function(tool) for tool in tools]
        tool_calls:list[ToolCall] = []
        tools_mapping = {tool['name']:tool for tool in tools}
        for function_call in function_calls:
            tool_names = re.findall(r'<tool_name>(.*?)</tool_name>', function_call, re.S)
            assert len(tool_names) == 1, function_call 
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
    def parse_tool(cls,function_calls:list[dict],tools:list[dict]) -> list:
        if not function_calls:
            return []
        return cls.convert_anthropic_xml_to_dict(
            cls.model_id,
            function_calls=function_calls,
            tools=tools
        )

class Claude3HaikuToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


class Claude2ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-v2"


class Claude21ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-instant-v1"


parse_tool_calling = ToolCallingParse.parse_tool



        






