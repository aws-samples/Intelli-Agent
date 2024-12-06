import os
from langchain_aws.chat_models import ChatBedrockConverse as _ChatBedrockConverse
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType
)
from common_logic.common_utils.logger_utils import get_logger, llm_messages_print_decorator
from . import Model

logger = get_logger("bedrock_model")


class ChatBedrockConverse(_ChatBedrockConverse):
    enable_auto_tool_choice: bool = False
    enable_prefill: bool = True


# Bedrock model type
class Claude2(Model):
    model_id = LLMModelType.CLAUDE_2
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


class ClaudeInstance(Claude2):
    model_id = LLMModelType.CLAUDE_INSTANCE


class Claude21(Claude2):
    model_id = LLMModelType.CLAUDE_21


class Claude3Sonnet(Claude2):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3Haiku(Claude2):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35Sonnet(Claude2):
    model_id = LLMModelType.CLAUDE_3_5_SONNET


class Claude35SonnetV2(Claude2):
    model_id = LLMModelType.CLAUDE_3_5_SONNET_V2


class Claude35Haiku(Claude2):
    model_id = LLMModelType.CLAUDE_3_5_HAIKU


class MistralLarge2407(Claude2):
    model_id = LLMModelType.MISTRAL_LARGE_2407
    enable_prefill = False


class Llama3d1Instruct70B(Claude2):
    model_id = LLMModelType.LLAMA3_1_70B_INSTRUCT
    enable_auto_tool_choice = False
    enable_prefill = False


class Llama3d2Instruct90B(Claude2):
    model_id = LLMModelType.LLAMA3_2_90B_INSTRUCT
    enable_auto_tool_choice = False
    enable_prefill = False


class CohereCommandRPlus(Claude2):
    model_id = LLMModelType.COHERE_COMMAND_R_PLUS
    enable_auto_tool_choice = False
    enable_prefill = False


class NovaPro(Claude2):
    model_id = LLMModelType.NOVA_PRO
    enable_auto_tool_choice = False
    enable_prefill = False
    
    # @classmethod
    # def create_model(cls, model_kwargs=None, **kwargs):
    #     model_kwargs = model_kwargs or {}
        
    #     # Get the inference profile ARN from environment variable or kwargs
    #     inference_profile = (
    #         kwargs.get("inference_profile", None)
    #         or os.environ.get("NOVA_PRO_INFERENCE_PROFILE", None)
    #         or "arn:aws:bedrock:us-west-2:817734611975:inference-profile/us.amazon.nova-pro-v1:0"
    #     )
        
    #     # Add inference profile to the model kwargs
    #     bedrock_parameters = {"inferenceProfile": inference_profile}
    #     model_kwargs["model_kwargs"] = bedrock_parameters
        
    #     # Merge with default kwargs
    #     model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

    #     credentials_profile_name = (
    #         kwargs.get("credentials_profile_name", None)
    #         or os.environ.get("AWS_PROFILE", None)
    #         or None
    #     )
    #     region_name = (
    #         kwargs.get("region_name", None)
    #         or os.environ.get("BEDROCK_REGION", None)
    #         or None
    #     )

    #     llm = ChatBedrockConverse(
    #         credentials_profile_name=credentials_profile_name,
    #         region_name=region_name,
    #         model=cls.model_id,
    #         enable_auto_tool_choice=cls.enable_auto_tool_choice,
    #         enable_prefill=cls.enable_prefill,
    #         **model_kwargs,
    #     )
    #     llm.client.converse_stream = llm_messages_print_decorator(
    #         llm.client.converse_stream)
    #     llm.client.converse = llm_messages_print_decorator(llm.client.converse)
    #     return llm
