"""
tool calling parse, convert content by llm to dict
"""
from typing import List
import re
import json  
from langchain_core.messages import(
    ToolCall
) 
from common_logic.common_utils.exceptions import (
    ToolNotExistError,
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from functions.tool_execute_result_format import format_tool_call_results
from common_logic.common_utils.constant import (
    LLMModelType,
    MessageType
)



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
    model_id = LLMModelType.CLAUDE_3_SONNET
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
    
    @classmethod
    def convert_anthropic_xml_to_dict(cls,model_id,function_calls:List[str], tools:list[dict]) -> List[dict]:
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
                    # expand search region
                    # search_region = re.findall(f'<parameter>\n<name>{parameter_key}</name>(.*?)</parameter>', function_call, re.DOTALL)
                    # # print(search_region)
                    # value = re.findall(f'<value>(.*?)</value>', search_region, re.DOTALL)
                    # if not value:
                    raise ToolParameterNotExistError(
                        tool_name=tool_name,
                        parameter_key=parameter_key,
                        function_call_content=function_call,
                        tool_format=f"\n注意正确的工具调用格式应该是下面的:\n{cls.tool_format}\n"
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
        tool_format = cls.tool_format
        e = ToolNotFound()
        e.agent_message = agent_message
        e.error_message = {
                    "role": MessageType.HUMAN_MESSAGE_TYPE,
                    "content": f"当前没有解析到tool,请检查tool调用的格式是否正确，并重新输出某个tool的调用。注意正确的tool调用格式应该为: {tool_format}。\n如果你认为当前不需要调用其他工具，请直接调用“give_final_response”工具进行返回。"
                }
        return e
    
    @classmethod
    def parse_tool(
        cls,
        agent_output
    ) -> list:
        function_calls = agent_output['agent_output']['function_calls']
        tools = agent_output['current_agent_tools_def']
        agent_message = {
            "role": MessageType.AI_MESSAGE_TYPE,
            "content": agent_output['agent_output']['content'],
            "additional_kwargs": {}
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
            
            agent_message['additional_kwargs']['tool_calls'] = tool_calls
            return {"agent_message": agent_message,"tool_calls":tool_calls}
        except (ToolNotExistError,ToolParameterNotExistError,MultipleToolNameError) as e:
            e.error_message = format_tool_call_results(
                    model_id = agent_output['current_agent_model_id'],
                    tool_output=[{
                        "output":{
                            "code": 1,
                            "result": e.to_agent(),
                            "tool_name": e.tool_name}
                        }]
                )['tool_message']
            e.agent_message = agent_message
            raise e 


class Claude3HaikuToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35SonnetFToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"


class Claude2ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = LLMModelType.CLAUDE_2


class Claude21ToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = LLMModelType.CLAUDE_21


class ClaudeInstanceToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Mixtral8x7bToolCallingParse(Claude3SonnetFToolCallingParse):
    model_id = LLMModelType.MIXTRAL_8X7B_INSTRUCT


class GLM4Chat9BToolCallingParse(ToolCallingParse):
    model_id = LLMModelType.GLM_4_9B_CHAT

    @classmethod
    def parse_tool_kwargs(cls,content:str,tools_def:list[dict]):
        tool_name = content.split("\n")[0]
        cur_tool_def = None
        for tool_def in tools_def:
            if tool_def['name'] == tool_name:
                cur_tool_def = tool_def
                break 
        if cur_tool_def is None:
            raise ToolNotExistError(tool_name=tool_name,function_call_content=content)
        tool_params = "\n".join(content.split("\n")[1:]).replace("<|observation|>","").strip()
        tool_params = json.loads(tool_params)
        

        cur_params_names = set(list(tool_params.keys()))
        tool_def_requires = set(cur_tool_def['parameters'].get("required",[]))
        remain_requires = list(tool_def_requires.difference(cur_params_names))
        if remain_requires:
            raise ToolParameterNotExistError(
                tool_name=tool_name,
                parameter_key=remain_requires[0],
                function_call_content=content
                ) 

        return {"name":tool_name,"kwargs":tool_params,"model_id":cls.model_id}


    @classmethod
    def parse_tool(cls,agent_output):
        try:
            content = agent_output['agent_output'].strip()
            # check use tool or direct reply
            tools = agent_output['current_agent_tools_def']
            agent_message = {
                    "role": MessageType.AI_MESSAGE_TYPE,
                    "content": content,
                    "additional_kwargs": {}
                }
            
            assert content.endswith(("<|user|>","<|observation|>")), content
            
            if content.endswith("<|observation|>"):
                # use one tool
                tool_call = cls.parse_tool_kwargs(content,tools_def=tools)
                agent_message['content'] = agent_message['content'].replace(tool_call['name'],"").strip()
                agent_message['additional_kwargs']['tool_calls'] = [tool_call]
            else:
                # default tool is give_final_response
                # response = content.replace("<|user|>","")
                tool_call = {"name":"give_final_response","kwargs":{"response":content},"model_id":cls.model_id}
            return {
                "agent_message": agent_message,
                "tool_calls": [tool_call]
            }
        except (ToolNotExistError, ToolParameterNotExistError, MultipleToolNameError) as e:
            e.agent_message = agent_message
            e.error_message = format_tool_call_results(
                    model_id = agent_output['current_agent_model_id'],
                    tool_output=[{
                        "output":{
                            "code": 1,
                            "result": e.to_agent(),
                            "tool_name": e.tool_name}
                        }]
                )['tool_message']
            raise e 



class Qwen2Instruct7BToolCallingParse(ToolCallingParse):
    model_id = LLMModelType.QWEN2INSTRUCT7B
    FN_NAME = '✿FUNCTION✿'
    FN_ARGS = '✿ARGS✿'
    FN_RESULT = '✿RESULT✿'
    FN_EXIT = '✿RETURN✿'

    tool_format = (f"{FN_NAME}: 工具名称\n"
                   f"{FN_ARGS}: 工具输入\n"
                   f"{FN_RESULT}"
                   )

    thinking_tag = "思考"
    fix_reply_tag = "固定回复"

    @classmethod
    def parse_tool_kwargs(cls,content:str,tools_def:list[dict],agent_message):
        try:
            r = re.match(f"{cls.FN_NAME}(.*?){cls.FN_ARGS}(.*?){cls.FN_RESULT}",content,re.S)
            tool_name = r.group(1).strip().lstrip(":").strip()
            tool_params = json.loads(r.group(2).strip().lstrip(":").strip())
        except Exception as e:
            e = cls.tool_not_found(agent_message,error=str(e))
            raise e

        cur_tool_def = None
        for tool_def in tools_def:
            if tool_def['name'] == tool_name:
                cur_tool_def = tool_def
                break 
        if cur_tool_def is None:
            raise ToolNotExistError(tool_name=tool_name,function_call_content=content)
        
        cur_params_names = set(list(tool_params.keys()))
        tool_def_requires = set(cur_tool_def['parameters'].get("required",[]))
        remain_requires = list(tool_def_requires.difference(cur_params_names))
        
        if remain_requires:
            raise ToolParameterNotExistError(
                tool_name=tool_name,
                parameter_key=remain_requires[0],
                function_call_content=content
                )
        return {"name":tool_name,"kwargs":tool_params,"model_id":cls.model_id}


    @classmethod
    def tool_not_found(cls,agent_message,error=""):
        tool_format = cls.tool_format
        e = ToolNotFound()
        e.agent_message = agent_message
        e.error_message = {
                    "role": MessageType.TOOL_MESSAGE_TYPE,
                    "content": f"\n{cls.FN_RESULT}: 当前没有解析到tool,{error}\n请检查tool调用的格式是否正确，并重新输出某个tool的调用。注意正确的tool调用格式应该为: {tool_format}。"
                }
        return e
    
    @classmethod
    def parse_tool(cls,agent_output):
        thinking_tag = cls.thinking_tag
        try: 
            output:dict = agent_output['agent_output']
            tools = agent_output['current_agent_tools_def']
            agent_message = {
                    "role": MessageType.AI_MESSAGE_TYPE,
                    "content": output['content'],
                    "additional_kwargs": {}
                }
            
            function_calls = output['function_calls']
            if function_calls:
                tool_call = cls.parse_tool_kwargs(function_calls[0],tools_def=tools,agent_message=agent_message)
                agent_message['additional_kwargs']['tool_calls'] = [tool_call]
            else:
                if any(s in output['content'] for s in [cls.FN_ARGS,cls.FN_EXIT,cls.FN_NAME,cls.FN_RESULT]):
                    e = cls.tool_not_found(agent_message=agent_message,error="如果你想调用某个工具，请确保格式正确。")
                    raise e
                response = re.sub(f"<{thinking_tag}>.*?</{thinking_tag}>","",output['content'],flags=re.DOTALL).strip()
                response = response.replace(f'<{cls.fix_reply_tag}>',"").replace(f'</{cls.fix_reply_tag}>',"").replace(f"</{thinking_tag}>","").strip()
                tool_call = {"name":"give_final_response","kwargs":{"response":response},"model_id":cls.model_id}

            return {
                "agent_message": agent_message,
                "tool_calls": [tool_call]
            }
        except (ToolNotExistError, ToolParameterNotExistError, MultipleToolNameError) as e:
            e.agent_message = agent_message
            e.error_message = format_tool_call_results(
                    model_id = agent_output['current_agent_model_id'],
                    tool_output=[{
                        "output":{
                            "code": 1,
                            "result": e.to_agent(),
                            "tool_name": e.tool_name}
                        }]
                )['tool_message']
            raise e 
        

class Qwen2Instruct72BToolCallingParse(Qwen2Instruct7BToolCallingParse):
    model_id = LLMModelType.QWEN2INSTRUCT72B


parse_tool_calling = ToolCallingParse.parse_tool



        






