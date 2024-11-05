# unified lambda tool calling
from functions import get_tool_by_name,Tool
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper

@chatbot_lambda_call_wrapper
def lambda_handler(event_body,context=None):
    tool_name = event_body['tool_name']
    state = event_body['state']
    tool:Tool = get_tool_by_name(tool_name,scene=state['chatbot_config']['scene'])
    
    output:dict = invoke_lambda(
            event_body=event_body,
            lambda_name=tool.lambda_name,
            lambda_module_path=tool.lambda_module_path,
            handler_name=tool.handler_name
        )
    return output





    