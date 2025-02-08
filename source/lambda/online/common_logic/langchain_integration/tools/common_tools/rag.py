from common_logic.common_utils.lambda_invoke_utils import StateContext
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.constant import (
    LLMTaskType,
    Threshold
)
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.langchain_integration.retrievers.retriever import lambda_handler as retrieve_fn
from common_logic.langchain_integration.chains import LLMChain
from common_logic.common_utils.monitor_utils import format_rag_data
from typing import Iterable
import logging


logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)


def filter_response(res: Iterable, state: dict):
    """
    Filter out reference tags from the response and store reference numbers
    Args:
        res: Generator object from LLM response
        state: State dictionary to store references
    Returns:
        Generator yielding filtered response
    """
    buffer = ""
    references = []
    tag_start = "<reference>"
    tag_end = "</reference>"

    for char in res:
        char_strip = char.strip()
        if not buffer and char_strip not in ["<", "<reference"]:
            yield char
            continue

        buffer += char

        # Check the string starts with <reference>
        if buffer == tag_start[:len(buffer)]:
            continue
        elif buffer.startswith(tag_start):
            if buffer.endswith(tag_end):
                # Get reference document number after finding </reference>
                ref_content = buffer[len(tag_start):-len(tag_end)]
                try:
                    ref_num = int(ref_content)
                    references.append(ref_num)
                except ValueError:
                    logger.error(f"Invalid reference number: {ref_content}")
                buffer = ""
            continue
        else:
            # Move next
            yield buffer[0]
            buffer = buffer[1:]

    if buffer:
        yield buffer

    if references:
        state["extra_response"]["references"] = references
        all_docs = state["extra_response"]["docs"]
        ref_docs = []
        ref_figures = []

        for ref in references:
            try:
                doc_id = ref
                ref_docs.append(all_docs[doc_id-1])
                ref_figures.extend(all_docs[doc_id-1].get("figure", []))
            except Exception as e:
                logger.error(f"Invalid reference doc id: {ref}. Error: {e}")

        # Remove duplicate figures
        unique_set = {tuple(d.items()) for d in ref_figures}
        unique_figure_list = [dict(t) for t in unique_set]
        state["extra_response"]["ref_docs"] = ref_docs
        state["extra_response"]["ref_figures"] = unique_figure_list


def rag_tool(retriever_config: dict, query=None):
    state = StateContext.get_current_state()
    context_list = []
    # Add QQ match results
    context_list.extend(state['qq_match_results'])
    figure_list = []
    retriever_params = retriever_config
    retriever_params["query"] = query or state[retriever_config.get(
        "query_key", "query")]
    output = retrieve_fn(retriever_params)
    top_k = retriever_config.get("top_k", Threshold.TOP_K_RETRIEVALS)
    score = retriever_config.get("score", Threshold.ALL_KNOWLEDGE_IN_AGENT_THRESHOLD)
    filtered_docs = [item for item in output["result"]["docs"] if item["score"] >= score]
    sorted_docs = sorted(filtered_docs, key=lambda x: x["score"], reverse=True)
    final_docs = sorted_docs[:top_k]
    state["extra_response"]["docs"] = final_docs

    for doc in final_docs:
        context_list.append(doc["page_content"])
        figure_list = figure_list + doc.get("figure", [])

    context_md = format_rag_data(
        final_docs, state.get("qq_match_contexts", {}))
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

    filtered_output = filter_response(output, state)

    return filtered_output, filtered_output
