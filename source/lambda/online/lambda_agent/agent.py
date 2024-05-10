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

from utils.constant import Type

from utils.logger_utils  import get_logger
from utils.langchain_utils import NestUpdateState,chain_logger
from utils.lambda_invoke_utils import invoke_with_handler,invoke_with_lambda
from utils.constant import LLMTaskType


logger = get_logger("agent")


def tool_calling(state:dict):
    state = state['keys']
    message_id = state['message_id']
    trace_infos = state['trace_infos']
    config = state["config"]

    tool_calling_config = config['tool_calling_config']

    tool_calling_chain = RunnableLambda(lambda x: invoke_with_lambda(
        lambda_name='xxxxx',
        event_body={
            "llm_config": {**tool_calling_config, "intent_type": LLMTaskType.TOOL_CALLING},
            "llm_input": x
            }
        )
    )

    conversation_summary_chain = chain_logger(
        tool_calling_chain,
        "tool_calling",
        message_id=message_id,
        trace_infos=trace_infos
    )

    state['tool_calling_res'] = conversation_summary_chain.invoke(tool_calling_chain)
    return state 



# @handle_error
def lambda_handler(event, context=None):
    # event_body = json.loads(event["body"])
    # state:dict = event_body['state']

    # logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')
    # workflow = StateGraph(NestUpdateState)

    # workflow.add_node('tool_calling',tool_calling)
    # workflow.set_entry_point('tool_calling')
    # workflow.set_finish_point('tool_calling')

    # app = workflow.compile()
    # output = app.invoke(state)
    # state.update(output)
    event_body = event["body"]
    state:dict = event_body['state']

    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')

    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    state["is_context_enough"] = 'enough context'
    response["body"] = {"state": state}
    
    return response