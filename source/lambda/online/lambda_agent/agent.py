from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)


from common_utils.logger_utils  import get_logger
from common_utils.langchain_utils import chain_logger
from common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_utils.constant import LLMTaskType
from functions.tools import get_tool_by_name

logger = get_logger("agent")

def tool_calling(state:dict):
    message_id = state.get('message_id',None)
    trace_infos = state.get('trace_infos',[])
    agent_config = state["chatbot_config"]['agent_config']
    tool_defs = [get_tool_by_name(tool_name).tool_def for tool_name in state['current_tools']]
    
    llm_config = {
        "tools": tool_defs,
        "model_kwargs": agent_config.get('model_kwargs',{}),
        "model_id": agent_config['model_id'],
        "fewshot_examples": state['intention_fewshot_examples'],
    }

    tool_calling_chain = RunnableLambda(lambda x: invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**llm_config, "intent_type": LLMTaskType.TOOL_CALLING},
            "llm_input": x
            }
        )
    )

    tool_calling_chain = chain_logger(
        tool_calling_chain,
        "tool_calling",
        message_id=message_id,
        trace_infos=trace_infos
    )

    output:dict = tool_calling_chain.invoke(state)

    return output



@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    output = tool_calling(state)
    return output