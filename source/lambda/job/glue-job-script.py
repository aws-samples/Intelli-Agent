import datetime
import itertools
import json
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import boto3
import chardet
import nltk

logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    from awsglue.utils import getResolvedOptions
    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "S3_BUCKET",
            "S3_PREFIX",
            "AOS_ENDPOINT",
            "EMBEDDING_MODEL_ENDPOINT",
            "ETL_MODEL_ENDPOINT",
            "REGION",
            "RES_BUCKET",
            "OFFLINE",
            "QA_ENHANCEMENT",
            "BATCH_INDICE",
            "ProcessedObjectsTable",
            "WORKSPACE_ID",
            "WORKSPACE_TABLE",
        ],
    )
except Exception as e:
    logger.warning("Running locally")
    sys.path.append("dep")
    args = json.load(open(sys.argv[1]))

from boto3.dynamodb.conditions import Attr, Key
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import OpenSearchVectorSearch

from llm_bot_dep import sm_utils
from llm_bot_dep.constant import SplittingType
from llm_bot_dep.ddb_utils import WorkspaceManager
from llm_bot_dep.embeddings import get_embedding_info
from llm_bot_dep.enhance_utils import EnhanceWithBedrock
from llm_bot_dep.loaders.auto import cb_process_object
from llm_bot_dep.storage_utils import save_content_to_s3
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tenacity import retry, stop_after_attempt, wait_exponential


# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers_cache"
os.environ["NOUGAT_CHECKPOINT"] = "/tmp/nougat_checkpoint"
os.environ["NLTK_DATA"] = "/tmp/nltk_data"

# Parse arguments


# Online process triggered by S3 Object create event does not have batch indice
# Set default value for BATCH_INDICE if it doesn't exist
if "BATCH_INDICE" not in args:
    args["BATCH_INDICE"] = "0"
s3_bucket = args["S3_BUCKET"]
s3_prefix = args["S3_PREFIX"]
aosEndpoint = args["AOS_ENDPOINT"]

embeddingModelEndpoint = args["EMBEDDING_MODEL_ENDPOINT"]
etlModelEndpoint = args["ETL_MODEL_ENDPOINT"]
region = args["REGION"]
res_bucket = args["RES_BUCKET"]
offline = args["OFFLINE"]
qa_enhancement = args["QA_ENHANCEMENT"]
# TODO, pass the bucket and prefix need to handle in current job directly
batchIndice = args["BATCH_INDICE"]
processedObjectsTable = args["ProcessedObjectsTable"]
workspace_id = args["WORKSPACE_ID"]
workspace_table = args["WORKSPACE_TABLE"]

s3 = boto3.client("s3")
smr_client = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(processedObjectsTable)
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)

ENHANCE_CHUNK_SIZE = 25000
# Make it 3600s for debugging purpose
OBJECT_EXPIRY_TIME = 3600

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    "es",
    session_token=credentials.token,
)
MAX_OS_DOCS_PER_PUT = 8

# Set the NLTK data path to the /tmp directory for AWS Glue jobs
nltk.data.path.append("/tmp/nltk_data")

supported_file_types = ["pdf", "txt", "doc", "md", "html", "json", "jsonl", "csv"]


def decode_file_content(content: str, default_encoding: str = "utf-8"):
    """Decode the file content and auto detect the content encoding.

    Args:
        content: The content to detect the encoding.
        default_encoding: The default encoding to try to decode the content.
        timeout: The timeout in seconds for the encoding detection.
    """

    try:
        decoded_content = content.decode(default_encoding)
    except UnicodeDecodeError:
        # Try to detect encoding
        encoding = chardet.detect(content)["encoding"]
        decoded_content = content.decode(encoding)

    return decoded_content


