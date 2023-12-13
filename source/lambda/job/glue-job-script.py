import itertools
import logging
import os
import sys
import time
import json
import datetime
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import boto3
import chardet
import nltk
from awsglue.utils import getResolvedOptions
from boto3.dynamodb.conditions import Attr, Key
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import OpenSearchVectorSearch
from llm_bot_dep import sm_utils
from llm_bot_dep.enhance_utils import EnhanceWithBedrock
from llm_bot_dep.loaders.auto import cb_process_object
from opensearchpy import RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from llm_bot_dep.storage_utils import save_content_to_s3
from llm_bot_dep.constant import SplittingType
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Adaption to allow nougat to run in AWS Glue with writable /tmp
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers_cache"
os.environ["NOUGAT_CHECKPOINT"] = "/tmp/nougat_checkpoint"
os.environ["NLTK_DATA"] = "/tmp/nltk_data"

# Parse arguments
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
        "DOC_INDEX_TABLE",
        "AOS_INDEX",
        "CONTENT_TYPE",
        "EMBEDDING_TYPE",
        "EMBEDDING_LANG"
    ],
)

# Online process triggered by S3 Object create event does not have batch indice
# Set default value for BATCH_INDICE if it doesn't exist
if "BATCH_INDICE" not in args:
    args["BATCH_INDICE"] = "0"
s3_bucket = args["S3_BUCKET"]
s3_prefix = args["S3_PREFIX"]
aosEndpoint = args["AOS_ENDPOINT"]
aos_index = args["DOC_INDEX_TABLE"]
# This index is used for the AOS injection, to allow user customize the index, otherwise default value is "chatbot-index" or set in CloudFormation parameter
aos_custom_index = args["AOS_INDEX"]
embeddingModelEndpoint = args["EMBEDDING_MODEL_ENDPOINT"]
etlModelEndpoint = args["ETL_MODEL_ENDPOINT"]
region = args["REGION"]
res_bucket = args["RES_BUCKET"]
offline = args["OFFLINE"]
qa_enhancement = args["QA_ENHANCEMENT"]
# TODO, pass the bucket and prefix need to handle in current job directly
batchIndice = args["BATCH_INDICE"]
processedObjectsTable = args["ProcessedObjectsTable"]
content_type = args["CONTENT_TYPE"]
_embedding_endpoint_name_list = args["EMBEDDING_MODEL_ENDPOINT"].split(",")
_embedding_lang_list = args["EMBEDDING_LANG"].split(",")
_embedding_type_list = args["EMBEDDING_TYPE"].split(",")
embeddings_model_info_list = []
for endpoint_name, lang, endpoint_type in zip(
    _embedding_endpoint_name_list, _embedding_lang_list, _embedding_type_list
):
    embeddings_model_info_list.append(
        {"endpoint_name": endpoint_name, "lang": lang, "type": endpoint_type}
    )

s3 = boto3.client("s3")
smr_client = boto3.client("sagemaker-runtime")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(processedObjectsTable)

