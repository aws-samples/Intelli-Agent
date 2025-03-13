import copy
from typing import Any, List, Union

from common_logic.common_utils.chatbot_utils import ChatbotManager
from pydantic import BaseModel, ConfigDict, Field
from shared.constant import (
    ChatbotMode,
    ContextExtendMethod,
    EmbeddingModelType,
    IndexType,
    KBType,
    LLMModelType,
    ModelProvider,
    RerankModelType,
    SceneType,
    Threshold,
)
from shared.utils.logger_utils import get_logger
from shared.utils.python_utils import update_nest_dict
from shared.utils.secret_utils import get_secret_value

logger = get_logger("pydantic_models")


class ForbidBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


# class AllowBaseModel(BaseModel):
class AllowBaseModel(BaseModel):
    class Config:
        extra = "allow"
        use_enum_values = True


##### model config ##############
class ModelConfig(AllowBaseModel):
    provider: ModelProvider
    model_id: Union[EmbeddingModelType, LLMModelType, RerankModelType]
    base_url: Union[str, None] = None
    api_key_arn: Union[str, None] = None
    api_key: Union[str, None] = None
    target_model: Union[str, None] = None
    model_endpoint: Union[str, None] = None
    model_kwargs: dict = Field(default_factory=lambda: {})

    def model_post_init(self, __context: Any) -> None:
        if self.api_key_arn and not self.api_key:
            self.api_key = get_secret_value(self.api_key_arn)


class LLMConfig(ModelConfig):
    provider: ModelProvider = ModelProvider.BEDROCK
    model_id: LLMModelType = LLMModelType.CLAUDE_3_5_HAIKU
    model_kwargs: dict = Field(
        default_factory=lambda: {"temperature": 0.01, "max_tokens": 4096}
    )

    def model_post_init(self, __context: Any) -> None:
        if self.api_key_arn and not self.api_key:
            self.api_key = get_secret_value(self.api_key_arn)


class EmbeddingModelConfig(ModelConfig):
    dimension: Union[int, None] = None
    embedding_dimension: Union[int, None] = None

    def model_post_init(self, __context: Any) -> None:
        if self.embedding_dimension is None:
            assert self.dimension is not None
            self.embedding_dimension = self.dimension


class RerankConfig(ModelConfig):
    pass


# query preprocess config


class QueryRewriteConfig(LLMConfig):
    rewrite_first_message: bool = False


class QueryProcessConfig(ForbidBaseModel):
    conversation_query_rewrite_config: QueryRewriteConfig = Field(
        default_factory=QueryRewriteConfig
    )


####### retriever config  ###########


class HybridSearchConfig(AllowBaseModel):
    bm25_search_context_extend_method: ContextExtendMethod = ContextExtendMethod.WHOLE_DOC
    bm25_search_whole_doc_max_size: int = 100
    bm25_search_chunk_window_size: int = 10
    bm25_search_top_k: int = 5
    bm25_search_threshold:float = Threshold.BM25_SEARCH_THRESHOLD
    enable_bm25_search: bool = True

    vector_search_context_extend_method: ContextExtendMethod = ContextExtendMethod.WHOLE_DOC
    vector_search_chunk_window_size: int = 10
    vector_search_top_k:int = 5 
    vector_search_whole_doc_max_size:int = 100
    vector_search_threshold:float = Threshold.VECTOR_SEARCH_THRESHOLD
    enable_vector_search:bool = True

    rerank_top_k: int = 10


class RetrieverConfigBase(HybridSearchConfig):
    # database: dict = Field(default_factory=dict)
    index_name: str
    index_type: IndexType
    query_key: str = "query"
    vector_field: str = "vector_field"
    source_field: str = "file_path"
    text_field: str = "text"
    kb_type: KBType = KBType.AOS
    embedding_config: Union[EmbeddingModelConfig, None] = None
    rerank_config: Union[RerankConfig, None] = None


class IntentionRetrieverConfig(RetrieverConfigBase):
    index_type: IndexType = IndexType.INTENTION
    vector_field: str = "vector"


