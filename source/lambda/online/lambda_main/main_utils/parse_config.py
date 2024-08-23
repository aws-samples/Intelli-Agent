import copy
import os

from common_logic.common_utils.constant import IndexType
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.pydantic_models import (
    ChatbotConfig,
    LLMConfig,
    PrivateKnowledgeRetrieverConfig,
    RagToolConfig,
)
from common_logic.common_utils.python_utils import update_nest_dict

logger = get_logger("parse_config")


class ConfigParserBase:
    default_llm_config_str = "{'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'model_kwargs': {'temperature': 0.01, 'max_tokens': 4096}}"
    default_index_names = {"intention": [], "private_knowledge": [], "qq_match": []}
    default_retriever_config = {
        "intention": {"top_k": 5, "query_key": "query"},
        "private_knowledge": {
            "top_k": 5,
            "query_key": "query",
            "context_num": 1,
            "using_whole_doc": False,
        },
        "qq_match": {"top_k": 5, "query_key": "query"},
    }

    @classmethod
    def parse_default_llm_config(cls, chatbot_config):
        default_llm_config = eval(
            os.environ.get("default_llm_config", cls.default_llm_config_str)
        )
        default_llm_config = update_nest_dict(
            copy.deepcopy(default_llm_config),
            chatbot_config.pop("default_llm_config", {}),
        )
        return default_llm_config

    @classmethod
    def parse_default_index_names(cls, chatbot_config):
        default_index_names = update_nest_dict(
            copy.deepcopy(cls.default_index_names),
            chatbot_config.pop("default_index_names", {}),
        )
        return default_index_names

    @classmethod
    def parse_default_retriever_config(cls, chatbot_config):
        default_retriever_config = update_nest_dict(
            copy.deepcopy(cls.default_retriever_config),
            chatbot_config.pop("default_retriever_config", {}),
        )
        return default_retriever_config

    @classmethod
    def from_chatbot_config(cls, chatbot_config: dict):
        chatbot_config = copy.deepcopy(chatbot_config)
        default_llm_config = cls.parse_default_llm_config(chatbot_config)
        default_index_names = cls.parse_default_index_names(chatbot_config)
        default_retriever_config = cls.parse_default_retriever_config(chatbot_config)

        group_name = chatbot_config["group_name"]
        chatbot_id = chatbot_config["chatbot_id"]
        user_profile = chatbot_config["user_profile"]

        # init chatbot config
        chatbot_config_obj = ChatbotConfig(
            group_name=group_name, chatbot_id=chatbot_id, user_profile=user_profile
        )
        # init default llm
        chatbot_config_obj.update_llm_config(default_llm_config)

        # init retriever
        chatbot_config_obj.update_retrievers(
            default_index_names, default_retriever_config
        )
        # update chatbot config obj from event body
        new_chatbot_config_obj = chatbot_config_obj.model_copy(
            deep=True, update=chatbot_config
        )
        return new_chatbot_config_obj.dict()


class CommonConfigParser(ConfigParserBase):
    @classmethod
    def from_chatbot_config(cls, chatbot_config: dict):
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
    def from_chatbot_config(cls, chatbot_config: dict):
        # get index_infos
        index_infos = ChatbotConfig.get_index_infos_from_ddb(
            chatbot_config["group_name"], chatbot_config["chatbot_id"]
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
                        index_name="retail-quick-reply",
                    )
                )
            ],
            llm_config=LLMConfig(**default_llm_config),
        )
        default_tools_config["rag_goods_exchange_config"] = rag_goods_exchange_config
        #

        chatbot_config["tools_config"] = default_tools_config
        chatbot_config = super().from_chatbot_config(chatbot_config)
        return chatbot_config
