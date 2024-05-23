import collections.abc
import copy
import logging
import os

from common_utils.constant import RerankerType,ChatbotMode


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
    llm_model_id = os.environ.get("llm_model_id", "anthropic.claude-3-sonnet-20240229-v1:0")
    
    llm_model_id = chatbot_config.get("llm_model_id", llm_model_id)

    default_chatbot_config = {
        "chatbot_mode": ChatbotMode.other,
        "query_process_config":{
            "conversation_query_rewrite_config":{
            }

        },
        "intent_recognition_config":{
        },
        "agent_config":{
            "model_id":llm_model_id,
            "model_kwargs": {},
            "tools":[]
        },
        "tool_execute_config":{
            "knowledge_base_retriever":{
                "retrievers": [
                {
                    "type": "qd",
                    "workspace_ids": [1],
                    "top_k": 10,
                }
                ]
            }
        },
        "retriever_config": {
            "retrievers": [
                {
                    "type": "qd",
                    "workspace_ids": [],
                    "config": {
                        "top_k": 20,
                        "using_whole_doc": True,
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
        }
    }
    chatbot_config = update_nest_dict(
        copy.deepcopy(default_chatbot_config),
        chatbot_config
        )

    return chatbot_config