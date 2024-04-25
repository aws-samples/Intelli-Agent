import collections.abc
import copy
import logging
import os
import json 

from .constant import (
    AWS_TRANSLATE_SERVICE_MODEL_ID, 
    IntentType, 
    RerankerType,
    MKTUserType,
    HistoryType
)


# update nest dict
def update_nest_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d



def parse_sagemind_llm_config(event_body):
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
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
        }
    }

    new_event_config = update_nest_dict(copy.deepcopy(default_config), event_body)
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


def parse_mkt_entry_knowledge_config(event_body:dict):
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

    assert llm_model_id, llm_model_id

    mkt_default_config = {
        # retriver config
        # query process config
        "retriever_config": {
            "qq_config": {
                "qq_match_threshold": 0.8,
                "retriever_top_k": 5,
                "query_key": "query",
                "enable_debug": False
            },
            "qd_config": {
                "retriever_top_k": 5,
                "context_num": 2,
                "using_whole_doc": False,
                "reranker_top_k": 10,
                # "reranker_type": RerankerType.BYPASS.value,
                "reranker_type": RerankerType.BGE_RERANKER.value,
                # "reranker_type": RerankerType.BGE_M3_RERANKER.value,
                "qd_match_threshold": 2,
                "enable_debug": False,
                "query_key": "query_for_qd_retrieve"
                # "enable_reranker":True
            },
            "workspace_ids": [
                "aos_index_mkt_faq_qd_m3",
                "aos_index_acts_qd_m3",
                "aos_index_mkt_faq_qq_m3_20240410",
                "aos_index_dgr_faq_qq_m3_20240410",
                "aos_index_global_site_cn_qd_m3_dense_20240320",
                "aws-cn-dgr-user-guide-qd-m3-dense-20240318",
                "aos_index_cn_docs_qd_m3"
            ],
            "event_workspace_ids": ["event-qd-index-20240313"],
        
        },
        "query_process_config": {
            "query_length_threshold": 1,
            "query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "conversation_query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
                "result_key": "conversation_query_rewrite",
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
            # based on llm 
            "llm_config":{
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name
            },
            # based on aos
            "aos_config":{
                "endpoint_name": os.environ.get('intent_recognition_embedding_endpoint',None),
                "endpoint_target_model": os.environ.get('intent_embedding_endpoint_target_model',None)
            }
        },
        # generator config
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "context_num": 1,
        },
        "use_history": True,
        "history_type": HistoryType.MESSAGE,
        "user_type": MKTUserType.ASSISTANT,
        "response_config": {
            # context return with chunk
            "context_return_with_chunk": False
        }
    }

    new_event_config = update_nest_dict(copy.deepcopy(mkt_default_config), event_body)

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config


def parse_main_entry_config(event_body):
    event_body = copy.deepcopy(event_body)

    llm_model_id = os.environ.get("llm_model_id", "anthropic.claude-v2:1")
    llm_model_endpoint_name = os.environ.get("llm_model_endpoint_name")
    region = os.environ.get("AWS_REGION")

    is_cn_region = "cn" in region

    # TODO modify rag_config
    llm_model_id = event_body.get("llm_model_id", llm_model_id)
    llm_model_endpoint_name = event_body.get(
        "llm_model_endpoint_name", llm_model_endpoint_name
    )

    assert llm_model_id, llm_model_id

    mkt_default_config = {
        # retriver config
        # query process config
        "retriever_config": {
            "qd_config": {
                "retriever_top_k": 5,
                "context_num": 2,
                "using_whole_doc": False,
                "reranker_top_k": 10,
                # "reranker_type": RerankerType.BYPASS.value,
                "reranker_type": RerankerType.BGE_RERANKER.value,
                # "reranker_type": RerankerType.BGE_M3_RERANKER.value,
                "qd_match_threshold": 2,
                "query_key": "query",
                # "enable_reranker":True
            },
            "workspace_ids": [
                "aos_index_mkt_faq_qq_m3",
                "aos_index_acts_qd_m3",
                "aos_index_mkt_faq_qd_m3",
                "aos_index_repost_qq_m3",
            ],
            "event_workspace_ids": ["event-qd-index-20240313"],
        },
        # generator config
        "generator_llm_config": {
            "model_id": llm_model_id,
            "endpoint_name": llm_model_endpoint_name,
            "context_num": 1,
        },
        "use_history": False,
    }

    new_event_config = update_nest_dict(copy.deepcopy(mkt_default_config), event_body)

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config

def parse_text2sql_entry_config(event_body):
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

    assert llm_model_id, llm_model_id

    default_config = {
        # retriver config
        # query process config
        "retriever_config": {
            "qq_config": {
                "qq_match_threshold": 0.8,
                "retriever_top_k": 5,
                "query_key": "query",
            },
            "qd_config": {
                "retriever_top_k": 5,
                "context_num": 2,
                "using_whole_doc": False,
                "reranker_top_k": 10,
                # "reranker_type": RerankerType.BYPASS.value,
                "reranker_type": RerankerType.BGE_RERANKER.value,
                # "reranker_type": RerankerType.BGE_M3_RERANKER.value,
                "qd_match_threshold": 2,
                "query_key": "conversation_query_rewrite",
                # "enable_reranker":True
            },
            "workspace_ids": ["txt2sql"],
            # "workspace_ids": [],
            "event_workspace_ids": ["txt2sql"],
            # "event_workspace_ids": ["event-qd-index-20240313"],
            # "retriever_top_k": 5,
            # "chunk_num": 2,
            # "using_whole_doc": False,
            # "reranker_top_k": 10,
            # "reranker_type": True,
            # "q_q_match_threshold": 0.9,
            # "qd_match_threshold": -1
        },
        "query_process_config": {
            "query_length_threshold": 3,
            "query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
            },
            "conversation_query_rewrite_config": {
                "model_id": llm_model_id,
                "endpoint_name": llm_model_endpoint_name,
                "result_key": "conversation_query_rewrite",
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
            "llm_max_try_num": 3,
        },
        "use_history": False,
    }

    new_event_config = update_nest_dict(copy.deepcopy(default_config), event_body)

    intent = event_body.get("intent", None) or event_body.get("model", None)
    if intent:
        new_event_config["intent_config"]["intent_type"] = intent

    return new_event_config