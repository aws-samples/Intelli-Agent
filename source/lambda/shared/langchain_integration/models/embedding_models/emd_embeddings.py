from . import EmbeddingModel 
from ....constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
import boto3 
import os
from emd.integrations.langchain_clients import SageMakerVllmEmbeddings as _SageMakerVllmEmbeddings
from ..model_config import (
    BGE_M3_CONFIGS
)

session = boto3.Session()
current_region = session.region_name




class SageMakerVllmEmbeddings(_SageMakerVllmEmbeddings):
    pass 


class EmdEmbeddingBaseModel(EmbeddingModel):
    model_provider = ModelProvider.EMD

    @classmethod
    def create_model(cls, **kwargs):
        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = kwargs.get("region_name", None) or current_region
        group_name = kwargs.get(
            "group_name", os.environ.get('GROUP_NAME', "Admin"))
        
        default_model_kwargs = cls.default_model_kwargs or {}
        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {})
        }

        embedding_model = SageMakerVllmEmbeddings(
            model_id=cls.model_id,
            model_tag=group_name,
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            model_kwargs=model_kwargs,
        )
        
        return embedding_model


EmdEmbeddingBaseModel.create_for_models(BGE_M3_CONFIGS)
