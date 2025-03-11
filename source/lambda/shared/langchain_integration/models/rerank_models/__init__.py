from .. import ModelBase 
from typing import Union
from ..model_config import EmbeddingModelConfig
from shared.constant import ModelProvider


class RerankModelBase(ModelBase):
    model_map = {}
    default_model_kwargs: Union[dict, None] = None
    
    @classmethod
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


RerankModel = RerankModelBase

def _import_bedrock_rerank():
    from . import bedrock_rerank

def _import_emd_rerank():
    from . import emd_rerank


def _load_module(model_provider):
    assert model_provider in MODEL_PROVIDER_LOAD_FN_MAP, (
        model_provider, MODEL_PROVIDER_LOAD_FN_MAP)
    MODEL_PROVIDER_LOAD_FN_MAP[model_provider]()


MODEL_PROVIDER_LOAD_FN_MAP = {
    ModelProvider.BEDROCK: _import_bedrock_rerank,
    # ModelProvider.BRCONNECTOR_BEDROCK: _import_brconnector_bedrock_embeddings,
    # ModelProvider.OPENAI: _import_openai_embeddings,
    ModelProvider.EMD: _import_emd_rerank,
    # ModelProvider.SAGEMAKER_MULTIMODEL: _import_sagemaker_embeddings,
}