# such glue job is running as map job, the batchIndice is the index per file to handle in current job
def iterate_s3_files(bucket: str, prefix: str) -> Generator:
    paginator = s3.get_paginator("list_objects_v2")
    currentIndice = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # skip the prefix with slash, which is the folder name
            if key.endswith("/"):
                continue
            logger.info(
                "Current batchIndice: {}, bucket: {}, key: {}".format(
                    currentIndice, bucket, key
                )
            )
            if currentIndice != int(batchIndice):
                logger.info(
                    "currentIndice: {}, batchIndice: {}, skip file: {}".format(
                        currentIndice, batchIndice, key
                    )
                )
                currentIndice += 1
                continue

            file_type = key.split(".")[-1].lower()  # Extract file extension
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response["Body"].read()
            # assemble bucket and key as args for the callback function
            kwargs = {
                "bucket": bucket,
                "key": key,
                "etl_model_endpoint": etlModelEndpoint,
                "smr_client": smr_client,
                "res_bucket": res_bucket,
            }

            if file_type == "txt":
                yield "txt", decode_file_content(file_content), kwargs
                break
            elif file_type == "csv":
                # Update row count here, the default row count is 1
                kwargs["csv_row_count"] = 1
                yield "csv", decode_file_content(file_content), kwargs
                break
            elif file_type == "html":
                yield "html", decode_file_content(file_content), kwargs
                break
            elif file_type in ["pdf"]:
                yield "pdf", file_content, kwargs
                break
            elif file_type in ["jpg", "png"]:
                yield "image", file_content, kwargs
                break
            elif file_type in ["docx", "doc"]:
                yield "doc", file_content, kwargs
                break
            elif file_type == "md":
                yield "md", decode_file_content(file_content), kwargs
                break
            elif file_type == "json":
                yield "json", decode_file_content(file_content), kwargs
                break
            elif file_type == "jsonl":
                yield "jsonl", file_content, kwargs
                break
            else:
                logger.info(f"Unknown file type: {file_type}")


def batch_generator(generator, batch_size: int):
    iterator = iter(generator)
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def aos_injection(
    content: List[Document],
    embeddingModelEndpoint: str,
    aosEndpoint: str,
    index_name: str,
    file_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 30,
    gen_chunk: bool = True,
) -> List[Document]:
    """
    This function includes the following steps:
    1. split the document into chunks with chunk size to fit the embedding model, note the document is already splited by title/subtitle to form sementic chunks approximately;
    2. call the embedding model to get the embeddings for each chunk;
    3. call the AOS to index the chunk with the embeddings;
    Parameters:
    content (list): A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading hierarchy etc.
    embeddingModelEndpointList (List[str]): The endpoint list of the embedding model.
    aosEndpoint (str): The endpoint of the AOS.
    index_name (str): The name of the index to be created in the AOS.
    chunk_size (int): The size of each chunk to be indexed in the AOS.
    file_type (str): The file type of the document.
    gen_chunk (bool): Whether generate chunks or not.

    Returns:

    Note:
    """
    embeddings = sm_utils.create_embeddings_with_single_model(
        embeddingModelEndpoint, region, file_type
    )

    def chunk_generator(
        content: List[Document], chunk_size: int = 500, chunk_overlap: int = 30
    ) -> Generator[Document, None, None]:
        temp_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        temp_content = content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        updated_heading_hierarchy = {}
        for temp_document in temp_content:
            temp_chunk_id = temp_document.metadata["chunk_id"]
            temp_split_size = len(temp_text_splitter.split_documents([temp_document]))
            # Add size in heading_hierarchy
            if "heading_hierarchy" in temp_document.metadata:
                temp_hierarchy = temp_document.metadata["heading_hierarchy"]
                temp_hierarchy["size"] = temp_split_size
                updated_heading_hierarchy[temp_chunk_id] = temp_hierarchy

        for document in content:
            splits = text_splitter.split_documents([document])
            # list of Document objects
            index = 1
            for split in splits:
                chunk_id = split.metadata["chunk_id"]
                logger.info(chunk_id)
                split.metadata["chunk_id"] = f"{chunk_id}-{index}"
                if chunk_id in updated_heading_hierarchy:
                    split.metadata["heading_hierarchy"] = updated_heading_hierarchy[
                        chunk_id
                    ]
                    logger.info(split.metadata["heading_hierarchy"])
                index += 1
                yield split

    if gen_chunk:
        generator = chunk_generator(
            content, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    else:
        generator = content

    batches = batch_generator(generator, batch_size=10)
    # note: typeof(batch)->list[Document], sizeof(batches)=batch_size
    for batch in batches:
        if len(batch) == 0:
            continue
        # the batch are still list of Document objects, we need to iterate the list to inject the embeddings, the chunk size (500) should already be small enough to fit the embedding model
        for document in batch:
            # update document with complete_heading
            if "complete_heading" in document.metadata:
                document.page_content = (
                    document.metadata["complete_heading"] + " " + document.page_content
                )
            else:
                document.page_content = document.page_content

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
            )
            def _aos_injection(document: Document) -> Document:

                document.metadata["embedding_endpoint_name"] = embeddingModelEndpoint
                docsearch = OpenSearchVectorSearch(
                    index_name=index_name,
                    embedding_function=embeddings,
                    opensearch_url="https://{}".format(aosEndpoint),
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                )
                logger.info(
                    "Adding documents %s to OpenSearch with index %s",
                    document,
                    index_name,
                )
                # TODO: add endpoint name as a metadata of document
                try:
                    # TODO, consider the max retry and initial backoff inside helper.bulk operation instead of using original LangChain
                    docsearch.add_documents(documents=[document])
                except Exception as e:
                    logger.info(
                        f"Catch exception when adding document to OpenSearch: {e}"
                    )
                logger.info("Retry statistics: %s", _aos_injection.retry.statistics)

            # logger.info("Adding documents %s to OpenSearch with index %s", document, index_name)
            save_content_to_s3(s3, document, res_bucket, SplittingType.CHUNK.value)
            _aos_injection(document)


