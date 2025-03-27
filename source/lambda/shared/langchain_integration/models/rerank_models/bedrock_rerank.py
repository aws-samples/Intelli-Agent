from . import RerankModelBase
from shared.utils.logger_utils import get_logger
from ..model_config import (
    BEDROCK_RERANK_CONFIGS
)
from shared.constant import (
    ModelProvider
)
import json
from langchain_core.documents import BaseDocumentCompressor,Document
import os
import boto3 
from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self
from langchain_aws.document_compressors.rerank import BedrockRerank as _BedrockRerank
import sys 
from copy import deepcopy
from langchain_core.callbacks.manager import Callbacks
from ..model_config import BEDROCK_RERANK_CONFIGS
from shared.utils.boto3_utils import get_boto3_client

logger = get_logger("bedrock_rerank_model")


class BedrockRerank(BaseDocumentCompressor):
    client: Any = Field(default=None, exclude=True)  #: :meta private:
    """Bedrock client."""
    region_name: Optional[str] = None
    """The aws region e.g., `us-west-2`. Fallsback to AWS_DEFAULT_REGION env variable
    or region specified in ~/.aws/config in case it is not provided here.
    """

    credentials_profile_name: Optional[str] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    model_id: str
    """Id of the model to call, e.g., amazon.titan-embed-text-v1, this is
    equivalent to the modelId property in the list-foundation-models api"""

    top_n: Optional[int] = sys.maxsize

    model_kwargs: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
    )
    
    @model_validator(mode="before")
    @classmethod
    def initialize_client(cls, values: Dict[str, Any]) -> Any:
        """Initialize the AWS Bedrock client."""
        if not values.get("client"):
            session = (
                boto3.Session(profile_name=values.get("credentials_profile_name"))
                if values.get("credentials_profile_name", None)
                else boto3.Session()
            )
            values["client"] = session.client(
                "bedrock-runtime",
                region_name=values.get("region_name"),
            )
        return values
    
    def rerank(
        self,
        documents: Sequence[Union[str, Document]],
        query: str,
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns an ordered list of documents based on their relevance to the query.

        Args:
            query: The query to use for reranking.
            documents: A sequence of documents to rerank.
            top_n: The number of top-ranked results to return. Defaults to self.top_n.
            additional_model_request_fields: Additional fields to pass to the model.

        Returns:
            List[Dict[str, Any]]: A list of ranked documents with relevance scores.
        """
        if len(documents) == 0:
            return []

        # Serialize documents for the Bedrock API
        serialized_documents = [
            doc.page_content
            if isinstance(doc,Document)
            else doc
            for doc in documents
        ]
        top_n = top_n or self.top_n

        request_body = {
            "query":query,
            "documents": serialized_documents,
            "top_n":top_n,
            **self.model_kwargs
        }
        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )
        result = json.loads(response["body"].read())
        results = result["results"]
        return results

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Compress documents using Bedrock's rerank API.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        compressed = []
        for res in self.rerank(documents, query):
            doc = documents[res["index"]]
            doc_copy = Document(doc.page_content, metadata=deepcopy(doc.metadata))
            doc_copy.metadata["relevance_score"] = res["relevance_score"]
            compressed.append(doc_copy)
        return compressed
    
    

class BedrockRerankBaseModel(RerankModelBase):
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
                region_name=region_name
            )

        extra_kwargs = {k: kwargs[k] for k in ["top_n"] if k in kwargs}

        default_model_kwargs = cls.default_model_kwargs or {}

        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {})
        }
                                          
        extra_kwargs.update({"model_kwargs": model_kwargs})
        logger.info('init BedrockRerank...')
        rerank_model = BedrockRerank(
            client=client,
            # credentials_profile_name=credentials_profile_name,
            # region_name=region_name,
            model_id=cls.model_id,
            **extra_kwargs
        )
        logger.info('after init BedrockRerank...')
        return rerank_model


BedrockRerankBaseModel.create_for_models(BEDROCK_RERANK_CONFIGS)