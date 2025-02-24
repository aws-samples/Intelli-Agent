from langchain_openai.embeddings import OpenAIEmbeddings as _OpenAIEmbeddings
import os
from . import EmbeddingModelBase
from common_logic.common_utils.constant import (
    ModelProvider
)

from ..model_config import OPENAI_EMBEDDING_CONFIG


class OpenAIEmbeddings(_OpenAIEmbeddings):
    pass


class OpenAIEmbeddingBaseModel(EmbeddingModelBase):
    model_provider = ModelProvider.OPENAI

    @classmethod
    def create_model(cls, **kwargs):
        base_url = kwargs.get("base_url", None) or os.environ.get(
            "OPENAI_BASE_URL", None)
        api_key = kwargs.get('openai_api_key', None) or os.environ.get(
            "OPENAI_API_KEY", None)
        default_model_kwargs = cls.default_model_kwargs or {}

        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {})
        }
        model_kwargs = model_kwargs or None

        return OpenAIEmbeddings(
            model_kwargs=model_kwargs,
            base_url=base_url,
            api_key=api_key,
            model=cls.model_id
        )


OpenAIEmbeddingBaseModel.create_for_models(OPENAI_EMBEDDING_CONFIG)
