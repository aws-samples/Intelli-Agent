import os
import boto3
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
from common_logic.common_utils.logger_utils import get_logger, llm_messages_print_decorator
from . import Model
from ..model_config import MODEL_CONFIGS
from langchain_openai import ChatOpenAI

logger = get_logger("brconnector_bedrock_model")


class BrconnetorChatOpenAI(ChatOpenAI):
    enable_any_tool_choice: bool = False
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
        base_url = kwargs.get("base_url", None) or os.environ.get("BRCONNECTOR_API_URL", None)

        assert base_url, ("base_url is required",kwargs)

        return BrconnetorChatOpenAI(
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
            base_url=base_url,
            **model_kwargs
        )



model_classes = {
    f"{Model.model_id_to_class_name(model_id)}": BrconnectorBedrockBaseModel.create_for_model(model_id)
    for model_id in MODEL_CONFIGS
}
