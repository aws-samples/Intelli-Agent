import json
import os
import boto3
from shared.constant import (
    ModelProvider
)
from shared.utils.logger_utils import get_logger, llm_messages_print_decorator
from . import ChatModel
from langchain_deepseek import ChatDeepSeek as _ChatDeepSeek
from ..model_config import SILICONFLOW_DEEPSEEK_MODEL_CONFIGS

logger = get_logger("siliconflow_models")

class ChatDeepSeekR1(_ChatDeepSeek):
    enable_any_tool_choice: bool = False
    # any_tool_choice_value: str = 'required'
    enable_prefill: bool = False
    is_reasoning_model: bool = True


class DeepSeekR1BaseModel(ChatModel):
    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.6, "top_p": 0.9}
    enable_any_tool_choice: bool = False
    enable_prefill: bool = False
    model_provider = ModelProvider.SILICONFLOW
    is_reasoning_model: bool = True

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        # TODO: 
        logger.info("deepseek model kwargs")
        logger.info(model_kwargs)
        logger.info(kwargs)
        api_key_json = json.loads(kwargs.get('api_key'))
        for value in api_key_json.values():
            api_key = value
            break
        logger.info(api_key)
        # api_key = kwargs.get('siliconflow_api_key', None) or os.environ.get(
        #     "SILICONFLOW_API_KEY", None)
        return ChatDeepSeekR1(
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
            api_base="https://api.siliconflow.cn/v1",
            api_key=api_key,
            model=cls.model,
            is_reasoning_model=cls.is_reasoning_model,
            **model_kwargs
        )


DeepSeekR1BaseModel.create_for_models(SILICONFLOW_DEEPSEEK_MODEL_CONFIGS)

