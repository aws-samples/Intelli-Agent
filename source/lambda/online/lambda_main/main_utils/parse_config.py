import collections.abc
import copy
import os
from common_logic.common_utils.constant import ChatbotMode,SceneType

# update nest dict
def update_nest_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


class ConfigParserBase:
    default_llm_config_str = "{'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'model_kwargs': {'temperature': 0.0, 'max_tokens': 4096}}"
    default_index_config = {"intent_index_ids": ["default-intent"], "rag_index_ids": ["test-pdf"]}
    
    @classmethod
    def get_default_chatbot_config(cls,default_llm_config,default_index_config,**kwargs):
        default_chatbot_config = {
            "chatbot_mode": ChatbotMode.chat,
            "use_history": True,
            "enable_trace": True,
            "scene": SceneType.COMMON,
            "agent_repeated_call_limit": 5,
            "query_process_config": {
                "conversation_query_rewrite_config": {**copy.deepcopy(default_llm_config)}
            },
            "intention_config": {
                "retrievers": [
                    {
                        "type": "qq",
                        "index_ids": default_index_config["intent_index_ids"],
                        "config": {
                            "top_k": 10,
                        },
                    },
                ]
            },
            "agent_config": {**copy.deepcopy(default_llm_config), "tools": []},
            "chat_config": {
                **copy.deepcopy(default_llm_config),
            },
            "rag_config": {
                "retriever_config": {
                    "retrievers": [
                        {
                            "type": "qd",
                            "index_ids": default_index_config["rag_index_ids"],
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
                    **copy.deepcopy(default_llm_config),
                },
            }
        }
        return default_chatbot_config
    
    @classmethod
    def from_chatbot_config(cls,chatbot_config:dict):
        chatbot_config = copy.deepcopy(chatbot_config)
        default_llm_config = eval(
        os.environ.get("default_llm_config", cls.default_llm_config_str)
        )
        default_llm_config = {
        **default_llm_config,
        **chatbot_config.get("default_llm_config", {})
        }
        default_index_config = {
            **cls.default_index_config,
            **chatbot_config.get("default_index_config", {})
        }
        assert ChatbotMode.has_value(chatbot_config["chatbot_mode"]), chatbot_config[
        "chatbot_mode"
        ]
        chatbot_config = update_nest_dict(
            copy.deepcopy(cls.get_default_chatbot_config(
                default_llm_config,
                default_index_config
            )),
            chatbot_config
        )
        return chatbot_config


class CommonConfigParser(ConfigParserBase):
    @classmethod
    def from_chatbot_config(cls,chatbot_config:dict):
        chatbot_config = super().from_chatbot_config(chatbot_config)
         # add default tools
        tools: list = chatbot_config["agent_config"]["tools"]
        if "give_rhetorical_question" not in tools:
            tools.append("give_rhetorical_question")

        if "give_final_response" not in tools:
            tools.append("give_final_response")

        if "get_weather" not in tools:
            tools.append("get_weather")

        return chatbot_config


class RetailConfigParser(ConfigParserBase):
    @classmethod
    def get_default_chatbot_config(cls, default_llm_config, default_index_config):
        default_chatbot_config = super().get_default_chatbot_config(default_llm_config, default_index_config)
        default_chatbot_config['agent_repeated_call_limit'] = 3
        default_chatbot_config['intention_config'] = {
            "query_key": "query_rewrite",
            "retrievers": [
                {
                    "type": "qq",
                    "index_ids": ["retail-intent"],
                    "config": {
                        "top_k": 5,
                    }
                },
            ]
        }
        return default_chatbot_config
