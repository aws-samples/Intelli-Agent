

from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper,invoke_lambda

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

    if not res['result']['docs']:
        # add default intention
        import json
        import pathlib
        current_path = pathlib.Path(__file__).parent.resolve()
        with open(f'{current_path}/intention_utils/default_intent.jsonl', 'r') as json_file:
            json_list = list(json_file)

        for json_str in json_list:
            intent_result = json.loads(json_str)
            intention_fewshot_examples = [{
                "query": intent_result["question"],
                "score": 'n/a',
                "name": intent_result['answer']['intent'],
                "intent": intent_result['answer']['intent'],
                "kwargs": intent_result['answer'].get('kwargs', {}),
            }]
    else:
        
        intention_fewshot_examples = [{
            "query": doc['page_content'],
            "score": doc['score'],
            "name": doc['answer']['jsonlAnswer']['intent'],
            "intent": doc['answer']['jsonlAnswer']['intent'],
            "kwargs": doc['answer']['jsonlAnswer'].get('kwargs', {}),
            } for doc in res['result']['docs'] if doc['score'] > 0.4
        ]

    return intention_fewshot_examples


