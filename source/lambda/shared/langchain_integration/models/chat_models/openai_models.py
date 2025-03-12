import os
import boto3
from shared.constant import (
    ModelProvider
)
from shared.utils.logger_utils import get_logger
from . import ChatModelBase
from langchain_openai import ChatOpenAI as _ChatOpenAI
from ..model_config import OPENAI_MODEL_CONFIGS

logger = get_logger("openai_models")


class ChatOpenAI(_ChatOpenAI):
    enable_any_tool_choice: bool = True
    any_tool_choice_value: str = 'required'
    enable_prefill: bool = False
    is_reasoning_model: bool = False


class OpenAIBaseModel(ChatModelBase):
    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.7, "top_p": 0.9}
    enable_any_tool_choice: bool = True
    any_tool_choice_value: str = 'required'
    enable_prefill: bool = False
    model_provider = ModelProvider.OPENAI

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        base_url = kwargs.get("base_url", None) or os.environ.get(
            "OPENAI_BASE_URL", None)
        api_key = kwargs.get('openai_api_key', None) or os.environ.get(
            "OPENAI_API_KEY", None)
        return ChatOpenAI(
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
            base_url=base_url,
            api_key=api_key,
            model=cls.model_id,
            is_reasoning_model=cls.is_reasoning_model,
            **model_kwargs
        )


OpenAIBaseModel.create_for_models(OPENAI_MODEL_CONFIGS)

# model_classes = {
#     f"{Model.model_id_to_class_name(model_id)}": OpenAIBaseModel.create_for_model(model_id)
#     for model_id in OPENAI_MODEL_CONFIGS
# }
