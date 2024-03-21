
# from .mkt_entry_core import get_qd_llm_chain   
from  .. import parse_config   

def main_chain_entry(
        query_input: str,
        index: str,
        stream=False,
        event_body=None
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.

    return: answer(str)
    """
    rag_config=parse_config.parse_rag_config(event_body)
    debug_info = {
        "query": query_input,
        "query_parser_info": {},
        "q_q_match_info": {},
        "knowledge_qa_knn_recall": {},
        "knowledge_qa_boolean_recall": {},
        "knowledge_qa_combined_recall": {},
        "knowledge_qa_cross_model_sort": {},
        "knowledge_qa_llm": {},
        "knowledge_qa_rerank": {},
    }
    contexts = []
    sources = []
    answer = ""
    full_chain = get_qd_llm_chain(
        [index], rag_config, stream
    )
    response = full_chain.invoke({"query": query_input, "debug_info": debug_info})
    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]
    return answer, sources, contexts, debug_info