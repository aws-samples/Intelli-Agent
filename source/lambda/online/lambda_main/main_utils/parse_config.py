import collections.abc
import copy
import os
import boto3
from pydantic import BaseModel,ConfigDict,Field
from typing import Union,Any

from common_logic.common_utils.constant import ChatbotMode,SceneType,LLMModelType,IndexType
from common_logic.common_utils.chatbot_utils import ChatbotManager
from common_logic.common_utils.logger_utils import get_logger

logger = get_logger("parse_config")

# update nest dict
def update_nest_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nest_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class ForbidBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=()
    )


class AllowBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        protected_namespaces=()
    )


class LLMConfig(AllowBaseModel):
    model_id: LLMModelType = LLMModelType.CLAUDE_3_SONNET
    model_kwargs: dict = {'temperature': 0.01, 'max_tokens': 4096}


class QueryProcessConfig(ForbidBaseModel):
    conversation_query_rewrite_config: LLMConfig = Field(default_factory=LLMConfig)

class RetrieverConfigBase(AllowBaseModel):
    index_type: str

class IntentionRetrieverConfig(RetrieverConfigBase):
    top_k: int = 5
    query_key: str = "query"
    index_name: str 


class QQMatchRetrieverConfig(RetrieverConfigBase):
    top_k: int = 5
    query_key: str = "query"
    index_name: str 


class PrivateKnowledgeRetrieverConfig(RetrieverConfigBase):
    top_k: int = 5
    context_num: int = 1
    using_whole_doc: bool = False 
    query_key: str = "query"
    index_name: str 


class IntentionConfig(ForbidBaseModel):
    retrievers: list[IntentionRetrieverConfig] = Field(default_factory=list)


class RerankConfig(AllowBaseModel):
    endpoint_name: str = None
    target_model: str = None


class QQMatchConfig(ForbidBaseModel):
    retrievers: list[QQMatchRetrieverConfig] = Field(default_factory=list)
    reranks: list[RerankConfig] = Field(default_factory=list)
    threshold: float = 0.9

class RagToolConfig(AllowBaseModel):
    retrievers: list[PrivateKnowledgeRetrieverConfig] = Field(default_factory=list)
    rerankers: list[RerankConfig] = Field(default_factory=list)
    llm_config: LLMConfig = Field(default_factory=LLMConfig)


class AgentConfig(ForbidBaseModel):
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    tools:list[str] = Field(default_factory=list)
    only_use_rag_tool: bool = False


class PrivateKnowledgeConfig(RagToolConfig):
    pass


