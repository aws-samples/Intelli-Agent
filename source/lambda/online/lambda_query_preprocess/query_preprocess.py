from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda
)

from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.langchain_utils import chain_logger
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper,send_trace
from common_logic.common_utils.constant import LLMTaskType
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb

logger = get_logger("query_preprocess")


def conversation_query_rewrite(query:str, chat_history:list, message_id:str, trace_infos:list, chatbot_config:dict, query_rewrite_llm_type:str):
    """rewrite query accoridng to chat history

    Args:
        query (str): input query from human
        chat_history (list): chat history between human and AI
        message_id (str): message id for each converation
        trace_infos (list): record running results in different steps
        chatbot_config (dict): config dict for chatbot
        query_rewrite_llm_type (str): llm type for query rewrite function

    Returns:
        rewrite_query (dict): query rewrite result
    """
    group_name = chatbot_config['group_name']
    conversation_query_rewrite_config = chatbot_config["query_process_config"][
        "conversation_query_rewrite_config"
    ]
    
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id=conversation_query_rewrite_config['model_id'],
        task_type=query_rewrite_llm_type
    )
    logger.info(f'conversation summary prompt templates: {prompt_templates_from_ddb}')

    cqr_llm_chain = RunnableLambda(lambda x: invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {**prompt_templates_from_ddb,
                           **conversation_query_rewrite_config,
                           "intent_type": query_rewrite_llm_type
                    },
            "llm_input": {"chat_history":x['chat_history'], "query":x['query']}
            }
        )
    )

    cqr_llm_chain = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'], RunnableLambda(lambda x:x['query'])),
        cqr_llm_chain
    )

    conversation_summary_chain = chain_logger(
         cqr_llm_chain,
        "conversation_summary_chain",
        message_id=message_id,
        trace_infos=trace_infos
    )
    conversation_summary_input = {}
    conversation_summary_input["chat_history"] = chat_history
    conversation_summary_input["query"] = query
    rewrite_query = conversation_summary_chain.invoke(conversation_summary_input)
    return rewrite_query
    
@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    query = state.get("query","")
    chat_history = state.get("chat_history",[])
    message_id = state.get('message_id',"")
    trace_infos = state.get('trace_infos',[])
    chatbot_config = state["chatbot_config"]
    query_rewrite_llm_type = state.get("query_rewrite_llm_type",None) or LLMTaskType.CONVERSATION_SUMMARY_TYPE
    output:dict = conversation_query_rewrite(query, chat_history, message_id, trace_infos, chatbot_config, query_rewrite_llm_type)
    return output
