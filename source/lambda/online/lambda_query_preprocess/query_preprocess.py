import json
import os
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

from utils.logger_utils  import get_logger
from utils.langchain_utils import NestUpdateState,chain_logger
from utils.lambda_invoke_utils import invoke_with_handler,invoke_with_lambda
from utils.constant import LLMTaskType

logger = get_logger("query_preprocess")

def conversation_query_rewrite(state:dict):
    state = state['keys']
    message_id = state['message_id']
    trace_infos = state['trace_infos']

    config = state["config"]
    conversation_query_rewrite_config = config["query_process_config"][
        "conversation_query_rewrite_config"
    ]
    conversation_query_rewrite_result_key = conversation_query_rewrite_config['result_key']

    cqr_llm_chain = RunnableLambda(lambda x: invoke_with_lambda(
        lambda_name='xxxxx',
        event_body={
            "llm_config": {**conversation_query_rewrite_config, "intent_type": LLMTaskType.CONVERSATION_SUMMARY_TYPE},
            "llm_input": x
            }
        )
    )

    cqr_llm_chain = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'],RunnableLambda(lambda x:x['query'])),
        cqr_llm_chain
    )

    conversation_summary_chain = chain_logger(
        RunnablePassthrough.assign(
            **{conversation_query_rewrite_result_key:cqr_llm_chain}
            # query=cqr_llm_chain
        ),
        "conversation_summary_chain",
        log_output_template=f'conversation_summary_chain result:<conversation_summary> {"{"+conversation_query_rewrite_result_key+"}"}</conversation_summary>',
        message_id=message_id,
        trace_infos=trace_infos
    )

    _state = conversation_summary_chain.invoke(state)
    state.update(**_state)


# @handle_error
def lambda_handler(event, context=None):
    event_body = json.loads(event["body"])
    state:dict = event_body['state']

    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')

    workflow = StateGraph(NestUpdateState)

    workflow.add_node('conversation_query_rewrite',conversation_query_rewrite)
    workflow.set_entry_point('conversation_query_rewrite')
    workflow.set_finish_point('conversation_query_rewrite')

    app = workflow.compile()
    output = app.invoke(state)
    state.update(output)
    
    return state