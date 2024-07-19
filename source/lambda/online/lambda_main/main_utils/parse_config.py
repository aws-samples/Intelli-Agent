import collections.abc
import copy
import os
import boto3

from common_logic.common_utils.constant import ChatbotMode,SceneType
from common_logic.common_utils.chatbot_utils import ChatbotManager
chatbot_table_name = os.environ.get("CHATBOT_TABLE_NAME", "")
model_table_name = os.environ.get("MODEL_TABLE_NAME", "")
index_table_name = os.environ.get("INDEX_TABLE_NAME", "")
dynamodb = boto3.resource("dynamodb")
chatbot_table = dynamodb.Table(chatbot_table_name)
model_table = dynamodb.Table(model_table_name)
index_table = dynamodb.Table(index_table_name)
chatbot_manager = ChatbotManager(chatbot_table, index_table, model_table)

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
    default_index_names = {"intention":[], "private_knowledge":[], "qq_match":[]}
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
                "retriever_config":{
                    "top_k": 10,
                    "query_key": "query"
                },
                "retrievers": default_index_config.get("intention",[])
            },
            "qq_match_config": {
                "retriever_config": {
                    "top_k": 10,
                    "query_key": "query",
                    "threshold": 0.9,
                },
                "retrievers": default_index_config.get("qq_match",[])
            },
            "agent_config": {**copy.deepcopy(default_llm_config), "tools": [], "only_use_rag_tool": False},
            "chat_config": {
                **copy.deepcopy(default_llm_config),
            },
            "private_knowledge_config": {
                "retriever_config": {
                    "retriever_config":{
                            "top_k": 10,
                            "context_num": 1,
                            "using_whole_doc": False,
                            "query_key": "query"
                    },
                    "retrievers": default_index_config.get("private_knowledge",[]),
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
    def parse_aos_indexs(cls,chatbot_config,default_index_names):
        group_name = chatbot_config['group_name']
        chatbot_id = chatbot_config['chatbot_id']
        chatbot = chatbot_manager.get_chatbot(group_name, chatbot_id)
        index_infos = {}
        for task_name,index_info in chatbot.index_ids.items():
            # TODO some modify needed
            assert task_name in ("qq","qd",'intention'),task_name
            # prepare list value
            if task_name == "qq":
                task_name = 'qq_match'
            elif task_name == "qd":
                task_name = "private_knowledge"
            elif task_name == "intention":
                task_name = "intention"
            all_index_names = list(index_info['value'].values())
            allow_index_names = default_index_names[task_name]
            if allow_index_names:
                all_index_names = [index for index in all_index_names if index['indexId'] in allow_index_names]
            index_infos[task_name] = all_index_names
        return index_infos


    @classmethod
    def index_postprocess(cls,chatbot_config):
        def _dict_update(config):
            retrievers = []
            _retrievers = config.pop('retrievers')
            for retriever_dict in _retrievers:
                retrievers.append({
                    **config['retriever_config'],
                    **retriever_dict
                })
            config['retrievers'] = retrievers
        # intention 
        intention_config = chatbot_config['intention_config']
        _dict_update(intention_config)
        # qq_match 
        qq_match_config = chatbot_config['qq_match_config']
        _dict_update(qq_match_config)
        # private knowledge 
        private_knowledge_config = chatbot_config['private_knowledge_config']['retriever_config']
        _dict_update(private_knowledge_config)
    

    @classmethod
    def from_chatbot_config(cls,chatbot_config:dict):
        chatbot_config = copy.deepcopy(chatbot_config)
        default_llm_config = eval(
            os.environ.get("default_llm_config", cls.default_llm_config_str)
        )
        default_llm_config = update_nest_dict(
            copy.deepcopy(default_llm_config),
            chatbot_config.get("default_llm_config", {})
        )

        default_index_names = update_nest_dict(
            copy.deepcopy(cls.default_index_names),
            chatbot_config.get('default_index_names',{})
        )

        default_index_config = cls.parse_aos_indexs(chatbot_config,default_index_names)

        default_index_config = {
            **default_index_config,
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
        # deal with index params
        cls.index_postprocess(chatbot_config)
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