# Main function to be called by Glue job script
def main():
    logger.info("Starting Glue job with passing arguments: %s", args)
    logger.info("Running in offline mode with consideration for large file size...")

    embeddings_model_provider, embeddings_model_name, embeddings_model_dimensions = (
        get_embedding_info(embeddingModelEndpoint)
    )

    for file_type, file_content, kwargs in iterate_s3_files(s3_bucket, s3_prefix):
        try:
            res = cb_process_object(s3, file_type, file_content, **kwargs)
            for document in res:
                save_content_to_s3(
                    s3, document, res_bucket, SplittingType.SEMANTIC.value
                )

            # the res is unified to list[Doucment] type, store the res to S3 for observation
            # TODO, parse the metadata to embed with different index
            if res:
                logger.info("Result: %s", res)

            aos_index = workspace_manager.update_workspace_open_search(
                workspace_id,
                embeddingModelEndpoint,
                embeddings_model_provider,
                embeddings_model_name,
                embeddings_model_dimensions,
                ["zh"],
                [file_type],
            )

            gen_chunk_flag = False if file_type == "csv" else True
            if file_type in supported_file_types:
                aos_injection(
                    res,
                    embeddingModelEndpoint,
                    aosEndpoint,
                    aos_index,
                    file_type,
                    gen_chunk=gen_chunk_flag,
                )

            if qa_enhancement == "true":
                enhanced_prompt_list = []
                # iterate the document to get the QA pairs
                for document in res:
                    # Define your prompt or else it uses default prompt
                    prompt = ""
                    # Make sure the document is Document object
                    logger.info(
                        "Enhancing document type: {} and content: {}".format(
                            type(document), document
                        )
                    )
                    ewb = EnhanceWithBedrock(prompt, document)
                    # This is should be optional for the user to choose the chunk size
                    document_list = ewb.SplitDocumentByTokenNum(
                        document, ENHANCE_CHUNK_SIZE
                    )
                    for document in document_list:
                        enhanced_prompt_list = ewb.EnhanceWithClaude(
                            prompt, document, enhanced_prompt_list
                        )
                    logger.info(f"Enhanced prompt: {enhanced_prompt_list}")

                if len(enhanced_prompt_list) > 0:
                    for document in enhanced_prompt_list:
                        save_content_to_s3(
                            s3,
                            document,
                            res_bucket,
                            SplittingType.QA_ENHANCEMENT.value,
                        )
                    aos_injection(
                        enhanced_prompt_list,
                        embeddingModelEndpoint,
                        aosEndpoint,
                        aos_index,
                        "qa",
                    )

        except Exception as e:
            logger.error(
                "Error processing object %s: %s",
                kwargs["bucket"] + "/" + kwargs["key"],
                e,
            )
            traceback.print_exc()


if __name__ == "__main__":
    logger.info("boto3 version: %s", boto3.__version__)

    # Set the NLTK data path to the /tmp directory for AWS Glue jobs
    nltk.data.path.append("/tmp")
    # List of NLTK packages to download
    nltk_packages = ["words", "punkt"]
    # Download the required NLTK packages to /tmp
    for package in nltk_packages:
        # Download the package to /tmp/nltk_data
        nltk.download(package, download_dir="/tmp/nltk_data")
    main()
