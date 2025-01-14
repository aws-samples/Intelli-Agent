from . import Model
from common_logic.common_utils.constant import (
    MessageType,
    LLMModelType,
    ModelProvider
)
import os 
import boto3
from dmaa.integrations.langchain_clients import SageMakerVllmChatModel as _SageMakerVllmChatModel

session = boto3.Session()
current_region = session.region_name

class SageMakerVllmChatModel(_SageMakerVllmChatModel):
    enable_any_tool_choice: bool = False
    enable_prefill: bool = True
    

class Qwen25Instruct72bAwq(Model):
    model_id = LLMModelType.QWEN25_INSTRUCT_72B_AWQ
    enable_any_tool_choice: bool = False
    enable_prefill: bool = True
    default_model_kwargs = {
        "max_tokens": 2000,
        "temperature": 0.7, 
        "top_p": 0.9
    }
    model_provider = ModelProvider.DMAA
    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = kwargs.get("region_name", None) or current_region
        group_name = kwargs.get("group_name", os.environ.get('GROUP_NAME',"Admin"))

        llm = SageMakerVllmChatModel(
            model_id=cls.model_id,
            model_tag=group_name,
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill
        )
        return llm 
    



