import json
import os
import time
import uuid
import boto3
import sys
from typing import TypedDict,Annotated

from langgraph.graph import END, StateGraph
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from common_utils.logger_utils  import get_logger
from common_utils.langchain_utils import NestUpdateState,chain_logger
from common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_utils.constant import LLMTaskType
from common_utils.serialization_utils import JSONEncoder


logger = get_logger("query_preprocess")


def conversation_query_rewrite(state:dict):
    state = state['keys']
    message_id = state['message_id']
    trace_infos = state['trace_infos']
    lambda_invoke_mode = state['lambda_invoke_mode']

    chatbot_config = state["chatbot_config"]
    conversation_query_rewrite_config = chatbot_config["query_process_config"][
        "conversation_query_rewrite_config"
    ]
    conversation_query_rewrite_result_key = conversation_query_rewrite_config['result_key']

    cqr_llm_chain = RunnableLambda(lambda x: invoke_lambda(
        lambda_invoke_mode=lambda_invoke_mode,
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**conversation_query_rewrite_config, "intent_type": LLMTaskType.CONVERSATION_SUMMARY_TYPE},
            "llm_input": x
            }
        )
    )

    cqr_llm_chain = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'], RunnableLambda(lambda x:x['query'])),
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


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    # event_body = json.loads(event["body"])
    # state:dict = event_body['state']

    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2,cls=JSONEncoder)}')

    workflow = StateGraph(NestUpdateState)

    workflow.add_node('conversation_query_rewrite',conversation_query_rewrite)
    workflow.set_entry_point('conversation_query_rewrite')
    workflow.set_finish_point('conversation_query_rewrite')

    app = workflow.compile()

    base_state = {
        "message_id":"",
        "trace_infos": []
        }
    
    output = app.invoke({"keys": {**base_state,**state}})
    state.update(output['keys'])
    
    return state 
