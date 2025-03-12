import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import (
    load_content_from_s3,
    parse_s3_uri,
    s3_object_exists,
    upload_file_to_s3,
)

S3_FETCH_MAX_RETRY = 3600
S3_FETCH_WAIT_TIME = 5
ETL_INFERENCE_PREFIX = "etl_image_inference/"

logger = logging.getLogger(__name__)


class SageMakerImageLoader(BaseLoader):
    """Load image file such as png, jpeg, jpg."""

    def __init__(
        self,
        etl_endpoint_name,
        source_bucket_name,
        result_bucket_name,
        portal_bucket_name,
        processing_mode="ppstructure",
        language_code="zh",
        vllm_params=None,
    ):
        """Initialize with configuration parameters.

        Args:
            etl_endpoint_name (str): Name of the ETL model endpoint
            source_bucket_name (str): Source S3 bucket containing the image
            result_bucket_name (str): Destination S3 bucket for results
            portal_bucket_name (str): Portal bucket name
            file_path (str): Local path to the image file
            s3_uri (str): S3 URI of the image file
            processing_mode (str): Processing mode (default: "ppstructure")
            language_code (str): Language code (default: "zh")
            vllm_params: VLLMParameters (optional)
        """
        self.etl_endpoint_name = etl_endpoint_name
        self.source_bucket_name = source_bucket_name
        self.result_bucket_name = result_bucket_name
        self.portal_bucket_name = portal_bucket_name
        self.processing_mode = processing_mode
        self.language_code = language_code
        self.vllm_params = vllm_params
        # Initialize clients
        self.sagemaker_runtime_client = boto3.client("sagemaker-runtime")

    def invoke_etl_model(self, source_object_key):
        """
        Invoke the ETL model endpoint to process an image file asynchronously.

        Args:
            source_object_key (str): Source S3 key of the image

        Returns:
            dict: Dictionary containing output_location, failure_location, and inference_id
        """
        # Prepare request data
        request_data = {
            "s3_bucket": self.source_bucket_name,
            "object_key": source_object_key,
            "destination_bucket": self.result_bucket_name,
            "portal_bucket": self.portal_bucket_name,
            "mode": self.processing_mode,
            "lang": self.language_code,
            "model_provider": self.vllm_params.model_provider,  # type: ignore
            "model_id": self.vllm_params.model_id,  # type: ignore
            "model_api_url": self.vllm_params.model_api_url,  # type: ignore
            "model_secret_name": self.vllm_params.model_secret_name,  # type: ignore
            "model_sagemaker_endpoint_name": self.vllm_params.model_sagemaker_endpoint_name,  # type: ignore
        }

        # Create unique filename for the request
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex
        request_filename = f"data_{timestamp}_{unique_id}.json"

        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            json.dump(request_data, temp_file)
            temp_file_path = temp_file.name

        try:
            # Upload request to S3
            request_s3_prefix = f"{ETL_INFERENCE_PREFIX}{request_filename}"
            upload_file_to_s3(
                self.result_bucket_name,
                request_s3_prefix,
                temp_file_path,
            )
            logger.info(
                f"JSON request uploaded to s3://{self.result_bucket_name}/{request_s3_prefix}"
            )

            # Invoke the endpoint asynchronously
            # Set RequestTTLSeconds to 5 hours to avoid timeout
            response = self.sagemaker_runtime_client.invoke_endpoint_async(
                EndpointName=self.etl_endpoint_name,
                ContentType="application/json",
                InputLocation=f"s3://{self.result_bucket_name}/{request_s3_prefix}",
                RequestTTLSeconds=3600 * 5,
                InvocationTimeoutSeconds=3600,
            )

            logger.info(
                f"Async inference started with ID: {response['InferenceId']}"
            )

            return {
                "output_location": response["OutputLocation"],
                "failure_location": response["FailureLocation"],
                "inference_id": response["InferenceId"],
            }
        except Exception as e:
            logger.error(f"Error invoking ETL model: {str(e)}")
            raise e
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def wait_for_async_inference_results(self, inference_response):
        """
        Wait for all ETL inference results to complete.

        Args:
            inference_results (list): List of dictionaries containing output_location,
                                     failure_location, and chunk information

        Returns:
            list: List of successful result prefixes
            list: List of failed chunk keys
        """
        inference_id = inference_response["inference_id"]
        output_location = inference_response["output_location"]
        failure_location = inference_response["failure_location"]

        for attempt in range(S3_FETCH_MAX_RETRY):

            # Check for successful completion
            if s3_object_exists(output_location):
                return {
                    "inference_id": inference_id,
                    "output_location": output_location,
                    "timeout": False,
                }

            # Check for failure
            if s3_object_exists(failure_location):
                return {
                    "inference_id": inference_id,
                    "failure_location": failure_location,
                    "timeout": False,
                }
            logger.info(
                f"Waiting for ETL inferences to complete... (attempt {attempt+1}/{S3_FETCH_MAX_RETRY})"
            )
            time.sleep(S3_FETCH_WAIT_TIME)

        # Add a return value for timeout case
        logger.error(
            f"ETL inference timed out after {S3_FETCH_MAX_RETRY} attempts"
        )
        return {
            "inference_id": inference_id,
            "timeout": True,
        }

    def get_etl_results(self, inference_result):
        """
        Get the ETL results from S3.

        Args:
            inference_result (dict): Dictionary containing inference result information

        Returns:
            str: Extracted text from the image
        """
        try:
            if inference_result.get("timeout", False):
                logger.error(f"ETL inference timed out")
                return ""
            elif inference_result.get("failure_location"):
                failure_output_bucket_name, failure_output_key = parse_s3_uri(
                    inference_result["failure_location"]
                )
                failure_output_content = load_content_from_s3(
                    failure_output_bucket_name, failure_output_key
                )
                logger.error(
                    f"ETL inference failed with error: {failure_output_content}"
                )
                return ""
            else:
                # Parse the S3 URI
                inference_output_bucket_name, inference_output_key = (
                    parse_s3_uri(inference_result["output_location"])
                )
                # Get the content from the output location
                async_inference_result = load_content_from_s3(
                    inference_output_bucket_name, inference_output_key
                )
                destination_key = json.loads(async_inference_result)[
                    "destination_prefix"
                ]

                content = load_content_from_s3(
                    self.result_bucket_name, destination_key
                )
                return content

        except Exception as e:
            logger.error(
                f"Error reading content from {inference_result.get('output_location', 'unknown')}: {str(e)}"
            )
            return ""

    def load(self, source_object_key: str) -> str:
        """
        Process an image file using the ETL model.

        Args:
            source_object_key (str): Source S3 key of the image

        Returns:
            str: Extracted text from the image
        """
        try:
            # Step 1: Invoke the ETL model
            inference_response = self.invoke_etl_model(source_object_key)

            # Step 2: Wait for the inference to complete
            inference_result = self.wait_for_async_inference_results(
                inference_response
            )

            # Step 3: Get the results
            content = self.get_etl_results(inference_result)

            return content

        except Exception as e:
            logger.error(
                f"Error processing image {source_object_key}: {str(e)}"
            )
            return ""


