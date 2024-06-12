import datetime
import json
import logging
import os
import re
import time
import uuid

import botocore
from langchain.docstore.document import Document
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
from langchain.document_loaders.pdf import BasePDFLoader
from smart_open import open as smart_open

from ..cleaning import remove_duplicate_sections
from ..splitter_utils import MarkdownHeaderTextSplitter, extract_headings
from ..storage_utils import _s3_uri_exist
from .html import CustomHtmlLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Max retry is 2 hours
_S3_FETCH_MAX_RETRY = 3600
_S3_FETCH_WAIT_TIME = 5

metadata_template = {
    "content_type": "paragraph",
    "heading_hierarchy": {},
    "figure_list": [],
    "chunk_id": "$$",
    "file_path": "",
    "keywords": [],
    "summary": "",
}


def detect_language(input):
    """
    This function detects the language of the input text. It checks if the input is a list,
    and if so, it joins the list into a single string. Then it uses a regular expression to
    search for Chinese characters in the input. If it finds any, it returns 'zh' for Chinese.
    If it doesn't find any Chinese characters, it assumes the language is English and returns 'en'.
    """
    if isinstance(input, list):
        input = " ".join(input)
    if re.search("[\u4e00-\u9fff]", input):
        return "zh"
    else:
        return "en"


def invoke_etl_model(
    s3_client: "botocore.client.S3",
    smr_client: "botocore.client.SageMakerRuntime",
    etl_model_endpoint: str,
    bucket: str,
    key: str,
    res_bucket: str,
    mode: str = "ppstructure",
    lang: str = "zh",
):
    json_data = {
        "s3_bucket": bucket,
        "object_key": key,
        "destination_bucket": res_bucket,
        "mode": mode,
        "lang": lang,
    }

    file_name = f"data_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.json"
    with open(file_name, "w") as json_file:
        json.dump(json_data, json_file)

    s3_file_path = "etl_pdf_inference/" + file_name
    # Upload the file to S3
    s3_client.upload_file(file_name, res_bucket, s3_file_path)
    logger.info(f"JSON data uploaded to S3 bucket: {res_bucket}/{s3_file_path}")

    response = smr_client.invoke_endpoint_async(
        EndpointName=etl_model_endpoint,
        ContentType="application/json",
        InputLocation=f"s3://{res_bucket}/{s3_file_path}",
    )
    logger.info("This is the async response:")
    logger.info(response)
    inference_id = response["InferenceId"]
    output_location = response["OutputLocation"]

    fetch_count = 0
    while fetch_count < _S3_FETCH_MAX_RETRY:
        if _s3_uri_exist(s3_client, output_location):
            logger.info("ETL inference completed")
            output = json.load(smart_open(output_location))

            return output["destination_prefix"]
        else:
            logger.info("Waiting for ETL output...")
            fetch_count = fetch_count + 1
            time.sleep(_S3_FETCH_WAIT_TIME)

    raise Exception(
        "Unable to fetch ETL inference result, and the number of retries reached."
    )


def load_content_from_s3(s3, bucket, key):
    """
    This function loads the content of a file from S3 and returns it as a string.
    """
    logger.info(f"Loading content from s3://{bucket}/{key}")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")


def process_pdf(s3, pdf: bytes, **kwargs):
    """
    Process a given PDF file and extracts structured information from it.

    This function reads a PDF file, converts it to HTML using PDFMiner, then extracts
    and structures the information into a list of dictionaries containing headings and content.

    Parameters:
    s3 (boto3.client): The S3 client to use for downloading the PDF file.
    pdf (bytes): The PDF file to process.
    **kwargs: Arbitrary keyword arguments. The function expects 'bucket' and 'key' among the kwargs
              to specify the S3 bucket and key where the PDF file is located.

    Returns:
    list[Document]: A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata defined in metadata_template, and page_content string with the text content of that section.
    """
    logger.info("Processing PDF file...")
    bucket = kwargs["bucket"]
    key = kwargs["key"]

    etl_model_endpoint = kwargs.get("etl_model_endpoint", None)
    smr_client = kwargs.get("smr_client", None)
    res_bucket = kwargs.get("res_bucket", None)
    # TODO: make it configurable in frontend
    document_language = kwargs.get("document_language", "zh")
    # Extract file name also in consideration of file name with blank space
    local_path = str(os.path.basename(key))
    # Download to local for further processing
    logger.info(local_path)
    s3.download_file(Bucket=bucket, Key=key, Filename=local_path)
    loader = PDFMinerPDFasHTMLLoader(local_path)
    # Entire PDF is loaded as a single Document
    file_content = loader.load()[0].page_content

    if not etl_model_endpoint or not smr_client or not res_bucket:
        logger.info(
            "No ETL model endpoint or SageMaker Runtime client provided, using default PDF loader..."
        )
        loader = CustomHtmlLoader(aws_path=f"s3://{bucket}/{key}")
        doc = loader.load(file_content)
        splitter = MarkdownHeaderTextSplitter(res_bucket)
        doc_list = splitter.split_text(doc)

        for doc in doc_list:
            doc.metadata["file_path"] = f"s3://{bucket}/{key}"
            doc.metadata["file_type"] = "pdf"
    else:
        if document_language == "zh":
            logger.info("Detected language is Chinese, using default PDF loader...")
            markdown_prefix = invoke_etl_model(
                s3,
                smr_client,
                etl_model_endpoint,
                bucket,
                key,
                res_bucket,
                mode="ppstructure",
                lang="zh",
            )
            logger.info(f"Markdown file path: s3://{res_bucket}/{markdown_prefix}")
            content = load_content_from_s3(s3, res_bucket, markdown_prefix)
        else:
            logger.info("Detected language is English, using ETL model endpoint...")
            markdown_prefix = invoke_etl_model(
                s3,
                smr_client,
                etl_model_endpoint,
                bucket,
                key,
                res_bucket,
                mode="ppstructure",
                lang="en",
            )
            logger.info(f"Markdown file path: s3://{res_bucket}/{markdown_prefix}")
            content = load_content_from_s3(s3, res_bucket, markdown_prefix)

        # Remove duplicate sections
        content = remove_duplicate_sections(content)

        metadata = {"file_path": f"s3://{bucket}/{key}", "file_type": "pdf"}

        markdown_splitter = MarkdownHeaderTextSplitter(res_bucket)
        doc_list = markdown_splitter.split_text(
            Document(page_content=content, metadata=metadata)
        )

    return doc_list
