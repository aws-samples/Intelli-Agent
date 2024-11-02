from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,StateContext
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.constant import (
    LLMTaskType
)
from common_logic.common_utils.lambda_invoke_utils import send_trace


def rag_tool(retriever_config:dict,query=None):
    state = StateContext.get_current_state()
    # state = event_body['state']
    context_list = []
    # add qq match results
    context_list.extend(state['qq_match_results'])
    figure_list = []
    retriever_params = retriever_config
    # retriever_params = state["chatbot_config"]["private_knowledge_config"]
    retriever_params["query"] = query or state[retriever_config.get("query_key","query")]
    # retriever_params["query"] = query
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )

    for doc in output["result"]["docs"]:
        context_list.append(doc["page_content"])
        figure_list = figure_list + doc.get("figure",[])
    
    # Remove duplicate figures
    unique_set = {tuple(d.items()) for d in figure_list}
    unique_figure_list = [dict(t) for t in unique_set]
    state['extra_response']['figures'] = unique_figure_list
    
    send_trace(f"\n\n**rag-contexts:** {context_list}", enable_trace=state["enable_trace"])
    
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
    return output

