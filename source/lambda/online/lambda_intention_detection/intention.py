import json
import pathlib
import os
import asyncio
from typing import List
from langchain_core.documents import Document
from shared.utils.logger_utils import get_logger
from shared.utils.lambda_invoke_utils import chatbot_lambda_call_wrapper
from shared.langchain_integration.retrievers import OpensearchHybridQueryQuestionRetriever
from langchain.retrievers.merger_retriever import MergerRetriever
logger = get_logger("intention")
kb_enabled = os.environ["KNOWLEDGE_BASE_ENABLED"].lower() == "true"
kb_type = json.loads(os.environ["KNOWLEDGE_BASE_TYPE"])
intelli_agent_kb_enabled = kb_type.get(
    "intelliAgentKb", {}).get("enabled", False)


def get_intention_results(query: str, intention_config: dict, intent_threshold: float):
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


    intention_retriever = MergerRetriever(retrievers=[
        OpensearchHybridQueryQuestionRetriever.from_config(
        **retriver_config
    ) for retriver_config in intention_config['retrievers']
    ])
    intention_retrievered:List[Document] = asyncio.run(intention_retriever.ainvoke(event_body['query']))
    # res = retrieve_fn(event_body)

    if not intention_retrievered:
        # Return to guide the user to add intentions
        return [], False
    else:
        intent_fewshot_examples = []
        for doc in intention_retrievered:
            # if "titan-embed-text-v1" in intention_config["retrievers"][0]["target_model"]:
            #     # Titan v1 threshold is 0.001, Titan v2 threshold is 0.4
            #     threshold_score = 0.001
            if doc.metadata["score"] > intent_threshold:
                doc_item = {
                    "query": doc.page_content,
                    "score": doc.metadata["score"],
                    "name": doc.metadata["answer"],
                    "intent": doc.metadata["answer"],
                    "kwargs": doc.metadata.get("kwargs", {}),
                }
                intent_fewshot_examples.append(doc_item)
    # if not res["result"]["docs"]:
    #     # Return to guide the user to add intentions
    #     return [], False
    # else:
    #     intent_fewshot_examples = []
    #     for doc in res["result"]["docs"]:
    #         # if "titan-embed-text-v1" in intention_config["retrievers"][0]["target_model"]:
    #         #     # Titan v1 threshold is 0.001, Titan v2 threshold is 0.4
    #         #     threshold_score = 0.001
    #         if doc["score"] > intent_threshold:
    #             doc_item = {
    #                 "query": doc["page_content"],
    #                 "score": doc["score"],
    #                 "name": doc["answer"],
    #                 "intent": doc["answer"],
    #                 "kwargs": doc.get("kwargs", {}),
    #             }
    #             intent_fewshot_examples.append(doc_item)

    return intent_fewshot_examples, True


@chatbot_lambda_call_wrapper
def lambda_handler(state: dict, context=None):
    intention_config = state["chatbot_config"].get("intention_config", {})
    query_key = intention_config.get(
        "retriever_config", {}).get("query_key", "query")
    query = state[query_key]

    output: list = get_intention_results(
        query,
        {
            **intention_config,
        }
    )
    return output
