from common_logic.common_utils.lambda_invoke_utils import invoke_lambda
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.constant import (
    LLMTaskType
)
from common_logic.common_utils.lambda_invoke_utils import send_trace
from typing import Iterable
import logging
logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)

def llm_stream_helper(res:Iterable, state:dict):
    reference_close_flag = False
    reference_str = ""
    all_str = ""
    for r in res:
        all_str += r
        if all_str.endswith("</reference>"):
            reference_str = all_str.split("</reference>")[0]
            state["extra_response"]["references"] = reference_str.split(",")
            reference_close_flag = True
            all_docs = state["extra_response"]["docs"]
            ref_docs = []
            ref_figures = []
            for ref in state['extra_response']['references']:
                try:
                    doc_id = int(ref)
                    ref_docs.append(all_docs[doc_id-1])
                    ref_figures.append(all_docs[doc_id-1].get("figure",[]))
                except:
                    logger.error(f"Invalid reference doc id: {ref} in {all_str}")
            state['extra_response']['ref_docs'] = ref_docs
            state['extra_response']['ref_figures'] = ref_figures
            continue

        if reference_close_flag:
            yield r

def lambda_handler(event_body,context=None):
    state = event_body['state']
    context_list = []
    # add qq match results
    context_list.extend(state['qq_match_results'])
    figure_list = []
    retriever_params = state["chatbot_config"]["private_knowledge_config"]
    retriever_params["query"] = state[retriever_params.get("retriever_config",{}).get("query_key","query")]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Functions",
        lambda_module_path="functions.functions_utils.retriever.retriever",
        handler_name="lambda_handler",
    )
    state['extra_response']['docs'] = output["result"]["docs"]
    for doc in output["result"]["docs"]:
        context_list.append(doc["page_content"])
        figure_list = figure_list + doc.get("figure",[])

    send_trace(f"\n\n**rag-contexts:** {context_list}", enable_trace=state["enable_trace"])
    
    group_name = state['chatbot_config']['group_name']
    llm_config = state["chatbot_config"]["private_knowledge_config"]["llm_config"]
    task_type = LLMTaskType.RAG
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id=llm_config['model_id'],
        task_type=task_type
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
    filtered_output = llm_stream_helper(output, state)
    
    # Remove duplicate figures
    # unique_set = {tuple(d.items()) for d in figure_list}
    # unique_figure_list = [dict(t) for t in unique_set]



    # return {"code":0,"result":output}
    return {"code":0,"result":filtered_output}