class ChatbotConfig(ForbidBaseModel):
    user_id: str = "default_user_id"
    group_name: str = "Admin"
    chatbot_id: str = "admin"
    chatbot_mode: ChatbotMode = ChatbotMode.chat
    use_history: bool = True
    enable_trace: bool = True 
    scene: SceneType = SceneType.COMMON
    agent_repeated_call_limit: int = 5
    query_process_config: QueryProcessConfig = Field(default_factory=QueryProcessConfig)
    intention_config: IntentionConfig = Field(default_factory=IntentionConfig)
    qq_match_config: QQMatchConfig = Field(default_factory=QQMatchConfig)
    agent_config: AgentConfig = Field(default_factory=AgentConfig)
    chat_config: LLMConfig = Field(default_factory=LLMConfig)
    private_knowledge_config: PrivateKnowledgeConfig = Field(default_factory=PrivateKnowledgeConfig)
    tools_config: dict[str, Any] = Field(default_factory=dict)

    def update_llm_config(self,new_llm_config:dict):
        """unified update llm config

        Args:
            new_llm_config (dict): _description_
        """
        def _update_llm_config(m):
            if isinstance(m,LLMConfig):
                for k,v in new_llm_config.items():
                    setattr(m,k,copy.deepcopy(v))
                return 
            elif isinstance(m,BaseModel):
                for k,v in m:
                    _update_llm_config(v)
        _update_llm_config(self)
     

    @staticmethod
    def format_index_info(index_info_from_ddb:dict):
        return {
            "index_name": index_info_from_ddb["indexId"],
            "embedding_model_endpoint": index_info_from_ddb['modelIds']['embedding']['parameter']['ModelEndpoint'],
            "target_model": index_info_from_ddb['modelIds']['embedding']['parameter']['ModelName'],
            "group_name": index_info_from_ddb['groupName'],
            "kb_type": index_info_from_ddb['kbType'],
            "index_type": index_info_from_ddb['indexType']
        }
     
    @staticmethod
    def get_index_info(index_infos:dict,index_type:str,index_name:str):
        try:
            index_info = index_infos[index_type][index_name]
            return index_info
        except KeyError:
            valid_index_names = []
            for task_name,infos in index_infos.items():
                for key in infos.keys():
                    valid_index_names.append(f"{task_name}->{key}")
            valid_index_name_str = "\n".join(valid_index_names)
            logger.error(f"valid index_names:\n{valid_index_name_str}")
            raise KeyError(f"key: {index_type}->{index_name} not exits")
    
    @classmethod
    def get_index_infos_from_ddb(cls,group_name,chatbot_id):
        chatbot_manager = ChatbotManager.from_environ()
        chatbot = chatbot_manager.get_chatbot(group_name, chatbot_id)
        _infos = chatbot.index_ids or {}
        infos = {}
        for index_type,index_info in _infos.items():
            assert IndexType.has_value(index_type), IndexType.all_values()
            info_list = [cls.format_index_info(info) for info in list(index_info['value'].values())]
            infos[index_type] = {info['index_name']:info for info in info_list}
        
        for index_type in IndexType.all_values():
            if index_type not in infos:
                infos[index_type] = {}

        return infos
    
    def update_retrievers(
        self,
        default_index_names: dict[str,list],
        default_retriever_config: dict[str,dict]
    ):
        index_infos = self.get_index_infos_from_ddb(self.group_name,self.chatbot_id)
        for task_name,index_names in default_index_names.items():
            assert task_name in ("qq_match","intention","private_knowledge")
            if task_name == "qq_match":
                index_type = IndexType.QQ
            elif task_name == "intention":
                index_type = IndexType.INTENTION
            elif task_name == "private_knowledge":
                index_type = IndexType.QD
            
            # default to use all index
            if not index_names:
                index_info_list = list(index_infos[index_type].values())
                index_info_list = [{
                    **default_retriever_config[task_name],
                    **index_info
                } for index_info in index_info_list]
                getattr(self,f"{task_name}_config").retrievers.extend(index_info_list)
            else:
                for index_name in index_names:     
                    index_info = self.get_index_info(index_infos,index_type,index_name)
                    getattr(self,f"{task_name}_config").retrievers.append(
                        {
                            **default_retriever_config[task_name],
                            **index_info
                        }
                    )
    
    def model_copy(self,update=None,deep=True):
        update = update or {}
        new_dict = update_nest_dict(
            copy.deepcopy(self.model_dump()),
            update
        )
        cls = type(self)
        obj = cls(**new_dict)
        return obj

    
