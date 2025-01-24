import os
import boto3
from langchain_openai.embeddings import OpenAIEmbeddings as _OpenAIEmbeddings
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
from common_logic.common_utils.logger_utils import (
    get_logger
)
from . import Model
from ..model_config import (
    BEDROCK_EMBEDDING_CONFIGS
)

logger = get_logger("brconnector_bedrock_embedding_model")

class BrconnectorBedrockEmbeddings(_OpenAIEmbeddings):
    pass 


class BrconnectorBedrockEmbeddingBaseModel(Model):
    model_provider = ModelProvider.BRCONNECTOR_BEDROCK
    @classmethod
    def create_model(cls, **kwargs):
        base_url = kwargs.get("base_url", None) or os.environ.get("BRCONNECTOR_API_URL", None)
        api_key = kwargs.get('br_api_key',None) or os.environ.get("BR_API_KEY", None)
        default_model_kwargs = cls.default_model_kwargs or {}
        assert base_url, ("base_url is required",kwargs)
        embedding_model = BrconnectorBedrockEmbeddings(
            **default_model_kwargs,
            **kwargs,
            model=cls.model_id,
            api_key=api_key,
            base_url=base_url
        )
        return embedding_model


BrconnectorBedrockEmbeddingBaseModel.create_for_models(BEDROCK_EMBEDDING_CONFIGS)




       





