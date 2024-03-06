import asyncio
import json 

from .mkt_entry_core import (
    QueryQuestionRetriever,
    get_query_process_chain,
    auto_intention_recoginition_chain,
    get_qd_chain
)
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from ..time_utils import timeit
from ..langchain_utils import chain_logger
from .. import parse_config

def get_strict_qq_chain(strict_q_q_index):
    def get_strict_qq_result(docs, threshold=0.7):
        results = []
        for doc in docs:
            if doc.metadata["score"] < threshold:
                break 
            results.append(
                {
                    "score": doc.metadata["score"],
                    "source": doc.metadata["source"],
                    "answer": doc.metadata["answer"],
                    "question": doc.metadata["question"],
                }
            )
        return results

    
    mkt_q_q_retriever = QueryQuestionRetriever(
        index=strict_q_q_index,
        vector_field="vector_field",
        source_field="file_path",
        size=5,
    )
    strict_q_q_chain = mkt_q_q_retriever | RunnableLambda(get_strict_qq_result)
    return strict_q_q_chain


def main_qq_retriever_entry(
    query_input: str,
    index: str,
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.

    return: answer(str)
    """
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
    full_chain = get_strict_qq_chain(index)
    response = full_chain.invoke({"query": query_input, "debug_info": debug_info})
    return response


@timeit
def main_qd_retriever_entry(
    query_input: str,
    aos_index: str,
    event_body=None,
    manual_input_intent=None
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
    retriever_top_k = rag_config['retriever_config']['retriever_top_k']
    using_whole_doc = rag_config['retriever_config']['using_whole_doc']
    chunk_num = rag_config['retriever_config']['chunk_num']
    query_process_chain = get_query_process_chain(
        rag_config['chat_history'],
        rag_config['query_process_config']['query_rewrite_config'],
        rag_config['query_process_config']['conversation_query_rewrite_config'],
        rag_config['query_process_config']['hyde_config']
    )
    intent_type = rag_config['intent_config']['intent_type']
    intent_info = {
        "manual_input_intent": manual_input_intent,
        "strict_qq_intent_result": {},
    }
    intent_recognition_chain = auto_intention_recoginition_chain("aos_index_mkt_qq")
    intent_recognition_chain = chain_logger(
        intent_recognition_chain,
        'intention module',
        log_output_template='intent chain output: {intent_type}'
        
    )
    qd_chain = get_qd_chain(
        [aos_index], using_whole_doc=using_whole_doc, chunk_num=chunk_num, retriever_top_k=retriever_top_k, reranker_top_k=10
    )
    full_chain = query_process_chain | intent_recognition_chain | qd_chain
    response = asyncio.run(full_chain.ainvoke({
            "query": query_input,
            "debug_info": debug_info,
            "intent_type": intent_type,
            "intent_info": intent_info,
    }))
    doc_list = []
    for doc in response["docs"]:
        doc_list.append({"page_content": doc.page_content, "metadata": doc.metadata})
    return doc_list, debug_info



def get_retriever_response(docs, debug_info):
    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }
    response["body"] = json.dumps({"docs": docs, "debug_info": debug_info})
    response["headers"] = resp_header
    return response