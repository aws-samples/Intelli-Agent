import os
import boto3
from langchain_aws.embeddings import BedrockEmbeddings as _BedrockEmbeddings
from shared.constant import (
    ModelProvider
)
from shared.utils.logger_utils import (
    get_logger
)
from . import EmbeddingModel
from ..model_config import (
    BEDROCK_EMBEDDING_CONFIGS
)

logger = get_logger("bedrock_embedding_model")


class BedrockEmbeddings(_BedrockEmbeddings):
    pass


class BedrockEmbeddingBaseModel(EmbeddingModel):
    model_provider = ModelProvider.BEDROCK

    @classmethod
    def create_model(cls, **kwargs):
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
        default_model_kwargs = cls.default_model_kwargs or {}

        client = None

        if br_aws_access_key_id != "" and br_aws_secret_access_key != "":
            logger.info(
                f"Bedrock Using AWS AKSK from environment variables. Key ID: {br_aws_access_key_id}")

            client = boto3.client("bedrock-runtime", region_name=region_name,
                                  aws_access_key_id=br_aws_access_key_id, aws_secret_access_key=br_aws_secret_access_key)

        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {})
        }

        model_kwargs = model_kwargs or None
        embedding_model = BedrockEmbeddings(
            model_kwargs=model_kwargs,
            client=client,
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            model_id=cls.model_id,
        )
        return embedding_model


BedrockEmbeddingBaseModel.create_for_models(BEDROCK_EMBEDDING_CONFIGS)
