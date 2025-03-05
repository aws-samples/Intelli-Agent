from typing import Union
from .. import ModelBase 

from common_logic.common_utils.constant import ModelProvider

from ..model_config import EmbeddingModelConfig


class EmbeddingModelBase(ModelBase):
    model_map = {}
    default_model_kwargs: Union[dict, None] = None

    def load_module(cls,model_provider):
        _load_module(model_provider)

    @classmethod
    def create_for_model(cls, config: EmbeddingModelConfig):
        """Factory method to create a model with a specific model id"""
        # config = MODEL_CONFIGS[model_id]
        model_id = config.model_id
        # Create a new class dynamically
        model_class = type(
            f"{cls.model_id_to_class_name(model_id)}",
            (cls,),
            {
                "model_id": model_id,
                "default_model_kwargs": config.default_model_kwargs
            },
        )
        return model_class


EmbeddingModel = EmbeddingModelBase


def _import_bedrock_embeddings():
    from . import bedrock_embeddings


def _import_brconnector_bedrock_embeddings():
    from . import brconnector_bedrock_embeddings


def _import_openai_embeddings():
    from . import openai_embeddings


def _import_emd_embeddings():
    from . import emd_embeddings


def _import_sagemaker_embeddings():
    from . import sagemaker_embeddings


def _load_module(model_provider):
    assert model_provider in MODEL_PROVIDER_LOAD_FN_MAP, (
        model_provider,
        MODEL_PROVIDER_LOAD_FN_MAP,
    )
    MODEL_PROVIDER_LOAD_FN_MAP[model_provider]()


MODEL_PROVIDER_LOAD_FN_MAP = {
    ModelProvider.BEDROCK: _import_bedrock_embeddings,
    ModelProvider.BRCONNECTOR_BEDROCK: _import_brconnector_bedrock_embeddings,
    ModelProvider.OPENAI: _import_openai_embeddings,
    ModelProvider.EMD: _import_emd_embeddings,
    ModelProvider.SAGEMAKER_MULTIMODEL: _import_sagemaker_embeddings,
}

