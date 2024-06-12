from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda
)

from common_utils.logger_utils  import get_logger
from common_utils.langchain_utils import chain_logger
from common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_utils.constant import LLMTaskType

logger = get_logger("query_preprocess")


def conversation_query_rewrite(state:dict):
    message_id = state.get('message_id',"")
    trace_infos = state.get('trace_infos',[])

    chatbot_config = state["chatbot_config"]
    conversation_query_rewrite_config = chatbot_config["query_process_config"][
        "conversation_query_rewrite_config"
    ]

    query_rewrite_llm_type = state.get("query_rewrite_llm_type",None) or LLMTaskType.CONVERSATION_SUMMARY_TYPE

    cqr_llm_chain = RunnableLambda(lambda x: invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**conversation_query_rewrite_config, "intent_type": query_rewrite_llm_type},
            "llm_input": {"chat_history":state['chat_history'], "query":state['query']}
            }
        )
    )

    cqr_llm_chain = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'], RunnableLambda(lambda x:x['query'])),
        cqr_llm_chain
    )

    conversation_summary_chain = chain_logger(
         cqr_llm_chain
            # query=cqr_llm_chain
        ,
        "conversation_summary_chain",
        # log_output_template='conversation_summary_chain result:<conversation_summary> {outputs}</conversation_summary>',
        message_id=message_id,
        trace_infos=trace_infos
    )

    output = conversation_summary_chain.invoke(state)
    return output
    
@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    output:dict = conversation_query_rewrite(state)
    return output
