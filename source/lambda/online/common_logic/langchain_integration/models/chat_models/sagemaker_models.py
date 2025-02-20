import os

import boto3
from common_logic.common_utils.constant import (
    LLMModelType,
    MessageType,
    ModelProvider,
)
from dmaa.integrations.langchain_clients import (
    SageMakerVllmChatModel as _SageMakerVllmChatModel,
)

from . import Model

session = boto3.Session()
current_region = session.region_name


class SageMakerVllmChatModel(_SageMakerVllmChatModel):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = "any"
    enable_prefill: bool = True


class SageMakerDeepSeekR1DistillLlama(Model):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = "any"
    enable_prefill: bool = True
    default_model_kwargs = {
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    model_provider = ModelProvider.SAGEMAKER

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        print(f"sagemaker model kwargs: {model_kwargs}")
        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = kwargs.get("region_name", None) or current_region

        llm = SageMakerVllmChatModel(
            endpoint_name=kwargs["endpoint_name"],
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
        )
        return llm


class SageMakerDeepSeekR1DistillLlama70B(SageMakerDeepSeekR1DistillLlama):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_70B


class SageMakerDeepSeekR1DistillLlama8B(SageMakerDeepSeekR1DistillLlama):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_8B


class SageMakerDeepSeekR1DistillQwen32B(SageMakerDeepSeekR1DistillLlama):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_QWEN_32B