def process_image(processing_params: ProcessingParameters):
    """Process text content and split into documents.

    Args:
        processing_params: ProcessingParameters object containing the bucket and key

    Returns:
        List of processed documents.
    """
    # Extract required parameters
    source_bucket_name = processing_params.source_bucket_name
    source_object_key = processing_params.source_object_key

    if not source_bucket_name or not source_object_key:
        raise ValueError("Source bucket name and object key are required")

    # Extract optional parameters
    etl_endpoint_name = processing_params.etl_endpoint_name
    result_bucket_name = processing_params.result_bucket_name
    portal_bucket_name = processing_params.portal_bucket_name
    language_code = processing_params.document_language or "zh"
    vllm_params = processing_params.vllm_parameters

    # Use the loader with the local file path
    image_loader = SageMakerImageLoader(
        etl_endpoint_name=etl_endpoint_name,
        source_bucket_name=source_bucket_name,
        result_bucket_name=result_bucket_name,
        portal_bucket_name=portal_bucket_name,
        processing_mode="ppstructure",
        language_code=language_code,
        vllm_params=vllm_params,
    )
    content = image_loader.load(source_object_key)
    file_type = Path(source_object_key).suffix[1:]

    metadata = {
        "file_path": f"s3://{source_bucket_name}/{source_object_key}",
        "file_type": file_type,
    }
    doc = Document(page_content=content, metadata=metadata)

    doc_list = [doc]
    return doc_list
