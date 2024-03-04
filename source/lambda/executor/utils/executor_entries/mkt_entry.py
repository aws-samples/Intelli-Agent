import json
import logging
import os

from ..constant import AWS_TRANSLATE_SERVICE_MODEL_ID
from ..serialization_utils import JSONEncoder
from .mkt_entry_core import market_chain_entry as market_chain_entry_core

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def market_chain_entry(
    query_input: str, stream=False, manual_input_intent=None, rag_config=None
):
    # TODO: move this hard code to config
    llm_model_id = os.environ.get("llm_model_id", "internlm2-chat-7b")
    llm_model_endpoint_name = os.environ.get(
        "llm_model_endpoint_name", "instruct-internlm2-chat-7b-f7dc2"
    )
    region = os.environ.get("AWS_REGION")

    is_cn_region = "cn" in region

    # TODO modify rag_config
    llm_model_id = rag_config.get("llm_model_id", llm_model_id)
    llm_model_endpoint_name = rag_config.get(
        "llm_model_endpoint_name", llm_model_endpoint_name
    )
    print(
        f"rag_config:{rag_config}, llm_model_id:{llm_model_id}, llm_model_endpoint_name:{llm_model_endpoint_name}"
    )
    assert llm_model_id and llm_model_endpoint_name, (
        llm_model_id,
        llm_model_endpoint_name,
    )

    rag_new_config = {
        # retriver config
        # query process config
        "retriever_config": {
            "retriever_top_k": 5,
            "chunk_num": 2,
            "using_whole_doc": False,
            "reranker_top_k": 10,
            "enable_reranker": rag_config["retriever_config"]["enable_reranker"],
            "q_q_match_threshold": 0.9,
        },
        "query_process_config": {
            "query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "conversation_query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "hyde_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "stepback_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "translate_config": {
                # default use Amazon Translate service
                "model_id": (
                    llm_model_id if is_cn_region else AWS_TRANSLATE_SERVICE_MODEL_ID
                ),
                "endpoint_name": llm_model_endpoint_name,
            },
        },
        # intent_config
        "intent_config": {
            "intent_type": rag_config["intent_config"]["intent_type"],
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "sub_intent": rag_config["intent_config"]["sub_intent"],
        },
        # generator config
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "context_num": rag_config["generator_llm_config"]["context_num"],
        },
        "mkt_conversation_summary_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
        },
        "debug_level": rag_config["debug_level"],
        "session_id": rag_config["session_id"],
        "ws_connection_id": rag_config["ws_connection_id"],
        "chat_history": rag_config["chat_history"],
    }

    logger.info(
        f"market rag configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}"
    )

    return market_chain_entry_core(
        query_input,
        stream=stream,
        manual_input_intent=manual_input_intent,
        rag_config=rag_new_config,
    )
