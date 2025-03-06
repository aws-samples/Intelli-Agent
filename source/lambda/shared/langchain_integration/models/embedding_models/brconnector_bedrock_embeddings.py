import os
import boto3
from langchain_openai.embeddings import OpenAIEmbeddings as _OpenAIEmbeddings
from ....constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
from ....utils.logger_utils import (
    get_logger
)
from . import EmbeddingModel
from ..model_config import (
    BEDROCK_EMBEDDING_CONFIGS
)

logger = get_logger("brconnector_bedrock_embedding_model")


class BrconnectorBedrockEmbeddings(_OpenAIEmbeddings):
    pass


class BrconnectorBedrockEmbeddingBaseModel(EmbeddingModel):
    model_provider = ModelProvider.BRCONNECTOR_BEDROCK

    @classmethod
    def create_model(cls, **kwargs):
        base_url = kwargs.get("base_url", None) or os.environ.get(
            "BRCONNECTOR_API_URL", None)
        api_key = kwargs.get('br_api_key', None) or os.environ.get(
            "BR_API_KEY", None)
        default_model_kwargs = cls.default_model_kwargs or {}
        assert base_url, ("base_url is required", kwargs)

        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {})
        }
        model_kwargs = model_kwargs or None
        embedding_model = BrconnectorBedrockEmbeddings(
            model_kwargs=model_kwargs,
            model=cls.model_id,
            api_key=api_key,
            base_url=base_url
        )
        return embedding_model


BrconnectorBedrockEmbeddingBaseModel.create_for_models(BEDROCK_EMBEDDING_CONFIGS)
