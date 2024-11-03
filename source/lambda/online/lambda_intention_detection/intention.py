import json
import pathlib
import os

from common_logic.common_utils.logger_utils  import get_logger
from common_logic.common_utils.lambda_invoke_utils import chatbot_lambda_call_wrapper,invoke_lambda
from common_logic.langchain_integration.retrievers.retriever import lambda_handler as retrieve_fn

logger = get_logger("intention")
kb_enabled = os.environ["KNOWLEDGE_BASE_ENABLED"].lower() == "true"
kb_type = json.loads(os.environ["KNOWLEDGE_BASE_TYPE"])
intelli_agent_kb_enabled = kb_type.get("intelliAgentKb", {}).get("enabled", False)


def get_intention_results(query:str, intention_config:dict):
    """get intention few shots results according embedding similarity

    Args:
        query (str): input query from human
        intention_config (dict): intention config information

    Returns:
        intent_fewshot_examples (dict): retrieved few shot examples
    """
    event_body = {
        "query": query,
        "type": "qq",
        **intention_config
    }
    # call retriver
    # res:list[dict] = invoke_lambda(
    #     lambda_name="Online_Functions",
    #     lambda_module_path="functions.functions_utils.retriever.retriever",
    #     handler_name="lambda_handler",
    #     event_body=event_body
    # )
    res = retrieve_fn(event_body)

    if not res["result"]["docs"]:
        # add default intention
        current_path = pathlib.Path(__file__).parent.resolve()
        try:
            with open(f"{current_path}/intention_utils/default_intent.jsonl", "r") as json_file:
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
                "score": "n/a",
                "name": answer.get("intent","chat"),
                "intent": answer.get("intent","chat"),
                "kwargs": answer.get("kwargs", {}),
            })       
    else:
        intent_fewshot_examples = []
        for doc in res["result"]["docs"]:
            threshold_score = 0.4
            if "titan-embed-text-v1" in intention_config["retrievers"][0]["target_model"]:
                # Titan v1 threshold is 0.001, Titan v2 threshold is 0.4
                threshold_score = 0.001
            if doc["score"] > threshold_score:
                doc_item = {
                    "query": doc["page_content"],
                    "score": doc["score"],
                    "name": doc["answer"],
                    "intent": doc["answer"],
                    "kwargs": doc.get("kwargs", {}),
                }
                intent_fewshot_examples.append(doc_item)
        
    return intent_fewshot_examples


@chatbot_lambda_call_wrapper
def lambda_handler(state:dict, context=None):
    intention_config = state["chatbot_config"].get("intention_config",{})
    query_key = intention_config.get("retriever_config",{}).get("query_key","query")
    query = state[query_key]

    output:list = get_intention_results(
            query,
            {
                **intention_config,
            }
        )
    return output