class QQMatchRetrieverConfig(RetrieverConfigBase):
    index_type: IndexType = IndexType.QQ
    vector_field: str = "vector_field"


class PrivateKnowledgeRetrieverConfig(RetrieverConfigBase):
    index_type: IndexType = IndexType.QD
    vector_field: str = "vector_field"


class IntentionConfig(ForbidBaseModel):
    retrievers: list[IntentionRetrieverConfig] = Field(default_factory=list)
    intent_threshold: float = Threshold.INTENTION_THRESHOLD
    all_knowledge_in_agent_threshold: float = (
        Threshold.ALL_KNOWLEDGE_IN_AGENT_THRESHOLD
    )


class QQMatchConfig(ForbidBaseModel):
    retrievers: list[QQMatchRetrieverConfig] = Field(default_factory=list)
    # reranks: list[RerankConfig] = Field(default_factory=list)
    qq_match_threshold: float = 0.9
    qq_in_rag_context_threshold: float = Threshold.QQ_IN_RAG_CONTEXT_THRESHOLD


class RagToolConfig(AllowBaseModel):
    retrievers: List[PrivateKnowledgeRetrieverConfig] = Field(
        default_factory=list
    )
    # rerankers: list[RerankConfig] = Field(default_factory=list)
    llm_config: LLMConfig = Field(default_factory=LLMConfig)


class AgentConfig(ForbidBaseModel):
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    tools: list[Union[str, dict]] = Field(default_factory=list)
    only_use_rag_tool: bool = False


class PrivateKnowledgeConfig(RagToolConfig):
    pass


