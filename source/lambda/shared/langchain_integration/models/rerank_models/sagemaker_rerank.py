from . import RerankModelBase
from shared.utils.logger_utils import get_logger
from shared.constant import (
    ModelProvider,
    RerankModelType
)
import json
from langchain_core.documents import BaseDocumentCompressor,Document
import os
import boto3 
from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self
import sys 
from copy import deepcopy
from langchain_core.callbacks.manager import Callbacks
from langchain_community.llms.sagemaker_endpoint import ContentHandlerBase
from langchain_core.utils import pre_init

logger = get_logger("sagemaker_rerank_model")



class RerankContentHandler(ContentHandlerBase):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, query: str, documents:List[str],model_kwargs: Dict) -> bytes:
        rerank_pair = [[query,doc] for doc in documents]
        input_str = json.dumps({"inputs": rerank_pair})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json["rerank_scores"]
    

class SagemakerEndpointRerank(BaseModel, BaseDocumentCompressor):
    """Custom Sagemaker Inference Endpoints.
    """
    client: Any = None

    endpoint_name: str = ""
    """The name of the endpoint from the deployed Sagemaker model.
    Must be unique within an AWS Region."""

    region_name: str = ""
    """The aws region where the Sagemaker model is deployed, eg. `us-west-2`."""

    credentials_profile_name: Optional[str] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    content_handler: ContentHandlerBase
    """The content handler class that provides an input and
    output transform functions to handle formats between LLM
    and the endpoint.
    """

    """
     Example:
        .. code-block:: python

        from langchain_community.embeddings.sagemaker_endpoint import EmbeddingsContentHandler

        class ContentHandler(EmbeddingsContentHandler):
                content_type = "application/json"
                accepts = "application/json"

                def transform_input(self, prompts: List[str], model_kwargs: Dict) -> bytes:
                    input_str = json.dumps({prompts: prompts, **model_kwargs})
                    return input_str.encode('utf-8')

                def transform_output(self, output: bytes) -> List[List[float]]:
                    response_json = json.loads(output.read().decode("utf-8"))
                    return response_json["vectors"]
    """  # noqa: E501

    model_kwargs: Optional[Dict] = None
    """Keyword arguments to pass to the model."""

    endpoint_kwargs: Optional[Dict] = None
    """Optional attributes passed to the invoke_endpoint
    function. See `boto3`_. docs for more info.
    .. _boto3: <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
    """
    rarank_batch_size = 100

    model_config = ConfigDict(
        arbitrary_types_allowed=True, extra="forbid", protected_namespaces=()
    )

    @pre_init
    def validate_environment(cls, values: Dict) -> Dict:
        """Dont do anything if client provided externally"""
        if values.get("client") is not None:
            return values

        """Validate that AWS credentials to and python package exists in environment."""
        try:
            import boto3

            try:
                if values["credentials_profile_name"] is not None:
                    session = boto3.Session(
                        profile_name=values["credentials_profile_name"]
                    )
                else:
                    # use default credentials
                    session = boto3.Session()

                values["client"] = session.client(
                    "sagemaker-runtime", region_name=values["region_name"]
                )

            except Exception as e:
                raise ValueError(
                    "Could not load credentials to authenticate with AWS client. "
                    "Please check that credentials in the specified "
                    f"profile name are valid. {e}"
                ) from e

        except ImportError:
            raise ImportError(
                "Could not import boto3 python package. "
                "Please install it with `pip install boto3`."
            )
        return values

    def rerank(
            self,
            documents: Sequence[Document],
            query: str
        ):
        _model_kwargs = self.model_kwargs or {}
        _endpoint_kwargs = self.endpoint_kwargs or {}
        serialized_documents = [
            doc.page_content
            if isinstance(doc,Document)
            else doc
            for doc in documents
        ]
        body = self.content_handler.transform_input(
            query=query,
            documents=serialized_documents,
            model_kwargs=_model_kwargs,
        )
        content_type = self.content_handler.content_type
        accepts = self.content_handler.accepts

        # send request
        try:
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                Body=body,
                ContentType=content_type,
                Accept=accepts,
                **_endpoint_kwargs,
            )
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

        return self.content_handler.transform_output(response["Body"])

    
    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        # batch documents
        compressed = []
        for i in range(0, len(documents), self.rarank_batch_size):
            batch_documents = documents[i:i+self.rarank_batch_size]
            # rerank
            rerank_scores = self.rerank(
                documents=batch_documents, 
                query=query
            )
            # update rerank scores
            for j, doc in enumerate(batch_documents):
                doc_copy = Document(doc.page_content, metadata=deepcopy(doc.metadata))
                doc_copy.metadata["relevance_score"] = rerank_scores[j]
                compressed.append(doc_copy)
        
        return sorted(compressed, key=lambda x: x.metadata["relevance_score"], reverse=True)
        


class SageMakerMultiModelRerankModelBase(RerankModelBase,BaseDocumentCompressor):
    model_provider = ModelProvider.SAGEMAKER
    endpoint_kwargs:dict = Field(default_factory=dict)

    def create_content_handler(cls, **kwargs):
        raise RerankContentHandler()

    @classmethod
    def create_model(cls, **kwargs):
        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = (
            kwargs.get("region_name", None)
            or os.environ.get("AWS_REGION", None)
            or None
        )
        aws_access_key_id = os.environ.get("SAGEMAKER_AWS_ACCESS_KEY_ID", "")
        aws_secret_access_key = os.environ.get(
            "SAGEMAKER_AWS_SECRET_ACCESS_KEY", ""
        )
        default_model_kwargs = cls.default_model_kwargs or {}

        content_handler = cls.create_content_handler(**kwargs)

        client = None
        if aws_access_key_id != "" and aws_secret_access_key != "":
            logger.info(
                f"Bedrock Using AWS AKSK from environment variables. Key ID: {aws_access_key_id}"
            )

            client = boto3.client(
                "sagemaker-runtime",
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        model_kwargs = {
            **default_model_kwargs,
            **kwargs.get("model_kwargs", {}),
        }
        model_kwargs = model_kwargs or None
        logger.info("Model kwargs: ")
        logger.info(kwargs)
        target_model = kwargs.get("target_model")
        model_id = kwargs.get("model_endpoint")

        endpoint_kwargs = cls.endpoint_kwargs.copy()
        if target_model:
            endpoint_kwargs["TargetModel"] = target_model

        endpoint_kwargs = endpoint_kwargs or None

        rerank_model = SagemakerEndpointRerank(
            # model_kwargs=model_kwargs,
            endpoint_kwargs=endpoint_kwargs,
            client=client,
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            endpoint_name=model_id,
            content_handler=content_handler,
        )
        return rerank_model
        
        
class SageMakerMultiModelRerankBce(SageMakerMultiModelRerankModelBase):
    model_provider = ModelProvider.SAGEMAKER
    model_id = RerankModelType.BGE_RERANKER_LARGE
    endpoint_kwargs:dict = Field(
        default_factory= lambda : {"TargetModel": "bge_reranker_model.tar.gz"}
    )




