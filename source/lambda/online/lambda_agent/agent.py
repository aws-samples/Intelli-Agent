from langchain.schema.runnable import (
    RunnableLambda
)
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_logic.common_utils.constant import LLMTaskType
from functions import get_tool_by_name

logger = get_logger("agent")

def tool_calling(state:dict):
    agent_config = state["chatbot_config"]['agent_config']
    tools = state['intent_fewshot_tools'] + agent_config['tools']
    tool_defs = [get_tool_by_name(
        tool_name,
        scene=state["chatbot_config"]['scene']).tool_def 
        for tool_name in tools
    ]
    
    other_chain_kwargs = state.get('other_chain_kwargs',{})
    llm_config = {
        **agent_config['llm_config'],
        **other_chain_kwargs,
        "tools": tool_defs,
        "fewshot_examples": state['intent_fewshot_examples'],
    }

    agent_llm_type = state.get("agent_llm_type",None) or LLMTaskType.TOOL_CALLING
    
    group_name = state['chatbot_config']['group_name']
    chatbot_id = state['chatbot_config']['chatbot_id']
     

    # add prompt template from ddb
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id = llm_config['model_id'],
        task_type=agent_llm_type,
        chatbot_id=chatbot_id
    )

    output = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **prompt_templates_from_ddb,
                **llm_config, 
                "intent_type": agent_llm_type
            },
            "llm_input": state
            }
        )

    return {
        "agent_output": output,
        "current_agent_tools_def": tool_defs,
        "current_agent_model_id": agent_config['llm_config']['model_id']
        }


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    output = tool_calling(state)
    return output