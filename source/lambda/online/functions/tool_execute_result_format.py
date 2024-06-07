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

class Claude3SonnetFormatToolResult(FormatToolResult):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    def format(tool_output:dict):
        exe_code = tool_output['code']
        if exe_code == 1:
            # failed
            return CLAUDE_TOOL_EXECUTE_FAIL_TEMPLATE.format(
                error=tool_output['result']
            )
        elif exe_code == 0:
            # succeed
            return CLAUDE_TOOL_EXECUTE_SUCCESS_TEMPLATE.format(
                tool_name=tool_output['tool_name'],
                result=tool_output['result']
            )
        else:
            raise ValueError(f"Invalid tool execute: {tool_output}") 

class Claude3HaikuFormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"


class Claude2FormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-v2"


class Claude21FormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-v2:1"


class ClaudeInstanceFormatToolResult(Claude3SonnetFormatToolResult):
    model_id = "anthropic.claude-instant-v1"


format_tool_execute_result = FormatToolResult.format



        






