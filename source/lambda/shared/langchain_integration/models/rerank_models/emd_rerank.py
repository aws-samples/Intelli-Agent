from . import RerankModelBase

from ....constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)

import boto3 
import os

from emd.integrations.langchain_clients import SageMakerVllmRerank as _SageMakerVllmRerank

from ..model_config import (
    BGE_RERANK_V2_M3_CONFIGS
)

session = boto3.Session()
current_region = session.region_name

class SageMakerVllmRerank(_SageMakerVllmRerank):
    pass 


class EmdRerankBaseModel(RerankModelBase):
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
        extra_kwargs = {k: kwargs[k] for k in ["top_n"] if k in kwargs}
        embedding_model = SageMakerVllmRerank(
            model_id=cls.model_id,
            model_tag=group_name,
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            model_kwargs=model_kwargs,
            **extra_kwargs
        )
        
        return embedding_model


EmdRerankBaseModel.create_for_model(BGE_RERANK_V2_M3_CONFIGS)