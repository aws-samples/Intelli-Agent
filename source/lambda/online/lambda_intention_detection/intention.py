from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper,invoke_lambda
import json
import pathlib

logger = get_logger("intention")

def get_intention_results(query:str, intention_config:dict):
    """get intentino few shots results according embedding similarity

    Args:
        query (str): input query from human
        intention_config (dict): intentino config information

    Returns:
        intent_fewshot_examples (dict): retrieved few shot examples
    """
    event_body = {
        "query": query,
        "type": 'qq',
        **intention_config
    }
    # call retriver
    res:list[dict] = invoke_lambda(
        lambda_name='Online_Functions',
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name='lambda_handler',
        event_body=event_body
    )

    if not res['result']['docs']:
        # add default intention
        current_path = pathlib.Path(__file__).parent.resolve()
        try:
            with open(f'{current_path}/intention_utils/default_intent.jsonl', 'r') as json_file:
                json_list = list(json_file)
        except FileNotFoundError:
            logger.error(f"File note found: {current_path}/intention_utils/default_intent.jsonl")
            json_list = []

        intent_fewshot_examples = []
        for json_str in json_list:
            try:
                intent_result = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}")
                intent_result = {}
            question = intent_result.get("question","你好")
            answer = intent_result.get("answer",{})
            intent_fewshot_examples.append({
                "query": question,
                "score": 'n/a',
                "name": answer.get('intent','chat'),
                "intent": answer.get('intent','chat'),
                "kwargs": answer.get('kwargs', {}),
            })
                
    else:
        intent_fewshot_examples = [{
            "query": doc['page_content'],
            "score": doc['score'],
            "name": doc['answer']['jsonlAnswer']['intent'],
            "intent": doc['answer']['jsonlAnswer']['intent'],
            "kwargs": doc['answer']['jsonlAnswer'].get('kwargs', {}),
            } for doc in res['result']['docs'] if doc['score'] > 0.4
        ]
        
    return intent_fewshot_examples


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    intention_config = state['chatbot_config'].get("intention_config",{})
    query_key = intention_config.get('retriever_config',{}).get("query_key","query")
    query = state[query_key]

    output:list = get_intention_results(
            query,
            {
                **intention_config,
            }
        )

    return output

