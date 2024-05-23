import collections.abc
import copy
import logging
import os

from common_utils.constant import RerankerType


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
        },
        "chat_config":{
            "model_id":llm_model_id
        }

    }
    chatbot_config = update_nest_dict(
        copy.deepcopy(default_chatbot_config),
        chatbot_config
        )

    return chatbot_config



