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

def process_shard(shard, embeddings_model_endpoint_name, aws_region, os_index_name, os_domain_ep, os_http_auth) -> int:
    embeddings = create_sagemaker_embeddings_from_js_model(embeddings_model_endpoint_name, aws_region)
    docsearch = OpenSearchVectorSearch(
        index_name=os_index_name,
        embedding_function=embeddings,
        opensearch_url="https://{}".format(os_domain_ep),
        http_auth = os_http_auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    docsearch.add_documents(documents=shard)
    return 0

def construct_shard(bucketName: str, prefix: str, embeddingEndpointName: str) -> str:
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

# Main entry point
if __name__ == "__main__":
    """
    Embedding Sample, shard format:
    [
        Document(
        page_content='Data Transfer Hub (数据传输解决方案)\n\n轻松将数据移入和移出 AWS 中国区域\n\n概览\n\n此解决方案可为 Amazon Simple Storage Service (Amazon S3) 对象和 Amazon Elastic Container Registry (Amazon ECR) 映像提供安全、可扩展且可追踪的数据传输。使用数据传输解决方案，您可以执行以下任何任务：在 AWS S3 之间传输对象\n\n优势\n\n直观的用户界面 客户可在用户界面上为 Amazon S3 对象和 Amazon ECR 映像创建和管理数据传输任务。\n\n支持各类源 将数据从其他云服务商的对象存储服务（包括阿里云 OSS，腾讯 COS，七牛 Kodo 以及其他兼容 Amazon S3 的云存储服务）传输到 Amazon S3。在 Amazon ECR 之间传输容器镜像。将容器镜像从公共容器镜像仓库（例如 Docker Hub、Google gcr.io 和 Red Hat Quay.io）传输到 Amazon ECR。\n\n无服务器架构\n\n传输任务可按需使用并随用随付。有关更多信息，请参阅实施指南的“成本”部分。', 
        metadata={
            'source': '/tmp/tmpmmod0k9m/csdc/dth.txt', 
            'timestamp': 1693494146.1509278, 
            'embeddings_model': 'embedding-endpoint'
        })
    ]
    """
    shard = construct_shard('<S3 bucket created in fror embedding documents>', '<S3 upload prefix>', 'embedding-endpoint')
    
    process_shard(shard, 'embedding-endpoint', 'us-east-1', 'chatbot-index', '<AOS endpoint>', awsauth)

    """
    LLM Sample
    """

    query_knowledge = "给我介绍一下什么是data transfer hub方案？"
    query_embedding = SagemakerEndpointVectorOrCross(prompt="为这个句子生成表示以用于检索相关文章：" + query_knowledge, endpoint_name="embedding-endpoint", region_name='us-east-1', model_type="vector", stop=None)
    logging.info(f"query_embedding is {query_embedding}")

    # For demo usage, should be retrieved from AOS
    retrieveContext = """
    Data Transfer Hub (数据传输解决方案)
    轻松将数据移入和移出 AWS 中国区域
    概览
    此解决方案可为 Amazon Simple Storage Service (Amazon S3) 对象和 Amazon Elastic Container Registry (Amazon ECR) 映像提供安全、可扩展且可追踪的数据传输。使用数据传输解决方案，您可以执行以下任何任务：在 AWS S3 之间传输对象
    优势
    直观的用户界面 客户可在用户界面上为 Amazon S3 对象和 Amazon ECR 映像创建和管理数据传输任务。
    支持各类源 将数据从其他云服务商的对象存储服务（包括阿里云 OSS，腾讯 COS，七牛 Kodo 以及其他兼容 Amazon S3 的云存储服务）传输到 Amazon S3。在 Amazon ECR 之间传输容器镜像。将容器镜像从公共容器镜像仓库（例如 Docker Hub、Google gcr.io 和 Red Hat Quay.io）传输到 Amazon ECR。
    无服务器架构
    传输任务可按需使用并随用随付。有关更多信息，请参阅实施指南的“成本”部分。
    """
    # Optional, predict recall knowledge correlation
    score = float(SagemakerEndpointVectorOrCross(prompt=query_knowledge, endpoint_name="cross-endpoint", region_name="us-east-1", model_type="cross", stop=None, context=retrieveContext))
    logging.info(f"score is {score}")

    # For demo usage, refer main.py in executor folder for recall process
    recallContext = """
    Data Transfer Hub (数据传输解决方案)
    轻松将数据移入和移出 AWS 中国区域
    概览
    此解决方案可为 Amazon Simple Storage Service (Amazon S3) 对象和 Amazon Elastic Container Registry (Amazon ECR) 映像提供安全、可扩展且可追踪的数据传输。使用数据传输解决方案，您可以执行以下任何任务：在 AWS S3 之间传输对象
    优势
    直观的用户界面 客户可在用户界面上为 Amazon S3 对象和 Amazon ECR 映像创建和管理数据传输任务。
    支持各类源 将数据从其他云服务商的对象存储服务（包括阿里云 OSS，腾讯 COS，七牛 Kodo 以及其他兼容 Amazon S3 的云存储服务）传输到 Amazon S3。在 Amazon ECR 之间传输容器镜像。将容器镜像从公共容器镜像仓库（例如 Docker Hub、Google gcr.io 和 Red Hat Quay.io）传输到 Amazon ECR。
    无服务器架构
    传输任务可按需使用并随用随付。有关更多信息，请参阅实施指南的“成本”部分。
    """
    answer = SagemakerEndpointVectorOrCross(prompt="请给我介绍一下什么是Data Transfer Hub方案？", endpoint_name="instruct-endpoint", region_name="us-east-1", model_type="answer", stop=None, history=[], parameters={'temperature': 0.8}, context=recallContext)

    logger.info(f"answer is {answer}")