class ConfigParserBase:
    default_llm_config_str = "{'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'model_kwargs': {'temperature': 0.01, 'max_tokens': 4096}}"
    default_index_names = {"intention":[], "private_knowledge":[], "qq_match":[]}
    default_retriever_config = {
        "intention": {
            "top_k":5,
            "query_key": "query"
        },
        "private_knowledge": {
            "top_k":5,
            "query_key": "query",
            "context_num": 1,
            "using_whole_doc": False
        },
        "qq_match": {
            "top_k":5,
            "query_key": "query"
        }
    }
    
    @classmethod
    def parse_default_llm_config(cls,chatbot_config):
        default_llm_config = eval(
            os.environ.get("default_llm_config", cls.default_llm_config_str)
        )
        default_llm_config = update_nest_dict(
            copy.deepcopy(default_llm_config),
            chatbot_config.pop("default_llm_config", {})
        )
        return default_llm_config

    @classmethod
    def parse_default_index_names(cls,chatbot_config):
        default_index_names = update_nest_dict(
            copy.deepcopy(cls.default_index_names),
            chatbot_config.pop('default_index_names',{})
        )
        return default_index_names
    
    @classmethod
    def parse_default_retriever_config(cls,chatbot_config):
        default_retriever_config = update_nest_dict(
            copy.deepcopy(cls.default_retriever_config),
            chatbot_config.pop("default_retriever_config", {})
        )
        return default_retriever_config

    
    @classmethod
    def from_chatbot_config(cls,chatbot_config:dict):
        chatbot_config = copy.deepcopy(chatbot_config)
        default_llm_config = cls.parse_default_llm_config(chatbot_config)
        default_index_names = cls.parse_default_index_names(chatbot_config)
        default_retriever_config = cls.parse_default_retriever_config(chatbot_config)

        group_name = chatbot_config['group_name']
        chatbot_id = chatbot_config['chatbot_id']
        
        # init chatbot config
        chatbot_config_obj = ChatbotConfig(
            group_name=group_name,
            chatbot_id=chatbot_id
        )
        # init default llm
        chatbot_config_obj.update_llm_config(default_llm_config)

        # init retriever
        chatbot_config_obj.update_retrievers(
            default_index_names,
            default_retriever_config
        )
        # update chatbot config obj from event body
        new_chatbot_config_obj = chatbot_config_obj.model_copy(
            deep=True,update=chatbot_config
        )
        return new_chatbot_config_obj.model_dump()


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
    def from_chatbot_config(cls,chatbot_config:dict):
        # get index_infos
        index_infos = ChatbotConfig.get_index_infos_from_ddb(
            chatbot_config['group_name'],
            chatbot_config['chatbot_id']
        )
        default_llm_config = cls.parse_default_llm_config(chatbot_config)
        # add retail tools
        default_tools_config = {}
        rag_goods_exchange_config = RagToolConfig(
            retrievers=[
                PrivateKnowledgeRetrieverConfig(
                    top_k=5,
                    **ChatbotConfig.get_index_info(
                        index_infos,
                        index_type=IndexType.QQ,
                        index_name="retail-quick-reply"
                    )
                )
            ],
            llm_config=LLMConfig(**default_llm_config)
        )
        default_tools_config['rag_goods_exchange_config'] = rag_goods_exchange_config
        # 

        chatbot_config['tools_config'] = default_tools_config
        chatbot_config = super().from_chatbot_config(chatbot_config)
        return chatbot_config


# class RetailConfigParser(ConfigParserBase):
#     @classmethod
#     def from_chatbot_config(cls,chatbot_config:dict):
#         chatbot_config = super().from_chatbot_config(chatbot_config)
#          # add default tools
#         # tools: list = chatbot_config["agent_config"]["tools"]
#         # if "give_rhetorical_question" not in tools:
#         #     tools.append("give_rhetorical_question")
#         return chatbot_config

#     @classmethod
#     def get_default_chatbot_config(cls, default_llm_config, default_index_config):
#         default_chatbot_config = super().get_default_chatbot_config(default_llm_config, default_index_config)
#         default_chatbot_config['agent_repeated_call_limit'] = 3
#         # default_chatbot_config['intention_config'] = {
#         #     "query_key": "query_rewrite",
#         #     "retrievers": [
#         #         {
#         #             "type": "qq",
#         #             "index_ids": ["retail-intent"],
#         #             "config": {
#         #                 "top_k": 5,
#         #             }
#         #         },
#         #     ]
#         # }
#         return default_chatbot_config

#     @classmethod
#     def parse_aos_indexs(cls,chatbot_config,default_index_names):
#         group_name = chatbot_config['group_name']
#         chatbot_id = chatbot_config['chatbot_id']
#         default_llm_config = chatbot_config['default_llm_config']
#         chatbot = chatbot_manager.get_chatbot(group_name, chatbot_id)
#         index_infos = {}
#         index_id_map = {}
#         for task_name,index_info in chatbot.index_ids.items():
#             # TODO some modify needed
#             assert task_name in ("qq","qd",'intention'),task_name
#             # prepare list value
#             if task_name == "qq":
#                 task_name = 'qq_match'
#             elif task_name == "qd":
#                 task_name = "private_knowledge"
#             elif task_name == "intention":
#                 task_name = "intention"
#             all_index_names = list(index_info['value'].values())
#             allow_index_names = default_index_names[task_name]
#             if allow_index_names:
#                 all_index_names = [index for index in all_index_names if index['indexId'] in allow_index_names]
#             index_infos[task_name] = all_index_names
#         for tool_name,index_info in chatbot.index_ids.items():
#             all_index = list(index_info['value'].values())
#             for index in all_index:
#                 index_id_map[index['indexId']] = index

