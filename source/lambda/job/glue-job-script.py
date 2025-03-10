import itertools
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Generator, Iterable, List

import boto3
import chardet
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger()
logger.setLevel(logging.INFO)


from awsglue.utils import getResolvedOptions

args = getResolvedOptions(
    sys.argv,
    [
        "AOS_ENDPOINT",
        "BATCH_FILE_NUMBER",
        "BATCH_INDICE",
        "DOCUMENT_LANGUAGE",
        "EMBEDDING_MODEL_ENDPOINT",
        "ETL_MODEL_ENDPOINT",
        "JOB_NAME",
        "OFFLINE",
        "ETL_OBJECT_TABLE",
        "TABLE_ITEM_ID",
        "QA_ENHANCEMENT",
        "REGION",
        "RES_BUCKET",
        "S3_BUCKET",
        "S3_PREFIX",
        "CHATBOT_ID",
        "INDEX_ID",
        "EMBEDDING_MODEL_TYPE",
        "CHATBOT_TABLE",
        "INDEX_TYPE",
        "OPERATION_TYPE",
        "PORTAL_BUCKET",
        "BEDROCK_REGION",
        "MODEL_TABLE",
        "GROUP_NAME",
    ],
)

from llm_bot_dep import sm_utils
from llm_bot_dep.constant import SplittingType
from llm_bot_dep.loaders.auto import process_object
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.storage_utils import save_content_to_s3

# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers_cache"
os.environ["NOUGAT_CHECKPOINT"] = "/tmp/nougat_checkpoint"

# Parse arguments
if "BATCH_INDICE" not in args:
    args["BATCH_INDICE"] = "0"

aosEndpoint = args["AOS_ENDPOINT"]
batchFileNumber = args["BATCH_FILE_NUMBER"]
batchIndice = args["BATCH_INDICE"]
document_language = args["DOCUMENT_LANGUAGE"]
embedding_model_endpoint = args["EMBEDDING_MODEL_ENDPOINT"]
etlModelEndpoint = args["ETL_MODEL_ENDPOINT"]
offline = args["OFFLINE"]
etl_object_table_name = args["ETL_OBJECT_TABLE"]
portal_bucket_name = args["PORTAL_BUCKET"]
table_item_id = args["TABLE_ITEM_ID"]
qa_enhancement = args["QA_ENHANCEMENT"]
region = args["REGION"]
bedrock_region = args["BEDROCK_REGION"]
res_bucket = args["RES_BUCKET"]
s3_bucket = args["S3_BUCKET"]
s3_prefix = args["S3_PREFIX"]
chatbot_id = args["CHATBOT_ID"]
group_name = args["GROUP_NAME"]
aos_index_name = args["INDEX_ID"]
embedding_model_type = args["EMBEDDING_MODEL_TYPE"]
chatbot_table = args["CHATBOT_TABLE"]
model_table = args["MODEL_TABLE"]
index_type = args["INDEX_TYPE"]
# Valid Operation types: "create", "delete", "update", "extract_only"
operation_type = args["OPERATION_TYPE"]
aos_secret = args.get("AOS_SECRET_NAME", "opensearch-master-user")


s3_client = boto3.client("s3")
sm_client = boto3.client("secretsmanager")
smr_client = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")
etl_object_table = dynamodb.Table(etl_object_table_name)

ENHANCE_CHUNK_SIZE = 25000
OBJECT_EXPIRY_TIME = 3600

credentials = boto3.Session().get_credentials()
MAX_OS_DOCS_PER_PUT = 8

def get_aws_auth():
    try:
        master_user = sm_client.get_secret_value(SecretId=aos_secret)[
            "SecretString"
        ]
        cred = json.loads(master_user)
        username = cred.get("username")
        password = cred.get("password")
        aws_auth = (username, password)

    except sm_client.exceptions.ResourceNotFoundException:
        aws_auth = AWS4Auth(
            refreshable_credentials=credentials, region=region, service="es"
        )
    except sm_client.exceptions.InvalidRequestException:
        logger.info(
            "InvalidRequestException. It might caused by getting secret value from a deleting secret"
        )
        logger.info("Fallback to authentication with IAM")
        aws_auth = AWS4Auth(
            refreshable_credentials=credentials, region=region, service="es"
        )
    except Exception as e:
        logger.error(f"Error retrieving secret '{aos_secret}': {str(e)}")
        raise
    return aws_auth


