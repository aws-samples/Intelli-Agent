

from common_utils.logger_utils  import get_logger
from common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper,invoke_lambda

logger = get_logger("intention")


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    intention_config = state['chatbot_config'].get("intention_config",{})
    query_key = intention_config.get("query_key","query")
    event_body = {
        "query": state[query_key],
        **intention_config
    }
    # call retriver
    res:list[dict] = invoke_lambda(
        lambda_name='Online_Function_Retriever',
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name='lambda_handler',
        event_body=event_body
    )
    
    intention_fewshot_examples = [{
        "query": doc['page_content'],
        "score": doc['score'],
        "name": doc['answer']['jsonlAnswer']['intent'],
        "intent": doc['answer']['jsonlAnswer']['intent'],
        "kwargs": doc['answer']['jsonlAnswer'].get('kwargs', {}),
        } for doc in res['result']['docs'] if doc['score'] > 0.4
    ]

    return intention_fewshot_examples


