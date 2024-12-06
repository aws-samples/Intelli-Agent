from common_logic.common_utils.lambda_invoke_utils import StateContext
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.constant import (
    LLMTaskType
)
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.langchain_integration.retrievers.retriever import lambda_handler as retrieve_fn
from common_logic.langchain_integration.chains import LLMChain
from common_logic.common_utils.monitor_utils import format_rag_data
from typing import Iterable
import logging


logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)


# def llm_stream_helper(res: Iterable, state: dict):
#     reference_close_flag = False
#     reference_str = ""
#     all_str = ""
#     for r in res:
#         all_str += r
#         if all_str.endswith("</reference>"):
#             reference_str = all_str.split("</reference>")[0]
#             state["extra_response"]["references"] = reference_str.split(",")
#             reference_close_flag = True
#             all_docs = state["extra_response"]["docs"]
#             ref_docs = []
#             ref_figures = []
#             for ref in state["extra_response"]["references"]:
#                 try:
#                     doc_id = int(ref)
#                     ref_docs.append(all_docs[doc_id-1])
#                     ref_figures.append(all_docs[doc_id-1].get("figure", []))
#                 except Exception as e:
#                     logger.error(
#                         f"Invalid reference doc id: {ref} in {all_str}. Error: {e}")
#             state["extra_response"]["ref_docs"] = ref_docs
#             state["extra_response"]["ref_figures"] = ref_figures
#             continue

#         if reference_close_flag:
#             yield r


def rag_tool(retriever_config: dict, query=None):
    state = StateContext.get_current_state()
    # state = event_body['state']
    context_list = []
    # add qq match results
    context_list.extend(state['qq_match_results'])
    figure_list = []
    retriever_params = retriever_config
    retriever_params["query"] = query or state[retriever_config.get(
        "query_key", "query")]
    output = retrieve_fn(retriever_params)
    state["extra_response"]["docs"] = output["result"]["docs"]

    for doc in output["result"]["docs"]:
        context_list.append(doc["page_content"])
        figure_list = figure_list + doc.get("figure", [])

    # # Remove duplicate figures
    # unique_set = {tuple(d.items()) for d in figure_list}
    # unique_figure_list = [dict(t) for t in unique_set]
    # state['extra_response']['figures'] = unique_figure_list

    context_md = format_rag_data(
        output["result"]["docs"], state.get("qq_match_contexts", {}))
    send_trace(
        f"\n\n{context_md}\n\n", enable_trace=state["enable_trace"])
    # send_trace(
    #     f"\n\n**rag-contexts:**\n\n {context_list}", enable_trace=state["enable_trace"])

    group_name = state["chatbot_config"]["group_name"]
    llm_config = state["chatbot_config"]["private_knowledge_config"]["llm_config"]
    chatbot_id = state["chatbot_config"]["chatbot_id"]
    task_type = LLMTaskType.RAG
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id=llm_config["model_id"],
        task_type=task_type,
        chatbot_id=chatbot_id
    )

    llm_config = {
        **prompt_templates_from_ddb,
        **llm_config,
        "stream": state["stream"],
        "intent_type": task_type,
    }

    llm_input = {
        "contexts": context_list,
        "query": state["query"],
        "chat_history": state["chat_history"]
    }

    chain = LLMChain.get_chain(
        **llm_config
    )
    output = chain.invoke(llm_input)

    # filtered_output = llm_stream_helper(output, state)

    # Remove duplicate figures
    # unique_set = {tuple(d.items()) for d in figure_list}
    # unique_figure_list = [dict(t) for t in unique_set]

    # return filtered_output, filtered_output
    return output, output
