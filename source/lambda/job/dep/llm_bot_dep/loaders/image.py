import base64
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.figure_llm import figureUnderstand
from llm_bot_dep.schemas.processing_parameters import (
    ProcessingParameters,
    VLLMParameters,
)
from llm_bot_dep.utils.s3_utils import (
    download_file_from_s3,
    parse_s3_uri,
    put_object_to_s3,
)

logger = logging.getLogger(__name__)


class CustomImageLoader(BaseLoader):
    """Load image file such as png, jpeg, jpg."""

    def __init__(
        self,
        file_path: str,
        s3_uri: str,
    ):
        """Initialize with S3 parameters."""
        self.file_path = file_path
        self.s3_uri = s3_uri

    def load(
        self, image_result_bucket_name: str, vllm_params: VLLMParameters
    ) -> Document:
        """Load directly from S3."""
        # Parse bucket and key from s3_uri
        s3_bucket, object_key = parse_s3_uri(self.s3_uri)
        file_name = Path(object_key).stem
        file_type = Path(object_key).suffix[1:]

        # Read image from file_path
        with open(self.file_path, "rb") as image_file:
            image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        # Initialize figureUnderstand and process image
        figure_llm = figureUnderstand(
            model_provider=vllm_params.model_provider,
            model_id=vllm_params.model_id,
            model_api_url=vllm_params.model_api_url,
            model_secret_name=vllm_params.model_secret_name,
            model_sagemaker_endpoint_name=vllm_params.model_sagemaker_endpoint_name,
        )
        # Using empty context and generic tag since we're processing standalone images
        understanding = figure_llm.figure_understand(
            img=encoded_image, context="", tag="[IMAGE]", s3_link="0.jpg"
        )

        # Upload image directly using image_bytes
        hour_timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        image_name = (
            f"{0:05d}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.jpg"
        )
        object_key = f"{file_name}/image/{hour_timestamp}/{image_name}"
        put_object_to_s3(image_result_bucket_name, object_key, image_bytes)
        understanding = understanding.replace(
            "<link>0.jpg</link>", f"<link>{object_key}</link>"
        )
        logger.info("Generated understanding: %s", understanding)
        metadata = {"file_path": self.s3_uri, "file_type": file_type}

        return Document(page_content=understanding, metadata=metadata)


def process_image(processing_params: ProcessingParameters):
    """Process text content and split into documents.

    Args:
        processing_params: ProcessingParameters object containing the bucket and key

    Returns:
        List of processed documents.
    """
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    vllm_params = processing_params.vllm_parameters
    suffix = Path(key).suffix

    # Create a temporary file with .txt suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name

    # Download the file locally
    download_file_from_s3(bucket, key, local_path)

    # Use the loader with the local file path
    loader = CustomImageLoader(
        file_path=local_path, s3_uri=f"s3://{bucket}/{key}"
    )
    doc = loader.load(
        image_result_bucket_name=processing_params.portal_bucket_name,
        vllm_params=vllm_params,
    )
    doc_list = [doc]
    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)

    return doc_list
