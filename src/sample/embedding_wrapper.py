import asyncio
import json
import os
from functools import partial
from typing import Any, Dict, List, Optional

from langchain.embeddings.base import Embeddings
# from langchain.pydantic_v1 import BaseModel, Extra, root_validator

import os
import time
import logging
import boto3
import tempfile
import numpy as np

from langchain.vectorstores import OpenSearchVectorSearch
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from opensearchpy import RequestsHttpConnection
from sagemaker_utils import create_sagemaker_embeddings_from_js_model, SagemakerEndpointVectorOrCross
from requests_aws4auth import AWS4Auth

s3 = boto3.resource('s3')
aws_region = boto3.Session().region_name
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, aws_region, 'es', session_token=credentials.token)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_FILE_SIZE = 1024*1024*100 # 100MB
MAX_OS_DOCS_PER_PUT = 500
CHUNK_SIZE_FOR_DOC_SPLIT = 600
CHUNK_OVERLAP_FOR_DOC_SPLIT = 20

class CSDCEmbeddings:
    """CSDC embedding models.

    To authenticate, the AWS client uses the following methods to
    automatically load credentials:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html

    If a specific credential profile should be used, you must pass
    the name of the profile from the ~/.aws/credentials file that is to be used.

    Make sure the credentials / roles used have the required policies to
    access the CSDC service.
    """

    """
    Example:
        .. code-block:: python
        from llm_utils import CSDCEmbeddings

        embeddings = CSDCEmbeddings(region = 'us-east-1', aosEndpointName = 'Amazon OpenSearch Service Domain Endpoint')
        doc_reult = embeddings.embed_documents(bucketName=<s3 bucket name>, prefix=<s3 bucket prefix>)
        logging.info(f"doc_reult is {doc_reult}, the type of doc_reult is {type(doc_reult)}")
    """

    def __init__(self, aosEndpointName: str, region: int):
        self.aosEndpointName = aosEndpointName
        self.region = region

    client: Any  #: :meta private:
    """CSDC client."""
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

    model_id: str = "csdc-default-model"
    """Id of the model to call, e.g., csdc-default-model, this is
    equivalent to the modelId property in the list-foundation-models api"""

    model_kwargs: Optional[Dict] = None
    """Key word arguments to pass to the model."""

    endpoint_url: Optional[str] = None
    """Needed if you don't want to default to us-east-1 endpoint"""

    class Config:
        """Configuration for this pydantic object."""

        # extra = Extra.forbid

    # @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that AWS credentials to and python package exists in environment."""

        if values["client"] is not None:
            return values

        try:
            import boto3

            if values["credentials_profile_name"] is not None:
                session = boto3.Session(profile_name=values["credentials_profile_name"])
            else:
                # use default credentials
                session = boto3.Session()

            client_params = {}
            if values["region_name"]:
                client_params["region_name"] = values["region_name"]

            if values["endpoint_url"]:
                client_params["endpoint_url"] = values["endpoint_url"]

            values["client"] = session.client("bedrock", **client_params)

        except ImportError:
            raise ModuleNotFoundError(
                "Could not import boto3 python package. "
                "Please install it with `pip install boto3`."
            )
        except Exception as e:
            raise ValueError(
                "Could not load credentials to authenticate with AWS client. "
                "Please check that credentials in the specified "
                "profile name are valid."
            ) from e

        return values

    def _embedding_func_legacy(self, text: str) -> List[float]:
        """Call out to CSDC embedding endpoint."""
        # replace newlines, which can negatively affect performance.
        text = text.replace(os.linesep, " ")
        _model_kwargs = self.model_kwargs or {}

        input_body = {**_model_kwargs, "inputText": text}
        body = json.dumps(input_body)

        try:
            response = self.client.invoke_model(
                body=body,
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json",
            )
            response_body = json.loads(response.get("body").read())
            return response_body.get("embedding")
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

    def embed_documents_legacy(self, texts: List[str]) -> List[List[float]]:
        """Compute doc embeddings using a CSDC model.

        Args:
            texts: The list of texts to embed

        Returns:
            List of embeddings, one for each text.
        """
        results = []
        for text in texts:
            response = self._embedding_func_legacy(text)
            results.append(response)
        return results

    async def aembed_query(self, text: str) -> List[float]:
        """Asynchronous compute query embeddings using a CSDC model.

        Args:
            text: The text to embed.

        Returns:
            Embeddings for the text.
        """

        return await asyncio.get_running_loop().run_in_executor(
            None, partial(self.embed_query, text)
        )

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Asynchronous compute doc embeddings using a CSDC model.

        Args:
            texts: The list of texts to embed

        Returns:
            List of embeddings, one for each text.
        """

        result = await asyncio.gather(*[self.aembed_query(text) for text in texts])

        return list(result)

    def _construct_shard(self, bucketName: str, prefix: str, embeddingEndpointName: str) -> str:
        """Inner helper function to construct a shard of documents.

        Args:
            bucketName (str): 
            prefix (str): _description_
            embeddingEndpointName (str): _description_

        Returns:
            str: _description_
        """        
        docs = []
        document_bucket = s3.Bucket(bucketName)
        for obj in document_bucket.objects.filter(Prefix=prefix):
            if obj.key.endswith("/"):
                continue
            else:
                with tempfile.TemporaryDirectory(dir='/tmp') as temp_dir:
                    file_path = f"{temp_dir}/{obj.key}"
                    logging.info(f"bucketName={bucketName}, obj.key={obj.key}, file_path={file_path}")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    s3.meta.client.download_file(bucketName, obj.key, file_path)

                    loader = UnstructuredFileLoader(file_path)
                    docs.extend(loader.load())

        # add a custom metadata field, timestamp and embeddings_model
        for doc in docs:
            doc.metadata['timestamp'] = time.time()
            doc.metadata['embeddings_model'] = embeddingEndpointName

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = CHUNK_SIZE_FOR_DOC_SPLIT,
            chunk_overlap = CHUNK_OVERLAP_FOR_DOC_SPLIT,
            length_function = len,
        )

        chunks = text_splitter.create_documents([doc.page_content for doc in docs], metadatas=[doc.metadata for doc in docs])

        db_shards = (len(chunks) // MAX_OS_DOCS_PER_PUT) + 1
        shards = np.array_split(chunks, db_shards)
        return shards[0].tolist()

    def _embedding_func(self, shard) -> List[float]:
        """Call out to CSDC embedding endpoint.
        Args:
            shard (_type_): must be a list of documents, sample format as follows:
            [
                Document(
                page_content='Data Transfer Hub (数据传输解决方案)\n\n轻松将数据移入和移出 AWS 中国区域\n\n概览\n\n此解决方案可为 Amazon Simple Storage Service (Amazon S3) 对象和 Amazon Elastic Container Registry (Amazon ECR) 映像提供安全、可扩展且可追踪的数据传输。使用数据传输解决方案，您可以执行以下任何任务：在 AWS S3 之间传输对象\n\n优势\n\n直观的用户界面 客户可在用户界面上为 Amazon S3 对象和 Amazon ECR 映像创建和管理数据传输任务。\n\n支持各类源 将数据从其他云服务商的对象存储服务（包括阿里云 OSS，腾讯 COS，七牛 Kodo 以及其他兼容 Amazon S3 的云存储服务）传输到 Amazon S3。在 Amazon ECR 之间传输容器镜像。将容器镜像从公共容器镜像仓库（例如 Docker Hub、Google gcr.io 和 Red Hat Quay.io）传输到 Amazon ECR。\n\n无服务器架构\n\n传输任务可按需使用并随用随付。有关更多信息，请参阅实施指南的“成本”部分。', 
                metadata={
                    'source': '/tmp/tmpmmod0k9m/csdc/dth.txt', 
                    'timestamp': 1693494146.1509278, 
                    'embeddings_model': 'embedding-endpoint'
                })
            ]
        Returns:
            List[float]: embeddings for the documents.
        """        
        embeddings = create_sagemaker_embeddings_from_js_model('embedding-endpoint', self.region)
        return embeddings
    
    def embed_documents(self, bucketName: str, prefix: str) -> List[List[float]]:
        """Compute doc embeddings using a CSDC model.
        Args:
            bucketName (str): The name of the bucket to embed
            prefix (str): The prefix of the bucket to embed
        Returns:
            List of embeddings, one for each text.
        """    
        shard = self._construct_shard(bucketName, prefix, 'embedding-endpoint')
        embeddings = self._embedding_func(shard)
        return embeddings.embed_documents([str(shard[0])])

    def embed_query(self, text: str) -> List[float]:
        """Compute query embeddings using a CSDC model.

        Args:
            text: The text to embed.

        Returns:
            Embeddings for the text.
        """
        embeddings = self._embedding_func(text)
        return embeddings.embed_documents([text])
