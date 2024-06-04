# unified lambda tool calling
from functions.tools import get_tool_by_name,Tool
from common_utils.lambda_invoke_utils import invoke_lambda

def lambda_handler(event_body,context=None):
    tool_name = event_body['tool_name']
    kwargs = event_body['kwargs']
    tool:Tool = get_tool_by_name(tool_name)
    output:dict = invoke_lambda(
            event_body=kwargs,
            lambda_name=tool.lambda_name,
            lambda_module_path=tool.lambda_module_path,
            handler_name=tool.handler_name
        )
    return output





    