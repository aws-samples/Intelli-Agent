import itertools
import json
import logging
import os
from typing import Generator, List

import boto3
import chardet
from langchain.docstore.document import Document
from utils.auto import cb_process_object

logger = logging.getLogger()
logger.setLevel(logging.INFO)

etlModelEndpoint = os.environ.get("ETL_MODEL_ENDPOINT")
region = os.environ.get("REGION")
res_bucket = os.environ.get("RES_BUCKET")

s3 = boto3.client("s3")
smr_client = boto3.client("sagemaker-runtime")


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


def iterate_s3_files(bucket: str, key: str, need_split: bool) -> Generator:
    # extract the file type from the key, e.g. llm/pdf-sample-01.pdf
    file_type = key.split(".")[-1]
    response = s3.get_object(Bucket=bucket, Key=key)
    file_content = response["Body"].read()

    # assemble bucket and key as args for the callback function
    kwargs = {
        "bucket": bucket,
        "key": key,
        "etl_model_endpoint": etlModelEndpoint,
        "smr_client": smr_client,
        "res_bucket": res_bucket,
        "need_split": need_split,
    }
    if file_type == "txt":
        yield "txt", decode_file_content(file_content), kwargs
    elif file_type == "csv":
        # Update row count here, the default row count is 1
        kwargs["csv_row_count"] = 1
        yield "csv", decode_file_content(file_content), kwargs
    elif file_type == "html":
        yield "html", decode_file_content(file_content), kwargs
    elif file_type in ["pdf"]:
        yield "pdf", file_content, kwargs
    elif file_type in ["jpg", "png"]:
        yield "image", file_content, kwargs
    elif file_type in ["docx", "doc"]:
        yield "doc", file_content, kwargs
    elif file_type == "md":
        yield "md", decode_file_content(file_content), kwargs
    elif file_type == "json":
        yield "json", decode_file_content(file_content), kwargs
    elif file_type == "jsonl":
        yield "jsonl", file_content, kwargs
    else:
        logger.info(f"Unknown file type: {file_type}")


def batch_generator(generator, batch_size: int):
    iterator = iter(generator)
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def document_to_dict(document: Document) -> dict:
    """
    Convert a Document instance to a dictionary.

    :param document: The Document instance to convert.
    :return: A dictionary representation of the Document.
    """
    return {
        "page_content": document.page_content,
        "metadata": document.metadata,
        # 'type': document.type,
    }


def serialize_documents(documents: List[Document]) -> str:
    """
    Serialize a list of Document instances to a JSON string.

    :param documents: The list of Document instances to serialize.
    :return: A JSON string representing the list of documents.
    """
    res_dicts = [document_to_dict(doc) for doc in documents]
    return json.dumps(res_dicts)


def lambda_handler(event, context):
    logger.info(f"Event: {event}")
    # get the bucket name and key from the event
    s3_bucket = json.loads(event["body"])["s3_bucket"]
    s3_prefix = json.loads(event["body"])["s3_prefix"]
    need_split = json.loads(event["body"])["need_split"]

    # Type List[List[Document]
    resp_list = []
    for file_type, file_content, kwargs in iterate_s3_files(
        s3_bucket, s3_prefix, need_split
    ):
        try:
            response = cb_process_object(s3, file_type, file_content, **kwargs)
            # for document in response:
            #     save_content_to_s3(
            #         s3, document, res_bucket, SplittingType.SEMANTIC.value
            #     )
            # logger.info(f"Response: {response} type: {type(response)}, serialize_documents: {serialize_documents(response)}")
            resp_list.append(serialize_documents(response))
        except Exception as e:
            logger.error(
                f"Error processing file: {kwargs['key']} in bucket: {kwargs['bucket']}"
            )
            logger.error(e)
            raise e
    # logger.info(f"responseList: {resp_list} type: {type(resp_list)}")
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "bucket": s3_bucket,
                "prefix": s3_prefix,
                "content": json.loads(resp_list[0]),
            }
        ),
    }
