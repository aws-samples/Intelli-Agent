from common_logic.common_utils.constant import LLMTaskType
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda, send_trace
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb


def general_rag(state):
    context_list = []
    retriever_params = state["chatbot_config"]["private_knowledge_config"]
    retriever_params["query"] = state[
        retriever_params.get("retriever_config", {}).get("query_key", "query")
    ]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )

    for doc in output["result"]["docs"]:
        context_list.append(doc["page_content"])

    return context_list


def specific_item_rag(state):

    item_detail_response = invoke_lambda(
        event_body={
            "query_specific_item": True,
            "item_id": state["chatbot_config"]["goods_id"],
        },
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )

    send_trace(
        f"item_detail_response: {item_detail_response}",
        enable_trace=state["enable_trace"],
    )

    if item_detail_response["result"]:
        item_detail = item_detail_response["result"]
        similar_items_response = invoke_lambda(
            event_body={
                "query_similar_items": True,
                "item_detail": item_detail,
            },
            lambda_name="Online_Functions",
            lambda_module_path="functions.functions_utils.retriever.retriever",
            handler_name="lambda_handler",
        )
        send_trace(
            f"similar_items_response: {similar_items_response}",
            enable_trace=state["enable_trace"],
        )
        item_description = item_detail["text"]
        similar_items_description = "\n\n".join(
            [item["text"] for item in similar_items_response["result"]]
        )
    else:
        item_description = ""
        similar_items_description = ""

    return item_description, similar_items_description


def multiple_items_rag(state):
    multiple_item_details = []
    item_id_list = state["chatbot_config"]["goods_id"].split(",")
    for item_id in item_id_list:
        item_detail_response = invoke_lambda(
            event_body={
                "query_specific_item": True,
                "item_id": item_id,
            },
            lambda_name="Online_Functions",
            lambda_module_path="functions.functions_utils.retriever.retriever",
            handler_name="lambda_handler",
        )
        multiple_item_details.append(item_detail_response["result"])
    multiple_items_description = "\n\n".join(
        [item["text"] for item in multiple_item_details]
    )
    return multiple_items_description


def lambda_handler(event_body, context=None):
    state = event_body["state"]

    group_name = state["chatbot_config"]["group_name"]
    llm_config = state["chatbot_config"]["private_knowledge_config"]["llm_config"]
    task_type = LLMTaskType.RAG
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name, model_id=llm_config["model_id"], task_type=task_type
    )

    if state["chatbot_config"]["goods_id"].strip() != "":
        goods_id_list = state["chatbot_config"]["goods_id"].split(",")
        if len(goods_id_list) > 1:
            multiple_items_description = multiple_items_rag(state)
            prompt_templates_from_ddb["system_prompt"] = (
                prompt_templates_from_ddb["system_prompt"]
                + f"\n The customer is asking about multiple items, the descriptions of the items are: {multiple_items_description}"
            )
        else:
            item_description, similar_items_description = specific_item_rag(state)
            prompt_templates_from_ddb["system_prompt"] = (
                prompt_templates_from_ddb["system_prompt"]
                + f"\n The customer is asking about a specific item, the description of the item is: {item_description}"
                + f"\n For your reference, the descriptions of the similar items are: {similar_items_description}"
            )

    context_list = general_rag(state)

    # # add qq match results
    # context_list.extend(state["qq_match_results"])

    # unused logic about figures
    figure_list = []
    unique_set = {tuple(d.items()) for d in figure_list}
    unique_figure_list = [dict(t) for t in unique_set]
    state["extra_response"]["figures"] = unique_figure_list

    send_trace(
        f"\n\n**rag-contexts:** {context_list}", enable_trace=state["enable_trace"]
    )

    send_trace(
        f"\n\n**prompt_templates_from_ddb:** {prompt_templates_from_ddb}",
        enable_trace=state["enable_trace"],
    )

    output: str = invoke_lambda(
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler",
        event_body={
            "llm_config": {
                **prompt_templates_from_ddb,
                **llm_config,
                "stream": state["stream"],
                "intent_type": task_type,
            },
            "llm_input": {
                "contexts": context_list,
                "query": state["query"],
                "chat_history": state["chat_history"],
            },
        },
    )
    #

    return {"code": 0, "result": output}
