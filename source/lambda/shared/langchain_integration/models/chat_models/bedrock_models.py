import os
import boto3
from langchain_aws.chat_models import ChatBedrockConverse as _ChatBedrockConverse
from shared.constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
from shared.utils.logger_utils import (
    get_logger,
    llm_messages_print_decorator
)
from . import (
    ChatModelBase,
    BedrockConverseReasonModelResult,
    BedrockConverseReasonModelStreamResult
)
from ..model_config import (
    BEDROCK_MODEL_CONFIGS
)
from pydantic import Field
from typing import Any

logger = get_logger("bedrock_model")


class ChatBedrockConverse(_ChatBedrockConverse):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = 'any'
    enable_prefill: bool = True
    is_reasoning_model: bool = False
    reason_model_result_cls:Any = BedrockConverseReasonModelResult
    reason_model_result_cls_init_kwargs:dict = Field(default_factory=dict)
    reason_model_stream_result_cls: Any = BedrockConverseReasonModelStreamResult
    reason_model_stream_result_cls_init_kwargs:dict = Field(default_factory=dict)



class BedrockBaseModel(ChatModelBase):
    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.7, "top_p": 0.9}
    # enable_any_tool_choice = False
    # any_tool_choice_value: str = 'any'
    model_provider = ModelProvider.BEDROCK
    is_reasoning_model: bool = False

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = (
            kwargs.get("region_name", None)
            or os.environ.get("BEDROCK_REGION", None)
            or None
        )
        br_aws_access_key_id = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID", "")
        br_aws_secret_access_key = os.environ.get(
            "BEDROCK_AWS_SECRET_ACCESS_KEY", "")

        
        model_name = cls.model or cls.model_id


        if br_aws_access_key_id != "" and br_aws_secret_access_key != "":
            logger.info(
                f"Bedrock Using AWS AKSK from environment variables. Key ID: {br_aws_access_key_id}")

            client = boto3.client("bedrock-runtime", region_name=region_name,
                                  aws_access_key_id=br_aws_access_key_id, aws_secret_access_key=br_aws_secret_access_key)

            llm = ChatBedrockConverse(
                client=client,
                region_name=region_name,
                model=model_name,
                enable_any_tool_choice=cls.enable_any_tool_choice,
                enable_prefill=cls.enable_prefill,
                is_reasoning_model=cls.is_reasoning_model,
                **model_kwargs,
            )
        else:
            llm = ChatBedrockConverse(
                credentials_profile_name=credentials_profile_name,
                region_name=region_name,
                model=model_name,
                enable_any_tool_choice=cls.enable_any_tool_choice,
                enable_prefill=cls.enable_prefill,
                is_reasoning_model=cls.is_reasoning_model,
                **model_kwargs,
            )
        llm.client.converse_stream = llm_messages_print_decorator(
            llm.client.converse_stream)
        llm.client.converse = llm_messages_print_decorator(llm.client.converse)
        return llm


BedrockBaseModel.create_for_models(BEDROCK_MODEL_CONFIGS)
