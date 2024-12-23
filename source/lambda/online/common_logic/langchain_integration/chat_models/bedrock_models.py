import os
import boto3
from langchain_aws.chat_models import ChatBedrockConverse as _ChatBedrockConverse
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType
)
from common_logic.common_utils.logger_utils import get_logger, llm_messages_print_decorator
from . import Model
from ..model_config import MODEL_CONFIGS

logger = get_logger("bedrock_model")


class ChatBedrockConverse(_ChatBedrockConverse):
    enable_auto_tool_choice: bool = False
    enable_prefill: bool = True


class BedrockBaseModel(Model):
    
    default_model_kwargs = {"max_tokens": 2000,
                            "temperature": 0.7, "top_p": 0.9}
    enable_auto_tool_choice = False

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

        if br_aws_access_key_id != "" and br_aws_secret_access_key != "":
            logger.info(
                f"Bedrock Using AWS AKSK from environment variables. Key ID: {br_aws_access_key_id}")

            client = boto3.client("bedrock-runtime", region_name=region_name,
                                  aws_access_key_id=br_aws_access_key_id, aws_secret_access_key=br_aws_secret_access_key)

            llm = ChatBedrockConverse(
                client=client,
                region_name=region_name,
                model=cls.model_id,
                enable_auto_tool_choice=cls.enable_auto_tool_choice,
                enable_prefill=cls.enable_prefill,
                **model_kwargs,
            )
        else:
            llm = ChatBedrockConverse(
                credentials_profile_name=credentials_profile_name,
                region_name=region_name,
                model=cls.model_id,
                enable_auto_tool_choice=cls.enable_auto_tool_choice,
                enable_prefill=cls.enable_prefill,
                **model_kwargs,
            )
        llm.client.converse_stream = llm_messages_print_decorator(
            llm.client.converse_stream)
        llm.client.converse = llm_messages_print_decorator(llm.client.converse)
        return llm


model_classes = {
    f"{Model.model_id_to_class_name(model_id)}": BedrockBaseModel.create_for_model(model_id)
    for model_id in MODEL_CONFIGS
}
