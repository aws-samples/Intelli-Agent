"""
tool execute format
"""

class FormatMeta(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)

        if name == "FormatToolResult":
            return new_cls
        new_cls.model_map[new_cls.model_id] = new_cls
        return new_cls
    

class FormatToolResult(metaclass=FormatMeta):
    model_map = {}

    @classmethod
    def format(cls,model_id,tool_output:dict):
        target_cls = cls.model_map[model_id]
        return target_cls.format(tool_output)
        

CLAUDE_TOOL_EXECUTE_SUCCESS_TEMPLATE = """
<function_results>
<result>
<tool_name>{tool_name}</tool_name>
<stdout>
{result}
</stdout>
</result>
</function_results>
"""

CLAUDE_TOOL_EXECUTE_FAIL_TEMPLATE = """
<function_results>
<error>
{error}
</error>
</function_results>
"""

MIXTRAL8X7B_TOOL_EXECUTE_SUCCESS_TEMPLATE = """工具: {tool_name} 的执行结果如下:
{result}"""

MIXTRAL8X7B_TOOL_EXECUTE_FAIL_TEMPLATE = """工具: {tool_name} 执行错误，错误如下:
{error}"""

class Claude3SonnetFormatToolResult(FormatToolResult):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    execute_success_template = CLAUDE_TOOL_EXECUTE_SUCCESS_TEMPLATE
    execute_fail_template = CLAUDE_TOOL_EXECUTE_FAIL_TEMPLATE
    
    @classmethod
    def format_one_tool_output(cls,tool_output:dict):
        exe_code = tool_output['code']
        if exe_code == 1:
            # failed
            return cls.execute_fail_template.format(
                error=tool_output['result'],
                tool_name = tool_output['tool_name']
            )
        elif exe_code == 0:
            # succeed
            return cls.execute_success_template.format(
                tool_name=tool_output['tool_name'],
                result=tool_output['result']
            )
        else:
            raise ValueError(f"Invalid tool execute: {tool_output}") 
    
    @classmethod
    def format(cls,tool_call_outputs:list[dict]):
        tool_call_result_strs = []
        for tool_call_result in tool_call_outputs:
            tool_exe_output = tool_call_result['output']
            tool_exe_output['tool_name'] = tool_call_result['name']
            ret:str = cls.format_one_tool_output(
                tool_exe_output
            )
            tool_call_result_strs.append(ret)
        
        ret = "\n".join(tool_call_result_strs)
        return {
            "tool_message": {
                "role":"user",
                "content": ret
            }
        }

class Claude3HaikuFormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


class Claude2FormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-v2"


class Claude21FormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceFormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-instant-v1"


class Mixtral8x7bFormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "mistral.mixtral-8x7b-instruct-v0:1"
    execute_success_template = MIXTRAL8X7B_TOOL_EXECUTE_SUCCESS_TEMPLATE
    execute_fail_template = MIXTRAL8X7B_TOOL_EXECUTE_FAIL_TEMPLATE


class GLM4Chat9BFormatToolResult(FormatToolResult):
    model_id = "glm-4-9b-chat"
    
    @classmethod
    def format(cls,tool_call_outputs:list[dict]):
        tool_call_result_strs = []
        for tool_call_result in tool_call_outputs:
            tool_exe_output = tool_call_result['output']
            tool_call_result_strs.append(str(tool_exe_output['result']))
        # print(tool_exe_output['result'])
        ret = "\n".join(tool_call_result_strs)
        return {
            "tool_message": {
                "role":"observation",
                "content": ret
            }
        }

format_tool_call_results = FormatToolResult.format



        






