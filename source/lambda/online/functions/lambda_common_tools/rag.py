from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.constant import (
    LLMTaskType
)
from common_logic.common_utils.lambda_invoke_utils import send_trace


def _generate_markdown_link(file_path: str) -> str:
    file_name = file_path.split("/")[-1]
    markdown_link = f"[{file_name}]({file_path})"
    return markdown_link


def format_rag_data(data) -> str:
    """
    Formats the given data into a markdown table.

    Args:
        data (list): A list of dictionaries containing 'source', 'score', and 'page_content' keys.

    Returns:
        str: A markdown table string representing the formatted data.
    """
    if data is None or len(data) == 0:
        return ""

    markdown_table = "| Source | Score | RAG Context |\n"
    markdown_table += "|-----|-----|-----|\n"
    for item in data:
        source = _generate_markdown_link(item.get("source", ""))
        score = item.get("score", -1)
        page_content = item.get("page_content", "").replace("\n", "<br>")
        markdown_table += f"| {source} | {score} | {page_content} |\n"

    return markdown_table


def lambda_handler(event_body, context=None):
    state = event_body['state']
    print(event_body)
    context_list = []
    # Add qq match results
    context_list.extend(state['qq_match_results'])
    figure_list = []
    retriever_params = state["chatbot_config"]["private_knowledge_config"]
    retriever_params["query"] = state[retriever_params.get(
        "retriever_config", {}).get("query_key", "query")]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )
    print("RAG debug")
    print(output)

    for doc in output["result"]["docs"]:
        context_list.append(doc["page_content"])
        figure_list = figure_list + doc.get("figure", [])

    # Remove duplicate figures
    unique_set = {tuple(d.items()) for d in figure_list}
    unique_figure_list = [dict(t) for t in unique_set]
    state['extra_response']['figures'] = unique_figure_list

    context_md = format_rag_data(output["result"]["docs"])
    send_trace(
        f"\n\n{context_md}\n\n", enable_trace=state["enable_trace"])

    group_name = state['chatbot_config']['group_name']
    llm_config = state["chatbot_config"]["private_knowledge_config"]['llm_config']
    chatbot_id = state["chatbot_config"]["chatbot_id"]
    task_type = LLMTaskType.RAG
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id=llm_config['model_id'],
        task_type=task_type,
        chatbot_id=chatbot_id
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

    return {"code": 0, "result": output}
