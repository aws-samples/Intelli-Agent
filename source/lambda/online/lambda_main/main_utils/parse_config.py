import collections.abc
import copy
import logging
import os

from common_utils.constant import ChatbotMode, RerankerType


# update nest dict
def update_nest_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def parse_common_entry_config(chatbot_config):
    chatbot_config = copy.deepcopy(chatbot_config)
    default_llm_config_str = "{'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'model_kwargs': {'temperature': 0.0, 'max_tokens': 4096}}"
    # get default_llm_kwargs from env
    default_llm_config = eval(
        os.environ.get("default_llm_config", default_llm_config_str)
    )

    default_llm_config = {
        **default_llm_config,
        **chatbot_config.get("default_llm_config", {}),
    }

    default_workspace_config = {"intent_workspace_ids": [], "rag_workspace_ids": []}

    default_workspace_config = {
        **default_workspace_config,
        **chatbot_config.get("default_workspace_config", {}),
    }

    assert ChatbotMode.has_value(chatbot_config["chatbot_mode"]), chatbot_config[
        "chatbot_mode"
    ]

    default_chatbot_config = {
        "chatbot_mode": ChatbotMode.chat,
        "use_history": True,
        "query_process_config": {
            "conversation_query_rewrite_config": {**default_llm_config}
        },
        "intention_config": {
            "retrievers": [
                {
                    "type": "qq",
                    "workspace_ids": default_workspace_config["intent_workspace_ids"],
                    "config": {
                        "top_k": 10,
                    },
                },
            ]
        },
        "agent_config": {**default_llm_config, "tools": []},
        "tool_execute_config": {
            "knowledge_base_retriever": {
                "retrievers": [
                    {
                        "type": "qd",
                        "workspace_ids": [1],
                        "top_k": 10,
                    }
                ]
            }
        },
        "chat_config": {
            **default_llm_config,
        },
        "rag_config": {
            "retriever_config": {
                "retrievers": [
                    {
                        "type": "qd",
                        "workspace_ids": default_workspace_config["rag_workspace_ids"],
                        "config": {
                            "top_k": 5,
                            "using_whole_doc": False,
                        },
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz",
                        },
                    }
                ],
            },
            "llm_config": {
                **default_llm_config,
            },
        },
    }
    chatbot_config = update_nest_dict(
        copy.deepcopy(default_chatbot_config), chatbot_config
    )

    # add default tools
    tools: list = chatbot_config["agent_config"]["tools"]
    if "give_rhetorical_question" not in tools:
        tools.append("give_rhetorical_question")

    if "give_final_response" not in tools:
        tools.append("give_final_response")

    return chatbot_config


def parse_retail_entry_config(chatbot_config):
    chatbot_config = copy.deepcopy(chatbot_config)
    default_llm_config_str = "{'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'model_kwargs': {'temperature': 0.1, 'max_tokens': 4096}}"
    # get default_llm_kwargs from env
    default_llm_config = eval(
        os.environ.get("default_llm_config", default_llm_config_str)
    )

    default_llm_config = {
        **default_llm_config,
        **chatbot_config.get("default_llm_config", {}),
    }

    assert ChatbotMode.has_value(chatbot_config["chatbot_mode"]), chatbot_config[
        "chatbot_mode"
    ]

    default_chatbot_config = {
        "chatbot_mode": ChatbotMode.chat,
        "use_history": True,
        "query_process_config": {
            "conversation_query_rewrite_config": {**default_llm_config}
        },
        "intention_config": {
            "retrievers": [
                {
                    "type": "qq",
                    "workspace_ids": ["retail-intent-1"],
                    "config": {
                        "top_k": 10,
                    }
                },
            ]
        },
        "agent_config": {**default_llm_config, "tools": []},
        "tool_execute_config": {
            "knowledge_base_retriever": {
                "retrievers": [
                    {
                        "type": "qd",
                        "workspace_ids": [1],
                        "top_k": 10,
                    }
                ]
            }
        },
        "chat_config": {
            **default_llm_config,
        },
        "rag_goods_exchange_config": {
            "retriever_config": {
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ["retail-quick-reply"],
                        "config": {
                            "top_k": 5
                        },
                    },
                ]
            },
            "llm_config": {
                **default_llm_config,
            },
        },
        "rag_daily_reception_config": {
            "retriever_config": {
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ["retail-quick-reply"],
                        "config": {
                            "top_k": 5
                        },
                    },
                ]
            },
            "llm_config": {
                **default_llm_config,
            },
        },
        "rag_product_aftersales_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu'],
                        "config": {
                            "top_k": 2,
                        }
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz"
                        }
                    }
                ],
            },
            "llm_config":{
                **default_llm_config,
            }
        },
        "rag_customer_complain_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
                        "config": {
                            "top_k": 2,
                        }
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz"
                        }
                    }
                ],
            },
            "llm_config":{
                **default_llm_config,
            }
        },
        "rag_promotion_config": {
            "retriever_config":{
                "retrievers": [
                    {
                        "type": "qq",
                        "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
                        "config": {
                            "top_k": 2,
                        }
                    },
                ],
                "rerankers": [
                    {
                        "type": "reranker",
                        "config": {
                            "enable_debug": False,
                            "target_model": "bge_reranker_model.tar.gz"
                        }
                    }
                ],
            },
            "llm_config":{
                **default_llm_config,
            }
        },
    }
    chatbot_config = update_nest_dict(
        copy.deepcopy(default_chatbot_config), chatbot_config
    )

    # add default tools
    tools: list = chatbot_config["agent_config"]["tools"]
    if "give_rhetorical_question" not in tools:
        tools.append("give_rhetorical_question")

    if "give_final_response" not in tools:
        tools.append("give_final_response")

    return chatbot_config
