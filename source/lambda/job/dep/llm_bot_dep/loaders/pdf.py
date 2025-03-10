import datetime
import json
import logging
import os
import re
import tempfile
import time
import uuid
from urllib.parse import urlparse

import boto3
import botocore
from botocore.exceptions import ClientError
from langchain.docstore.document import Document
from pypdf import PdfReader, PdfWriter
from smart_open import open as smart_open

from ..cleaning import remove_duplicate_sections
from ..splitter_utils import MarkdownHeaderTextSplitter
from ..storage_utils import _s3_uri_exist
from .html import CustomHtmlLoader

logger = logging.getLogger(__name__)
# Configure logger to display messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

S3_FETCH_MAX_RETRY = 3600
S3_FETCH_WAIT_TIME = 5
ETL_INFERENCE_PREFIX = "etl_pdf_inference/"

# Maximum pages per chunk for PDF splitting
PDF_CHUNK_SIZE = 100
# Maximum retries for failed chunks
MAX_CHUNK_RETRIES = 3


class SageMakerPdfLoader:
    """
    A class to handle loading and processing PDFs using SageMaker ETL endpoints.

    This class encapsulates the functionality for processing PDFs, including:
    - Splitting large PDFs into manageable chunks
    - Invoking SageMaker endpoints for ETL processing
    - Tracking and waiting for asynchronous inference results
    - Merging results from multiple chunks
    """

    def __init__(
        self,
        etl_endpoint_name,
        source_bucket_name,
        result_bucket_name,
        portal_bucket_name,
        processing_mode="ppstructure",
        language_code="zh",
        chunk_size=PDF_CHUNK_SIZE,
        s3_client=None,
        sagemaker_runtime_client=None,
    ):
        """
        Initialize the SageMakerPdfLoader with configuration parameters.

        Args:
            etl_endpoint_name (str): Name of the ETL model endpoint
            source_bucket_name (str): Source S3 bucket containing the PDF
            result_bucket_name (str): Destination S3 bucket for results
            portal_bucket_name (str): Portal bucket name
            processing_mode (str): Processing mode (default: "ppstructure")
            language_code (str): Language code (default: "zh")
            chunk_size (int): Maximum pages per chunk (default: PDF_CHUNK_SIZE)
            s3_client: Boto3 S3 client (optional)
            sagemaker_runtime_client: Boto3 SageMaker Runtime client (optional)
        """
        self.etl_endpoint_name = etl_endpoint_name
        self.source_bucket_name = source_bucket_name
        self.result_bucket_name = result_bucket_name
        self.portal_bucket_name = portal_bucket_name
        self.processing_mode = processing_mode
        self.language_code = language_code
        self.chunk_size = chunk_size

        # Initialize clients if not provided
        self.s3_client = s3_client or boto3.client("s3")
        self.sagemaker_runtime_client = (
            sagemaker_runtime_client
            or boto3.client("sagemaker-runtime", region_name="us-east-1")
        )

    def load_content_from_s3(self, s3_bucket, object_key):
        """
        Load content from an S3 object.

        Args:
            object_key (str): S3 object key

        Returns:
            str: Content of the S3 object
        """
        response = self.s3_client.get_object(Bucket=s3_bucket, Key=object_key)
        return response["Body"].read().decode("utf-8")

    def _s3_uri_exist(self, s3_uri: str) -> bool:
        """
        Checks if an object exists at a given S3 URI.
        eg. s3://bucket/folder/file.csv

        Args:
            s3_uri: s3 URI to the s3 object

        Returns:
            bool: whether the object exists or not
        """
        parsed = urlparse(s3_uri)

        try:
            self.s3_client.head_object(
                Bucket=parsed.netloc, Key=parsed.path.lstrip("/")
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise Exception("Failed to get S3 object during ETL inference")

    def split_pdf(self, source_key):
        """
        Split a large PDF into smaller chunks.

        Args:
            source_key (str): Source S3 key of the PDF

        Returns:
            list: List of tuples containing (temp_file_path, start_page, end_page) for each chunk
            str: Path to temporary directory containing chunks
        """
        logger.info(
            f"Splitting PDF from s3://{self.source_bucket_name}/{source_key}"
        )

        # Create a temporary directory to store PDF chunks
        temp_dir = tempfile.mkdtemp()

        # Download the PDF file
        local_pdf_path = os.path.join(temp_dir, os.path.basename(source_key))
        self.s3_client.download_file(
            self.source_bucket_name, source_key, local_pdf_path
        )

        # Open the PDF
        pdf = PdfReader(local_pdf_path)
        total_pages = len(pdf.pages)
        logger.info(
            f"PDF has {total_pages} pages, splitting into chunks of {self.chunk_size} pages"
        )

        chunks = []
        for i in range(0, total_pages, self.chunk_size):
            start_page = i
            end_page = min(i + self.chunk_size - 1, total_pages - 1)

            # Create a new PDF with the chunk of pages
            pdf_writer = PdfWriter()
            for page_num in range(start_page, end_page + 1):
                pdf_writer.add_page(pdf.pages[page_num])

            # Save the chunk
            chunk_filename = f"{os.path.splitext(os.path.basename(source_key))[0]}_chunk_{start_page+1}_{end_page+1}.pdf"
            chunk_path = os.path.join(temp_dir, chunk_filename)
            with open(chunk_path, "wb") as chunk_file:
                pdf_writer.write(chunk_file)

            chunks.append((chunk_path, start_page, end_page))
            logger.info(
                f"Created chunk {chunk_path} with pages {start_page+1}-{end_page+1}"
            )

        return chunks, temp_dir

    def upload_pdf_chunk(self, local_path, prefix):
        """
        Upload a PDF chunk to S3.

        Args:
            local_path (str): Local path to the PDF chunk
            prefix (str): S3 prefix for the chunk

        Returns:
            str: S3 key of the uploaded chunk
        """
        chunk_key = f"{prefix}{os.path.basename(local_path)}"
        self.s3_client.upload_file(
            local_path, self.result_bucket_name, chunk_key
        )
        logger.info(
            f"Uploaded chunk to s3://{self.result_bucket_name}/{chunk_key}"
        )
        return chunk_key

    def invoke_etl_model(self, source_object_key, source_bucket=None):
        """
        Invoke the ETL model endpoint to process a PDF file asynchronously.

        Args:
            source_object_key (str): Source S3 key of the PDF
            source_bucket (str, optional): Override the default source bucket

        Returns:
            dict: Dictionary containing output_location, failure_location, and inference_id
        """
        # Use provided source bucket or default
        bucket = (
            source_bucket
            if source_bucket is not None
            else self.source_bucket_name
        )

        # Prepare request data
        request_data = {
            "s3_bucket": bucket,
            "object_key": source_object_key,
            "destination_bucket": self.result_bucket_name,
            "portal_bucket": self.portal_bucket_name,
            "mode": self.processing_mode,
            "lang": self.language_code,
        }

        # Create unique filename for the request
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex
        request_filename = f"data_{timestamp}_{unique_id}.json"

        # Save request data locally
        with open(request_filename, "w") as json_file:
            json.dump(request_data, json_file)

        # Upload request to S3
        request_s3_path = f"{ETL_INFERENCE_PREFIX}{request_filename}"
        self.s3_client.upload_file(
            request_filename, self.result_bucket_name, request_s3_path
        )
        logger.info(
            f"JSON request uploaded to s3://{self.result_bucket_name}/{request_s3_path}"
        )

        # Invoke the endpoint asynchronously
        response = self.sagemaker_runtime_client.invoke_endpoint_async(
            EndpointName=self.etl_endpoint_name,
            ContentType="application/json",
            InputLocation=f"s3://{self.result_bucket_name}/{request_s3_path}",
            RequestTTLSeconds=3600,
            InvocationTimeoutSeconds=3600,
        )

        logger.info(
            f"Async inference started with ID: {response['InferenceId']}"
        )

        # Clean up local request file
        os.remove(request_filename)

        return {
            "output_location": response["OutputLocation"],
            "failure_location": response["FailureLocation"],
            "inference_id": response["InferenceId"],
        }

    def wait_for_async_inference_results(self, inference_results):
        """
        Wait for all ETL inference results to complete.

        Args:
            inference_results (list): List of dictionaries containing output_location,
                                     failure_location, and chunk information

        Returns:
            list: List of successful result prefixes
            list: List of failed chunk keys
        """
        successful_chunks = []
        failed_chunks = []
        pending_inferences = inference_results.copy()

        for attempt in range(S3_FETCH_MAX_RETRY):
            if not pending_inferences:
                logger.info("All ETL inferences completed")
                break

            remaining_inferences = []

            for inference in pending_inferences:
                chunk_key = inference["chunk_key"]
                output_location = inference["output_location"]
                failure_location = inference["failure_location"]

                # Check for successful completion
                if self._s3_uri_exist(output_location):
                    logger.info(
                        f"ETL inference for chunk {chunk_key} completed successfully"
                    )
                    successful_chunks.append(
                        {
                            "chunk_key": chunk_key,
                            "output_location": output_location,
                        }
                    )
                    continue

                # Check for failure
                if self._s3_uri_exist(failure_location):
                    logger.error(f"ETL inference for chunk {chunk_key} failed")
                    failed_chunks.append(
                        {
                            "chunk_key": chunk_key,
                            "failure_location": failure_location,
                        }
                    )
                    continue

                # Still pending
                remaining_inferences.append(inference)

            # Update pending inferences
            pending_inferences = remaining_inferences

            if pending_inferences:
                logger.info(
                    f"Waiting for {len(pending_inferences)} ETL inferences to complete... (attempt {attempt+1}/{S3_FETCH_MAX_RETRY})"
                )
                time.sleep(S3_FETCH_WAIT_TIME)

        # Check if any inferences are still pending after max retries
        if pending_inferences:
            logger.error(
                f"{len(pending_inferences)} ETL inferences timed out after maximum retries"
            )
            for inference in pending_inferences:
                failed_chunks.append(
                    {
                        "chunk_key": inference["chunk_key"],
                        "failure_location": inference["failure_location"],
                    }
                )

        return successful_chunks, failed_chunks

    def merge_etl_results(self, successful_chunks):
        """
        Merge ETL results from multiple chunks.

        Args:
            successful_chunks (list): List of successful chunks with output locations

        Returns:
            str: S3 prefix of the merged result
        """
        logger.info(f"Merging results from {len(successful_chunks)} chunks")

        # Sort chunks by starting page number
        sorted_chunks = []
        for chunk in successful_chunks:
            chunk_key = chunk["chunk_key"]
            # Extract page numbers from chunk key (format: prefix/filename_chunk_START_END.pdf)
            parts = os.path.basename(chunk_key).split("_")
            if len(parts) >= 3:
                try:
                    start_page = int(parts[-2])  # Get the start page number
                    sorted_chunks.append((start_page, chunk))
                except ValueError:
                    logger.warning(
                        f"Could not parse start page from chunk key: {chunk_key}"
                    )
                    sorted_chunks.append(
                        (float("inf"), chunk)
                    )  # Put at the end if can't parse
            else:
                logger.warning(f"Unexpected chunk key format: {chunk_key}")
                sorted_chunks.append(
                    (float("inf"), chunk)
                )  # Put at the end if can't parse

        # Sort by start page
        sorted_chunks.sort(key=lambda x: x[0])

        # Get the original key from the first chunk's key
        chunk_key = (
            successful_chunks[0]["chunk_key"] if successful_chunks else ""
        )

        # Concatenate all extracted text
        all_text = ""

        # Process each chunk in order
        for _, chunk in sorted_chunks:
            output_location = chunk["output_location"]

            # Parse the S3 URI
            parsed_uri = urlparse(output_location)
            bucket_name = parsed_uri.netloc
            key = parsed_uri.path.lstrip("/")

            try:
                # Get the content from the output location
                async_inference_result = self.load_content_from_s3(
                    bucket_name, key
                )
                destination_key = json.loads(async_inference_result)[
                    "destination_prefix"
                ]

                pdf_chunk_content = self.load_content_from_s3(
                    self.result_bucket_name, destination_key
                )

                # Append the content to our combined text
                all_text += pdf_chunk_content + "\n\n"
                logger.info(f"Added content from {output_location}")
            except Exception as e:
                logger.error(
                    f"Error reading content from {output_location}: {str(e)}"
                )

        return all_text

    def process_large_pdf(self, source_object_key):
        """
        Process a large PDF by splitting it into chunks, processing each chunk in parallel,
        and merging the results.

        Args:
            source_object_key (str): Source S3 key of the PDF

        Returns:
            str: S3 prefix of the merged result

        Raises:
            Exception: If processing fails for all chunks
        """
        # Split the PDF into chunks
        chunks, temp_dir = self.split_pdf(source_object_key)
        local_pdf_path = os.path.join(
            temp_dir, os.path.basename(source_object_key)
        )

        try:
            # Upload chunks to S3
            chunk_prefix = f"{ETL_INFERENCE_PREFIX}chunks/{os.path.splitext(os.path.basename(source_object_key))[0]}/"
            chunk_keys = []

            for chunk_path, _, _ in chunks:
                chunk_key = self.upload_pdf_chunk(chunk_path, chunk_prefix)
                chunk_keys.append(chunk_key)

            # Submit all chunks for processing asynchronously
            inference_results = []

            for chunk_key in chunk_keys:
                logger.info(f"Submitting chunk {chunk_key} for processing")
                inference_result = self.invoke_etl_model(
                    chunk_key,
                    source_bucket=self.result_bucket_name,  # Use destination bucket as source for chunks
                )
                inference_results.append(
                    {
                        "chunk_key": chunk_key,
                        "output_location": inference_result["output_location"],
                        "failure_location": inference_result[
                            "failure_location"
                        ],
                        "inference_id": inference_result["inference_id"],
                    }
                )

            # Wait for all inferences to complete
            successful_chunks, failed_chunks = (
                self.wait_for_async_inference_results(inference_results)
            )

            # Check if we have any successful results
            if not successful_chunks:
                raise Exception("All PDF chunks failed processing")

            # Log any failed chunks
            if failed_chunks:
                logger.warning(
                    f"{len(failed_chunks)} out of {len(chunk_keys)} chunks failed processing"
                )

            # Merge results from successful chunks
            all_text = self.merge_etl_results(successful_chunks)

            return all_text

        finally:
            # Clean up temporary files
            for chunk_path, _, _ in chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

            # Also remove the original downloaded PDF file
            if os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)

            # Use shutil.rmtree for safer directory removal
            import shutil

            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def process_pdf(s3_client, pdf_content: bytes, **kwargs):
    """
    Process a PDF file and extract structured information.

    Args:
        s3_client: Boto3 S3 client
        pdf_content (bytes): PDF content (not used in current implementation)
        **kwargs: Additional parameters including:
            - source_bucket_name: S3 bucket containing the PDF
            - source_object_key: S3 key of the PDF
            - etl_endpoint_name: Optional ETL model endpoint
            - sagemaker_runtime_client: Optional SageMaker Runtime client
            - result_bucket_name: Optional result bucket
            - portal_bucket_name: Optional portal bucket name
            - language_code: Optional document language (default: 'zh')

    Returns:
        list: List of Document objects representing the processed PDF
    """
    logger.info("Processing PDF file...")

    # Extract required parameters
    source_bucket_name = kwargs.get("bucket") or kwargs.get(
        "source_bucket_name"
    )
    source_object_key = kwargs.get("key") or kwargs.get("source_object_key")

    if not source_bucket_name or not source_object_key:
        raise ValueError("Source bucket name and object key are required")

    # Extract optional parameters
    etl_endpoint_name = kwargs.get("etl_model_endpoint") or kwargs.get(
        "etl_endpoint_name"
    )
    sagemaker_runtime_client = kwargs.get("smr_client") or kwargs.get(
        "sagemaker_runtime_client"
    )
    result_bucket_name = kwargs.get("res_bucket") or kwargs.get(
        "result_bucket_name"
    )
    portal_bucket_name = kwargs.get("portal_bucket_name")
    language_code = kwargs.get("document_language") or kwargs.get(
        "language_code", "zh"
    )

    pdf_loader = SageMakerPdfLoader(
        etl_endpoint_name=etl_endpoint_name,
        source_bucket_name=source_bucket_name,
        result_bucket_name=result_bucket_name,
        portal_bucket_name=portal_bucket_name,
        processing_mode="ppstructure",
        language_code=language_code,
        chunk_size=PDF_CHUNK_SIZE,
        s3_client=s3_client,
        sagemaker_runtime_client=sagemaker_runtime_client,
    )

    content = pdf_loader.process_large_pdf(source_object_key)

    metadata = {
        "file_path": f"s3://{source_bucket_name}/{source_object_key}",
        "file_type": "pdf",
    }
    document = Document(page_content=content, metadata=metadata)

    # Split document into chunks
    markdown_splitter = MarkdownHeaderTextSplitter(result_bucket_name)
    return markdown_splitter.split_text(document)
