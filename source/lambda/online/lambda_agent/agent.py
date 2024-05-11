import json
import os
import logging
import time
import uuid
import boto3
import sys

from langgraph.graph import END, StateGraph
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from common_utils.constant import Type

from common_utils.logger_utils  import get_logger
from common_utils.langchain_utils import NestUpdateState,chain_logger
from common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_utils.constant import LLMTaskType
from common_utils.serialization_utils import JSONEncoder

logger = get_logger("agent")


def tool_calling(state:dict):
    state = state['keys']
    message_id = state['message_id']
    trace_infos = state['trace_infos']
    agent_config = state["chatbot_config"]['agent_config']

    tool_calling_chain = RunnableLambda(lambda x: invoke_lambda(
        lambda_name='xxxxx',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**agent_config, "intent_type": LLMTaskType.TOOL_CALLING},
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

    output = tool_calling_chain.invoke(state)
    state.update(output)
    return {"keys":state} 



@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):

    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    workflow = StateGraph(NestUpdateState)

    workflow.add_node('tool_calling',tool_calling)
    workflow.set_entry_point('tool_calling')
    workflow.set_finish_point('tool_calling')

    app = workflow.compile()

    base_state = {
        "message_id":"",
        "trace_infos": []
        }
    
    output = app.invoke({"keys": {**base_state,**state}})
    state.update(output)

    # response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    # state["is_context_enough"] = 'enough context'
    # response["body"] = {"state": state}
    
    return state