class S3FileIterator:
    def __init__(
        self, bucket: str, prefix: str, supported_file_types: List[str] = []
    ):
        self.bucket = bucket
        self.prefix = prefix
        self.supported_file_types = supported_file_types
        self.paginator = s3_client.get_paginator("list_objects_v2")

    def update_etl_object_table(self, processing_params: ProcessingParameters):
        """
        Update the etl object table with the processing parameters.

        Args:
            processing_params (ProcessingParameters): The processing parameters.
        """
        input_body = {
            "s3Path": f"s3://{processing_params.source_bucket_name}/{processing_params.source_object_key}",
            "s3Bucket": processing_params.source_bucket_name,
            "s3Prefix": processing_params.source_object_key,
            "executionId": table_item_id,
            "createTime": str(datetime.now(timezone.utc)),
            "status": "RUNNING",
        }
        etl_object_table.put_item(Item=input_body)

    def iterate_s3_files(self, extract_content=True) -> Generator:
        current_indice = 0
        for page in self.paginator.paginate(
            Bucket=self.bucket, Prefix=self.prefix
        ):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                file_type = key.split(".")[-1].lower()  # Extract file extension

                if (
                    key.endswith("/")
                    or file_type not in self.supported_file_types
                ):
                    continue

                if current_indice < int(batchIndice) * int(batchFileNumber):
                    current_indice += 1
                    continue
                elif current_indice >= (int(batchIndice) + 1) * int(
                    batchFileNumber
                ):
                    # Exit this nested loop
                    break
                else:
                    logger.info("Processing object: %s", key)
                    current_indice += 1

                    # For operations that don't need file content (like delete)
                    processing_params = ProcessingParameters(
                        source_bucket_name=self.bucket,
                        source_object_key=key,
                        etl_endpoint_name=etlModelEndpoint,
                        result_bucket_name=res_bucket,
                        portal_bucket_name=portal_bucket_name,
                        document_language=document_language,
                        file_type=file_type,
                    )

                    self.update_etl_object_table(processing_params)

                    yield processing_params

            if current_indice >= (int(batchIndice) + 1) * int(batchFileNumber):
                # Exit the outer loop
                break