#         retail_tool_config = {
#             "rag_goods_exchange_config": {
#                 "retriever_config": {
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ["retail-quick-reply"],
#                             "config": {
#                                 "top_k": 5
#                             },
#                         },
#                     ]
#                 },
#                 "llm_config": {
#                     **copy.deepcopy(default_llm_config),
#                 },
#             },
#             "rag_daily_reception_config": {
#                 "retriever_config": {
#                     "top_k": 10,
#                 },
#                 "retrievers": [
#                         index_id_map['retail-quick-reply'],
#                 ],
#                 "llm_config": {
#                     **copy.deepcopy(default_llm_config),
#                 },
#             },
#             "rag_delivery_track_config": {
#                 "retriever_config": {
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ["retail-quick-reply"],
#                             "config": {
#                                 "top_k": 5
#                             },
#                         },
#                     ]
#                 },
#                 "llm_config": {
#                     **copy.deepcopy(default_llm_config),
#                 },
#             },
#             "rag_product_aftersales_config": {
#                 "retriever_config":{
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ['retail-shouhou-wuliu', 'retail-quick-reply'],
#                             "config": {
#                                 "top_k": 5,
#                             }
#                         },
#                     ],
#                     "rerankers": [
#                         {
#                             "type": "reranker",
#                             "config": {
#                                 "enable_debug": False,
#                                 "target_model": "bge_reranker_model.tar.gz"
#                             }
#                         }
#                     ],
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             },
#             "rag_customer_complain_config": {
#                 "retriever_config":{
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
#                             "config": {
#                                 "top_k": 2,
#                             }
#                         },
#                     ],
#                     "rerankers": [
#                         {
#                             "type": "reranker",
#                             "config": {
#                                 "enable_debug": False,
#                                 "target_model": "bge_reranker_model.tar.gz"
#                             }
#                         }
#                     ],
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             },
#             "rag_promotion_config": {
#                 "retriever_config":{
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
#                             "config": {
#                                 "top_k": 2,
#                             }
#                         },
#                     ],
#                     "rerankers": [
#                         {
#                             "type": "reranker",
#                             "config": {
#                                 "enable_debug": False,
#                                 "target_model": "bge_reranker_model.tar.gz"
#                             }
#                         }
#                     ],
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             },
#             "comparison_rag_config": {
#                 "retriever_config": {
#                     "retrievers": [index_id_map['aws-acts-knowledge']]
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             },
#             "step_back_rag_config": {
#                 "retriever_config": {
#                     "retrievers": [index_id_map['aws-acts-knowledge']]
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             },
#             "final_rag_retriever": {
#                 "retriever_config":{
#                     "retrievers": [
#                         {
#                             "type": "qq",
#                             "workspace_ids": ['retail-shouhou-wuliu','retail-quick-reply'],
#                             "config": {
#                                 "top_k": 2,
#                             }
#                         },
#                     ],
#                     "rerankers": [
#                         {
#                             "type": "reranker",
#                             "config": {
#                                 "enable_debug": False,
#                                 "target_model": "bge_reranker_model.tar.gz"
#                             }
#                         }
#                     ],
#                 },
#                 "llm_config":{
#                     **copy.deepcopy(default_llm_config),
#                 }
#             }
#         }
#         chatbot_config.update(retail_tool_config)
#         return index_infos

#     @classmethod
#     def index_postprocess(cls,chatbot_config):
#         def _dict_update(config):
#             retrievers = []
#             _retrievers = config.pop('retrievers')
#             for retriever_dict in _retrievers:
#                 retrievers.append({
#                     **config['retriever_config'],
#                     **retriever_dict
#                 })
#             config['retrievers'] = retrievers
#         # intention 
#         intention_config = chatbot_config['intention_config']
#         _dict_update(intention_config)
#         # qq_match
#         qq_match_config = chatbot_config['qq_match_config']
#         _dict_update(qq_match_config)
#         # private knowledge 
#         private_knowledge_config = chatbot_config['private_knowledge_config']
#         _dict_update(private_knowledge_config)

