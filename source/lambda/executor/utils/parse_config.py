import collections.abc
import copy
import logging
import os

from .constant import AWS_TRANSLATE_SERVICE_MODEL_ID, IntentType, RerankerType


# update nest dict
def update_nest_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


# default rag config
rag_default_config = {
    # retriver config
    # query process config
    "retriever_config": {
        "retriever_top_k": 5,
        "chunk_num": 2,
        "using_whole_doc": False,
        "reranker_top_k": 10,
        "reranker_type": RerankerType.BYPASS.value,
        "q_q_match_threshold": 0.8,
        "workspace_ids": [],
    },
    "query_process_config": {
        "query_rewrite_config": {
            "model_id": "anthropic.claude-instant-v1",
        },
        "conversation_query_rewrite_config": {
            "model_id": "anthropic.claude-instant-v1",
        },
        "hyde_config": {
            "model_id": "anthropic.claude-instant-v1",
        },
        "stepback_config": {
            "model_id": "anthropic.claude-instant-v1",
        },
        "translate_config": {
            # default use Amazon Translate service
            "model_id": AWS_TRANSLATE_SERVICE_MODEL_ID
        },
    },
    # intent_config
    "intent_config": {
        "intent_type": IntentType.KNOWLEDGE_QA.value,
        "model_id": "anthropic.claude-v2:1",
        # "model_kwargs":{"temperature":0,
        #                 "max_tokens_to_sample": 2000,
        #                 "stop_sequences": ["\n\n","\n\nHuman:"]
        #                 },
        "sub_intent": {},
    },
    # generator config
    "generator_llm_config": {
        "model_kwargs": {
            # "max_tokens_to_sample": 2000,
            # "temperature": 0.7,
            # "top_p": 0.9
        },
        "model_id": "anthropic.claude-v2:1",
        "context_num": 2,
    },
    "mkt_conversation_summary_config": {
        "model_id": "anthropic.claude-v2:1",
    },
    "debug_level": logging.INFO,
    "session_id": None,
    "ws_connection_id": None,
    "chat_history": None,
}


def parse_rag_config(event_body):
    event_body = copy.deepcopy(event_body)
    new_event_config = update_nest_dict(copy.deepcopy(rag_default_config), event_body)

    # adapting before setting
    temperature = event_body.get("temperature")
    llm_model_id = event_body.get("llm_model_id")

    if llm_model_id:
        new_event_config["generator_llm_config"]["model_id"] = llm_model_id
    if temperature:
        new_event_config["generator_llm_config"]["model_kwargs"][
            "temperature"
        ] = temperature

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config


def parse_mkt_entry_core_config(event_body):
    return parse_rag_config(event_body)


def parse_market_conversation_summary_entry_config(event_body):
    event_body = copy.deepcopy(event_body)
    llm_model_id = os.environ.get("llm_model_id")
    llm_model_endpoint_name = os.environ.get("llm_model_endpoint_name")
    region = os.environ.get("AWS_REGION")

    is_cn_region = "cn" in region
    llm_model_id = event_body.get("llm_model_id", llm_model_id)
    llm_model_endpoint_name = event_body.get(
        "llm_model_endpoint_name", llm_model_endpoint_name
    )
    assert llm_model_id and llm_model_endpoint_name, (
        llm_model_id,
        llm_model_endpoint_name,
    )
    default_config = {
        "mkt_conversation_summary_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
        }
    }

    new_event_config = update_nest_dict(copy.deepcopy(default_config), event_body)
    return new_event_config


def parse_mkt_entry_config(event_body):
    event_body = copy.deepcopy(event_body)

    llm_model_id = os.environ.get("llm_model_id")
    llm_model_endpoint_name = os.environ.get("llm_model_endpoint_name")
    region = os.environ.get("AWS_REGION")

    is_cn_region = "cn" in region

    # TODO modify rag_config
    llm_model_id = event_body.get("llm_model_id", llm_model_id)
    llm_model_endpoint_name = event_body.get(
        "llm_model_endpoint_name", llm_model_endpoint_name
    )
    assert llm_model_id and llm_model_endpoint_name, (
        llm_model_id,
        llm_model_endpoint_name,
    )

    mkt_default_config = {
        # retriver config
        # query process config
        "retriever_config": {
            "retriever_top_k": 5,
            "chunk_num": 2,
            "using_whole_doc": False,
            "reranker_top_k": 10,
            "reranker_type": RerankerType.BYPASS.value,
            "q_q_match_threshold": 0.9,
            "workspace_ids": ["aos_index_mkt_faq_qq", "aos_index_acts_qd"],
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
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "intent_type": IntentType.KNOWLEDGE_QA.value,
        },
        # generator config
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "context_num": 1,
        },
    }

    new_event_config = update_nest_dict(copy.deepcopy(mkt_default_config), event_body)

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config

def parse_mkt_entry_knowledge_config(event_body):
    event_body = copy.deepcopy(event_body)

    llm_model_id = os.environ.get("llm_model_id")
    llm_model_endpoint_name = os.environ.get("llm_model_endpoint_name")
    region = os.environ.get("AWS_REGION")

    is_cn_region = "cn" in region

    # TODO modify rag_config
    llm_model_id = event_body.get("llm_model_id", llm_model_id)
    llm_model_endpoint_name = event_body.get(
        "llm_model_endpoint_name", llm_model_endpoint_name
    )
    assert llm_model_id and llm_model_endpoint_name, (
        llm_model_id,
        llm_model_endpoint_name,
    )

    mkt_default_config = {
        # retriver config
        # query process config
        "retriever_config":{
            "qq_config": {
                "qq_match_threshold": 0.8,
                "retriever_top_k": 5
            },
            "qd_config":{
                "retriever_top_k": 5,
                "context_num": 2,
                "using_whole_doc": False,
                "reranker_top_k": 10,
                "reranker_type": RerankerType.BYPASS.value,
                "qd_match_threshold": 0.5,
                "enable_reranker":True
            },
            "workspace_ids": ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3"],
            # "retriever_top_k": 5,
            # "chunk_num": 2,
            # "using_whole_doc": False,
            # "reranker_top_k": 10,
            # "reranker_type": True,
            # "q_q_match_threshold": 0.9,
            # "qd_match_threshold": -1
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
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
        },
        # generator config
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "context_num": 1,
        },
    }

    new_event_config = update_nest_dict(copy.deepcopy(mkt_default_config), event_body)

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config