ENHANCE_CHUNK_SIZE = 500
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
            logger.info("Current batchIndice: {}, bucket: {}, key: {}".format(currentIndice, bucket, key))
            if currentIndice != int(batchIndice):
                logger.info(
                    "currentIndice: {}, batchIndice: {}, skip file: {}".format(
                        currentIndice, batchIndice, key
                    )
                )
                currentIndice += 1
                continue

            # # Truncate to seconds with round()
            # current_time = int(round(time.time()))
            # # Check for redundancy and expiry
            # response = table.query(
            #     KeyConditionExpression=Key("ObjectKey").eq(key),
            #     ScanIndexForward=False,  # Sort by ProcessTimestamp in descending order
            #     Limit=1,  # We only need the latest record
            # )

            # # If the object is found and has not expired, skip processing
            # if (
            #     response["Items"]
            #     and response["Items"][0]["ExpiryTimestamp"] > current_time
            # ):
            #     logger.info(f"Object {key} has not expired yet and will be skipped.")
            #     continue

            # # Record the processing of the S3 object with an updated expiry timestamp, and each job only update single object in table. TODO, current assume the object will be handled successfully
            # expiry_timestamp = current_time + OBJECT_EXPIRY_TIME
            # try:
            #     table.put_item(
            #         Item={
            #             "ObjectKey": key,
            #             "ProcessTimestamp": current_time,
            #             "Bucket": bucket,
            #             "Prefix": "/".join(key.split("/")[:-1]),
            #             "ExpiryTimestamp": expiry_timestamp,
            #         }
            #     )
            # except Exception as e:
            #     logger.error(f"Error recording processed of S3 object {key}: {e}")

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
    chunk_size: int = 500,
    gen_chunk: bool = True,
) -> List[Document]:
    """
    This function includes the following steps:
    1. split the document into chunks with chunk size to fit the embedding model, note the document is already splited by title/subtitle to form sementic chunks approximately;
    2. call the embedding model to get the embeddings for each chunk;
    3. call the AOS to index the chunk with the embeddings;
    Parameters:
    content (list): A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata dictionary with details about the heading hierarchy etc.
    embeddingModelEndpoint (str): The endpoint of the embedding model.
    aosEndpoint (str): The endpoint of the AOS.
    index_name (str): The name of the index to be created in the AOS.
    chunk_size (int): The size of each chunk to be indexed in the AOS.
    gen_chunk (bool): Whether generate chunks or not.

    Returns:

    Note:
    """
    embeddings = sm_utils.create_sagemaker_embeddings_from_js_model(
        embeddingModelEndpoint, region
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
        generator = chunk_generator(content, chunk_size=chunk_size)
    else:
        generator = content

    batches = batch_generator(generator, batch_size=10)
    # note: typeof(batch)->list[Document], sizeof(batches)=batch_size
    for batch in batches:
        if len(batch) == 0:
            continue
        # the batch are still list of Document objects, we need to iterate the list to inject the embeddings, the chunk size (500) should already be small enough to fit the embedding model
        for document in batch:

            @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
            def _aos_injection(document: Document) -> Document:
                # if user customize the index, use the customized index as high priority, NOTE the custom index will be created with default AOS mapping in LangChain, use API to create the index with customized mapping before running the job if you want to customize the mapping
                if aos_custom_index:
                    index_name = aos_custom_index
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
    # Check if offline mode
    if offline == "true" or offline == "false":
        logger.info("Running in offline mode with consideration for large file size...")
        for file_type, file_content, kwargs in iterate_s3_files(s3_bucket, s3_prefix):
            try:
                if file_type == "json":
                    kwargs["embeddings_model_info_list"] = embeddings_model_info_list
                    kwargs["aos_index"] = aos_index
                    kwargs["aosEndpoint"] = aosEndpoint
                    kwargs["region"] = region
                    kwargs["awsauth"] = awsauth
                    kwargs["content_type"] = content_type
                    kwargs["max_os_docs_per_put"] = MAX_OS_DOCS_PER_PUT
                res = cb_process_object(s3, file_type, file_content, **kwargs)
                for document in res:
                    save_content_to_s3(
                        s3, document, res_bucket, SplittingType.SEMANTIC.value
                    )

                # the res is unified to list[Doucment] type, store the res to S3 for observation
                # TODO, parse the metadata to embed with different index
                if res:
                    logger.info("Result: %s", res)
                if file_type == "csv":
                    # CSV page document has been splited into chunk, no more spliting is needed
                    aos_injection(
                        res,
                        embeddingModelEndpoint,
                        aosEndpoint,
                        aos_index,
                        gen_chunk=False,
                    )
                elif file_type in ["pdf", "txt", "doc", "md", "html"]:
                    aos_injection(res, embeddingModelEndpoint, aosEndpoint, aos_index)

                if qa_enhancement == "true":
                    # iterate the document to get the QA pairs
                    for document in res:
                        # prompt is not used in this case
                        prompt = ""
                        solution_title = "GCR Solution LLM Bot"
                        # Make sure the document is Document object
                        logger.info(
                            "Enhancing document type: {} and content: {}".format(
                                type(document), document
                            )
                        )
                        ewb = EnhanceWithBedrock(prompt, solution_title, document)
                        # This is should be optional for the user to choose the chunk size
                        document_list = ewb.SplitDocumentByTokenNum(
                            document, ENHANCE_CHUNK_SIZE
                        )
                        # enhanced_prompt_list = []
                        for document in document_list:
                            enhanced_prompt = ewb.EnhanceWithClaude(
                                prompt, solution_title, document
                            )
                            logger.info(
                                "Enhanced prompt: {}".format(enhanced_prompt)
                            )
                            # enhanced_prompt_list.append(enhanced_prompt)

                        # aos_injection(
                        #     enhanced_prompt_list,
                        #     embeddingModelEndpoint,
                        #     aosEndpoint,
                        #     aos_index,
                        #     gen_chunk=False,
                        # )



            except Exception as e:
                logger.error(
                    "Error processing object %s: %s",
                    kwargs["bucket"] + "/" + kwargs["key"],
                    e,
                )
    else:
        logger.info("Running in online mode, assume file number is small...")


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
