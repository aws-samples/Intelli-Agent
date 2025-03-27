import os
import boto3
from langchain_aws.embeddings import BedrockEmbeddings as _BedrockEmbeddings
from shared.constant import (
    ModelProvider
)
from shared.utils.logger_utils import (
    get_logger
)
import pickle
from shared.utils.boto3_utils import get_boto3_client
from . import EmbeddingModel
from ..model_config import (
    BEDROCK_EMBEDDING_CONFIGS
)
from shared.utils.cache_utils import (
    lru_cache_with_logging,
    alru_cache_with_logging
)

logger = get_logger("bedrock_embedding_model")


class BedrockEmbeddings(_BedrockEmbeddings):
    
    @staticmethod
    def embed_query_key(self,text:str):
        return pickle.dumps({
            "cls":self.__class__.__name__,
            "model_id":self.model_id,
            "model_kwargs":self.model_kwargs,
            "normalize":self.normalize,
            'config':self.config,
            "endpoint_url":self.endpoint_url,
            "region_name":self.region_name,
            "credentials_profile_name":self.credentials_profile_name,
            "text":text
        })

    async def aembed_documents(self, texts):
        return await super().aembed_documents(texts)
    
    @alru_cache_with_logging(key=embed_query_key)
    async def aembed_query(self, text):
        return await super().aembed_query(text)
     
    @lru_cache_with_logging(key=embed_query_key)
    def embed_query(self, text):
        return super().embed_query(text)
    

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

            client = get_boto3_client(
                "bedrock-runtime", 
                region_name=region_name,
                aws_access_key_id=br_aws_access_key_id, 
                aws_secret_access_key=br_aws_secret_access_key
            )
        
        if client is None:
            client = get_boto3_client(
                "bedrock-runtime",
                profile_name=credentials_profile_name,
                region_name=region_name,
                
            )

        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs")
        }

        model_kwargs = model_kwargs or None

        embedding_model = BedrockEmbeddings(
            model_kwargs=model_kwargs,
            client=client,
            # credentials_profile_name=credentials_profile_name,
            # region_name=region_name,
            model_id=cls.model_id,
        )
        return embedding_model


BedrockEmbeddingBaseModel.create_for_models(BEDROCK_EMBEDDING_CONFIGS)