class ChatbotConfig(AllowBaseModel):
    user_id: str = "default_user_id"
    group_name: str = "Admin"
    chatbot_id: str = "admin"
    chatbot_mode: ChatbotMode = ChatbotMode.chat
    use_history: bool = True
    enable_trace: bool = True
    scene: SceneType = SceneType.COMMON
    agent_repeated_call_limit: int = 5
    query_process_config: QueryProcessConfig = Field(
        default_factory=QueryProcessConfig
    )
    intention_config: IntentionConfig = Field(default_factory=IntentionConfig)
    qq_match_config: QQMatchConfig = Field(default_factory=QQMatchConfig)
    agent_config: AgentConfig = Field(default_factory=AgentConfig)
    chat_config: LLMConfig = Field(default_factory=LLMConfig)
    private_knowledge_config: PrivateKnowledgeConfig = Field(
        default_factory=PrivateKnowledgeConfig
    )
    # tools_config: dict[str, Any] = Field(default_factory=dict)

    def update_llm_config(self, new_llm_config: dict):
        """unified update llm config

        Args:
            new_llm_config (dict): _description_
        """

        def _update_llm_config(m):
            if isinstance(m, LLMConfig):
                for k, v in new_llm_config.items():
                    setattr(m, k, copy.deepcopy(v))
                return
            elif isinstance(m, BaseModel):
                for k, v in m:
                    _update_llm_config(v)

        _update_llm_config(self)

    @staticmethod
    def format_index_info(index_info_from_ddb: dict):
        print("index_info_from_ddb", index_info_from_ddb)
        embeddin_config_from_ddb = index_info_from_ddb["modelIds"]["embedding"]
        embedding_config = {
            "provider": embeddin_config_from_ddb["parameter"]["ModelProvider"],
            "model_id": embeddin_config_from_ddb["parameter"]["ModelEndpoint"],
            "base_url": embeddin_config_from_ddb["parameter"].get("BaseUrl"),
            "api_key_arn": embeddin_config_from_ddb["parameter"].get(
                "ApiKeyArn"
            ),
            "api_key": embeddin_config_from_ddb["parameter"].get("ApiKey"),
            "dimension": embeddin_config_from_ddb["parameter"].get(
                "ModelDimension"
            ),
            "target_model": embeddin_config_from_ddb["parameter"].get(
                "TargetModel"
            ),
            "model_endpoint": embeddin_config_from_ddb["parameter"].get(
                "ModelEndpoint"
            ),
        }
        return {
            "index_name": index_info_from_ddb["indexId"],
            "embedding_config": embedding_config,
            # "model_type": index_info_from_ddb["modelIds"]["embedding"]["parameter"][
            #     "ModelType"
            # ],
            # "target_model": index_info_from_ddb["modelIds"]["embedding"]["parameter"][
            #     "ModelName"
            # ],
            "group_name": index_info_from_ddb["groupName"],
            "kb_type": index_info_from_ddb["kbType"],
            "index_type": index_info_from_ddb["indexType"],
        }
        # return {
        #     "index_name": index_info_from_ddb["indexId"],
        #     "embedding_model_endpoint": index_info_from_ddb["modelIds"]["embedding"][
        #         "parameter"
        #     ]["ModelEndpoint"],
        #     "model_type": index_info_from_ddb["modelIds"]["embedding"]["parameter"][
        #         "ModelType"
        #     ],
        #     "target_model": index_info_from_ddb["modelIds"]["embedding"]["parameter"][
        #         "ModelName"
        #     ],
        #     "group_name": index_info_from_ddb["groupName"],
        #     "kb_type": index_info_from_ddb["kbType"],
        #     "index_type": index_info_from_ddb["indexType"],
        # }

    @staticmethod
    def get_index_info(index_infos: dict, index_type: str, index_name: str):
        try:
            index_info = index_infos[index_type][index_name]
            return index_info
        except KeyError:
            valid_index_names = []
            for task_name, infos in index_infos.items():
                for key in infos.keys():
                    valid_index_names.append(f"{task_name}->{key}")
            valid_index_name_str = "\n".join(valid_index_names)
            logger.error(f"valid index_names:\n{valid_index_name_str}")
            raise KeyError(f"key: {index_type}->{index_name} not exits")

    @classmethod
    def get_index_infos_from_ddb(cls, group_name, chatbot_id):
        chatbot_manager = ChatbotManager.from_environ()
        chatbot = chatbot_manager.get_chatbot(group_name, chatbot_id)
        _infos = chatbot.index_ids or {}
        infos = {}
        for index_type, index_info in _infos.items():
            assert IndexType.has_value(index_type), IndexType.all_values()
            info_list = [
                cls.format_index_info(info)
                for info in list(index_info["value"].values())
            ]
            infos[index_type] = {info["index_name"]: info for info in info_list}

        for index_type in IndexType.all_values():
            if index_type not in infos:
                infos[index_type] = {}

        return infos

    def update_retrievers(
        self,
        default_index_names: dict[str, list],
        default_retriever_config: dict[str, dict],
    ):
        index_infos = self.get_index_infos_from_ddb(
            self.group_name, self.chatbot_id
        )
        logger.info(f"index_infos: {index_infos}")
        logger.info(f"default_index_names: {default_index_names}")
        logger.info(f"default_retriever_config: {default_retriever_config}")
        for task_name, index_names in default_index_names.items():
            if task_name == "qq_match":
                index_type = IndexType.QQ
            elif task_name == "intention":
                index_type = IndexType.INTENTION
            elif task_name == "private_knowledge":
                index_type = IndexType.QD
            else:
                raise ValueError(f"Invalid task_name: {task_name}")

            # default to use all index
            if not index_names:
                index_info_list = list(index_infos[index_type].values())
                index_info_list = [
                    {**default_retriever_config[task_name], **index_info}
                    for index_info in index_info_list
                ]
                getattr(self, f"{task_name}_config").retrievers.extend(
                    index_info_list
                )
            else:
                for index_name in index_names:
                    index_info = self.get_index_info(
                        index_infos, index_type, index_name
                    )
                    getattr(self, f"{task_name}_config").retrievers.append(
                        {**default_retriever_config[task_name], **index_info}
                    )

    def model_copy(self, update=None, deep=True):
        update = update or {}
        new_dict = update_nest_dict(copy.deepcopy(self.dict()), update)
        cls = type(self)
        obj = cls(**new_dict)
        return obj
