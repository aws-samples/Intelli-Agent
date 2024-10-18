import os
from langchain_aws.chat_models import ChatBedrockConverse
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType
)
from common_logic.common_utils.logger_utils import get_logger
from . import Model


logger = get_logger("bedrock_model")

# Bedrock model type
class Claude2(Model):
    model_id = LLMModelType.CLAUDE_2
    default_model_kwargs = {"max_tokens": 2000, "temperature": 0.7, "top_p": 0.9}

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
            **model_kwargs,
        )
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


class MistralLarge2407(Claude2):
    model_id = LLMModelType.MISTRAL_LARGE_2407


class Llama3d1Instruct70B(Claude2):
    model_id = LLMModelType.LLAMA3_1_70B_INSTRUCT

class CohereCommandRPlus(Claude2):
    model_id = LLMModelType.COHERE_COMMAND_R_PLUS
    