class BatchChunkDocumentProcessor:
    """
    A class that processes documents in batches and chunks.

    Args:
        chunk_size (int): The size of each chunk.
        chunk_overlap (int): The overlap between consecutive chunks.
        batch_size (int): The size of each batch.

    Methods:
        chunk_generator(content: List[Document]) -> Generator[Document, None, None]:
            Generates chunks of documents from the given content.

        batch_generator(content: List[Document], gen_chunk_flag: bool = True):
            Generates batches of documents from the given content.

    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size

    def chunk_generator(
        self, content: List[Document]
    ) -> Generator[Document, None, None]:
        """
        Generates chunks of documents from the given content.

        Args:
            content (List[Document]): The list of documents to be chunked.

        Yields:
            Document: A chunk of a document.

        """
        temp_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        temp_content = content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        updated_heading_hierarchy = {}
        for temp_document in temp_content:
            temp_chunk_id = temp_document.metadata["chunk_id"]
            temp_split_size = len(
                temp_text_splitter.split_documents([temp_document])
            )
            # Add size in heading_hierarchy
            if "heading_hierarchy" in temp_document.metadata:
                temp_hierarchy = temp_document.metadata["heading_hierarchy"]
                temp_hierarchy["size"] = temp_split_size
                updated_heading_hierarchy[temp_chunk_id] = temp_hierarchy

        for document in content:
            splits = text_splitter.split_documents([document])
            # List of Document objects
            index = 1
            for split in splits:
                chunk_id = split.metadata["chunk_id"]
                logger.info(chunk_id)
                split.metadata["chunk_id"] = f"{chunk_id}-{index}"
                if chunk_id in updated_heading_hierarchy:
                    split.metadata["heading_hierarchy"] = (
                        updated_heading_hierarchy[chunk_id]
                    )
                    logger.info(split.metadata["heading_hierarchy"])
                index += 1
                yield split

    def batch_generator(
        self, content: List[Document], gen_chunk_flag: bool = True
    ):
        """
        Generates batches of documents from the given content.

        Args:
            content (List[Document]): The list of documents to be batched.
            gen_chunk_flag (bool, optional): Flag indicating whether to generate chunks before batching. Defaults to True.

        Yields:
            List[Document]: A batch of documents.

        """
        if gen_chunk_flag:
            generator = self.chunk_generator(content)
        else:
            generator = content
        iterator = iter(generator)
        while True:
            batch = list(itertools.islice(iterator, self.batch_size))
            if not batch:
                break
            yield batch


class BatchQueryDocumentProcessor:
    """
    A class that processes batch queries for documents.

    Args:
        docsearch (OpenSearchVectorSearch): An instance of OpenSearchVectorSearch used for document search.
        batch_size (int): The size of each batch.

    Methods:
        query_documents(s3_path): Queries documents based on the given S3 path.
        batch_generator(s3_path): Generates batches of document IDs based on the given S3 path.
    """

    def __init__(
        self,
        docsearch: OpenSearchVectorSearch,
        batch_size: int,
    ):
        self.docsearch = docsearch
        self.batch_size = batch_size

    def query_documents(self, s3_path) -> Iterable:
        """
        Queries documents based on the given S3 path.

        Args:
            s3_path (str): The S3 path to query documents from.

        Returns:
            Iterable: An iterable of document IDs.
        """
        search_body = {
            "query": {
                # use term-level queries only for fields mapped as keyword
                "prefix": {"metadata.file_path.keyword": {"value": s3_path}},
            },
            "size": 10000,
            "sort": [{"_score": {"order": "desc"}}],
            "_source": {"excludes": ["vector_field"]},
        }

        if self.docsearch.client.indices.exists(
            index=self.docsearch.index_name
        ):
            logger.info(
                "BatchQueryDocumentProcessor: Querying documents for %s",
                s3_path,
            )
            query_documents = self.docsearch.client.search(
                index=self.docsearch.index_name, body=search_body
            )
            document_ids = [
                doc["_id"] for doc in query_documents["hits"]["hits"]
            ]
            return document_ids
        else:
            logger.info(
                "BatchQueryDocumentProcessor: Index %s does not exist, skipping deletion",
                self.docsearch.index_name,
            )
            return []

    def batch_generator(self, s3_path):
        """
        Generates batches of document IDs based on the given S3 path.

        Args:
            s3_path (str): The S3 path to generate batches from.

        Yields:
            list: A batch of document IDs.
        """
        generator = self.query_documents(s3_path)
        iterator = iter(generator)
        while True:
            batch = list(itertools.islice(iterator, self.batch_size))
            if not batch:
                break
            yield batch


class OpenSearchIngestionWorker:
    def __init__(
        self,
        docsearch: OpenSearchVectorSearch,
        embedding_model_endpoint: str,
    ):
        self.docsearch = docsearch
        self.embedding_model_endpoint = embedding_model_endpoint

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def aos_ingestion(self, documents: List[Document]) -> None:
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        embeddings_vectors = self.docsearch.embedding_function.embed_documents(
            list(texts)
        )

        if isinstance(embeddings_vectors[0], dict):
            embeddings_vectors_list = []
            metadata_list = []
            for doc_id, metadata in enumerate(metadatas):
                embeddings_vectors_list.append(
                    embeddings_vectors[0]["dense_vecs"][doc_id]
                )
                metadata["embedding_endpoint_name"] = (
                    self.embedding_model_endpoint
                )
                metadata_list.append(metadata)
            embeddings_vectors = embeddings_vectors_list
            metadatas = metadata_list
        self.docsearch._OpenSearchVectorSearch__add(
            texts, embeddings_vectors, metadatas=metadatas
        )


class OpenSearchDeleteWorker:
    def __init__(self, docsearch: OpenSearchVectorSearch):
        self.docsearch = docsearch
        self.index_name = self.docsearch.index_name

    def aos_deletion(self, document_ids) -> None:
        bulk_delete_requests = []

        # Check if self.index_name exists
        if not self.docsearch.client.indices.exists(index=self.index_name):
            logger.info("Index %s does not exist", self.index_name)
            return
        else:
            for document_id in document_ids:
                bulk_delete_requests.append(
                    {"delete": {"_id": document_id, "_index": self.index_name}}
                )

            self.docsearch.client.bulk(
                index=self.index_name, body=bulk_delete_requests, refresh=True
            )
            logger.info("Deleted %d documents", len(document_ids))
            return


def ingestion_pipeline(
    s3_files_iterator,
    batch_chunk_processor,
    ingestion_worker,
    extract_only=False,
):
    for processing_params in s3_files_iterator:
        try:
            # The res is list[Document] type
            documents = process_object(processing_params)
            for document in documents:
                save_content_to_s3(
                    s3_client,
                    document,
                    processing_params.result_bucket_name,
                    SplittingType.SEMANTIC.value,
                )

            gen_chunk_flag = False if processing_params.file_type in ["csv", "xlsx", "xls"] else True
            batches = batch_chunk_processor.batch_generator(documents, gen_chunk_flag)

            for batch in batches:
                if len(batch) == 0:
                    continue

                for document in batch:
                    if "complete_heading" in document.metadata:
                        document.page_content = (
                            document.metadata["complete_heading"]
                            + " "
                            + document.page_content
                        )
                    else:
                        document.page_content = document.page_content

                    save_content_to_s3(
                        s3_client,
                        document,
                        processing_params.result_bucket_name,
                        SplittingType.CHUNK.value,
                    )

                if not extract_only:
                    ingestion_worker.aos_ingestion(batch)
        except Exception as e:
            logger.error(
                "Error processing object %s: %s",
                f"{processing_params.source_bucket_name}/{processing_params.source_object_key}",
                e,
            )
            input_body = {
                "s3Path": f"s3://{processing_params.source_bucket_name}/{processing_params.source_object_key}",
                "s3Bucket": processing_params.source_bucket_name,
                "s3Prefix": processing_params.source_object_key,
                "executionId": table_item_id,
                "createTime": str(datetime.now(timezone.utc)),
                "status": "FAILED",
                "detail": str(e),
            }
            traceback.print_exc()
        finally:
            etl_object_table.put_item(Item=input_body)


def delete_pipeline(s3_files_iterator, document_generator, delete_worker):
    for processing_params in s3_files_iterator:
        try:
            s3_path = f"s3://{processing_params.source_bucket_name}/{processing_params.source_object_key}"

            batches = document_generator.batch_generator(s3_path)
            for batch in batches:
                if len(batch) == 0:
                    continue
                delete_worker.aos_deletion(batch)

        except Exception as e:
            logger.error(
                "Error processing object %s: %s",
                f"{processing_params.source_bucket_name}/{processing_params.source_object_key}",
                e,
            )
            traceback.print_exc()


def create_processors_and_workers(
    operation_type, docsearch, embedding_model_endpoint, file_iterator
):
    """
    Create processors and workers based on the operation type.

    Args:
        operation_type (str): The type of operation to perform. Valid types are "create", "delete", "update", and "extract_only".
        docsearch: The instance of the DocSearch class.
        embedding_model_endpoint: The endpoint of the embedding model.
        file_iterator: The instance of the file processor.

    Returns:
        tuple: A tuple containing the following elements:
            - s3_files_iterator: The iterator for iterating over S3 files.
            - batch_processor: The batch processor for processing documents in chunks.
            - worker: The worker responsible for performing the operation.
    """

    if operation_type in ["create", "extract_only"]:
        s3_files_iterator = file_iterator.iterate_s3_files(
            extract_content=True
        )
        batch_processor = BatchChunkDocumentProcessor(
            chunk_size=1024, chunk_overlap=30, batch_size=10
        )
        worker = OpenSearchIngestionWorker(docsearch, embedding_model_endpoint)
    elif operation_type in ["delete", "update"]:
        s3_files_iterator = file_iterator.iterate_s3_files(
            extract_content=False
        )
        batch_processor = BatchQueryDocumentProcessor(docsearch, batch_size=10)
        worker = OpenSearchDeleteWorker(docsearch)
    else:
        raise ValueError(
            "Invalid operation type. Valid types: create, delete, update, extract_only"
        )

    return s3_files_iterator, batch_processor, worker


# Main function to be called by Glue job script
def main():
    logger.info("Starting Glue job with passing arguments: %s", args)
    logger.info(
        "Running in offline mode with consideration for large file size..."
    )

    if index_type == "qq" or index_type == "intention":
        supported_file_types = ["jsonl", "xlsx", "xls"]
    else:
        # Default is qd
        supported_file_types = [
            "pdf",
            "txt",
            "docx",
            "xlsx",
            "xls",
            "md",
            "html",
            "json",
            "csv",
            "png",
            "jpeg",
            "jpg",
            "webp",
        ]

    file_iterator = S3FileIterator(s3_bucket, s3_prefix, supported_file_types)

    if operation_type == "extract_only":
        embedding_function, docsearch = None, None
    else:
        embedding_function = sm_utils.getCustomEmbeddings(
            embedding_model_endpoint,
            region_name=region,
            bedrock_region=bedrock_region,
            model_type=embedding_model_type,
            group_name=group_name,
            chatbot_id=chatbot_id,
            model_table=model_table
        )
        aws_auth = get_aws_auth()
        docsearch = OpenSearchVectorSearch(
            index_name=aos_index_name,
            embedding_function=embedding_function,
            opensearch_url="https://{}".format(aosEndpoint),
            http_auth=aws_auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    s3_files_iterator, batch_processor, worker = create_processors_and_workers(
        operation_type, docsearch, embedding_model_endpoint, file_iterator
    )

    if operation_type == "create":
        ingestion_pipeline(s3_files_iterator, batch_processor, worker)
    elif operation_type == "extract_only":
        ingestion_pipeline(
            s3_files_iterator, batch_processor, worker, extract_only=True
        )
    elif operation_type == "delete":
        delete_pipeline(s3_files_iterator, batch_processor, worker)
    elif operation_type == "update":
        # Delete the documents first
        delete_pipeline(s3_files_iterator, batch_processor, worker)

        # Then ingest the documents
        s3_files_iterator, batch_processor, worker = (
            create_processors_and_workers(
                "create", docsearch, embedding_model_endpoint, file_iterator
            )
        )
        ingestion_pipeline(s3_files_iterator, batch_processor, worker)
    else:
        raise ValueError(
            "Invalid operation type. Valid types: create, delete, update, extract_only"
        )


if __name__ == "__main__":
    logger.info("boto3 version: %s", boto3.__version__)

    main()
