import os
import boto3
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
from common_logic.common_utils.logger_utils import get_logger, llm_messages_print_decorator
from . import Model
from ..model_config import BEDROCK_MODEL_CONFIGS
from langchain_openai import ChatOpenAI
from common_logic.common_utils.constant import LLMModelType


logger = get_logger("brconnector_bedrock_model")


BRCONNECTOR_MODEL_MAP = {
    LLMModelType.CLAUDE_3_5_HAIKU: "claude-3-5-haiku",
    LLMModelType.CLAUDE_3_5_SONNET: "claude-3-5-sonnet",
    LLMModelType.CLAUDE_3_5_SONNET_V2: "claude-3-5-sonnet-v2",
    LLMModelType.NOVA_MICRO: "amazon-nova-micro",
    LLMModelType.NOVA_LITE: "amazon-nova-lite",
    LLMModelType.NOVA_PRO: "amazon-nova-pro",
    LLMModelType.CLAUDE_3_HAIKU: "claude-3-haiku",
    LLMModelType.CLAUDE_3_SONNET: "claude-3-sonnet"
}


class BrconnetorChatOpenAI(ChatOpenAI):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = 'any'
    enable_prefill: bool = True


class BrconnectorBedrockBaseModel(Model):
    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.7, "top_p": 0.9}
    enable_any_tool_choice = False
    any_tool_choice_value = 'any'
    enable_prefill = False
    model_provider = ModelProvider.BRCONNECTOR_BEDROCK

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        base_url = kwargs.get("base_url", None) or os.environ.get(
            "BRCONNECTOR_API_URL", None)
        api_key = kwargs.get('br_api_key', None) or os.environ.get(
            "BR_API_KEY", None)

        assert base_url, ("base_url is required", kwargs)

        return BrconnetorChatOpenAI(
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
            base_url=base_url,
            api_key=api_key,
            model=BRCONNECTOR_MODEL_MAP[cls.model_id],
            **model_kwargs
        )


BrconnectorBedrockBaseModel.create_for_models(BEDROCK_MODEL_CONFIGS)
