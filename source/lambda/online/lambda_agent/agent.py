from langchain.schema.runnable import (
    RunnableLambda
)

from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.langchain_utils import chain_logger
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_logic.common_utils.constant import LLMTaskType
from functions.tools import get_tool_by_name

logger = get_logger("agent")

def tool_calling(state:dict):
    agent_config = state["chatbot_config"]['agent_config']

    tools = state['current_intent_tools'] + state['chatbot_config']['agent_config']['tools']
    tool_defs = [get_tool_by_name(tool_name).tool_def for tool_name in tools]
    
    other_chain_kwargs = state.get('other_chain_kwargs',{})
    llm_config = {
        **agent_config,
        # "model_kwargs": agent_config.get('model_kwargs',{}),
        # "model_id": agent_config['model_id'],
        **other_chain_kwargs,
        "tools": tool_defs,
        "fewshot_examples": state['intention_fewshot_examples'],
    }

    agent_llm_type = state.get("agent_llm_type",None) or LLMTaskType.TOOL_CALLING

    output = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**llm_config, "intent_type": agent_llm_type},
            "llm_input": state
            }
        )

    return {
        "agent_output": output,
        "current_agent_tools_def": tool_defs,
        "current_agent_model_id": agent_config['model_id']
        }


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    output = tool_calling(state)
    return output