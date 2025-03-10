import copy
import json
import logging
import tempfile
from pathlib import Path

from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import download_file_from_s3, load_content_from_file

logger = logging.getLogger(__name__)


class CustomJsonLoader(BaseLoader):
    """Load markdown file.

    Args:
        file_path: Path to the file to load.
        s3_uri: S3 URI of the file to load.
    """

    def __init__(
        self,
        file_path: str,
        s3_uri: str,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.s3_uri = s3_uri

    def load(self):
        """Load from file path."""
        content = load_content_from_file(self.file_path)

        metadata = {"file_path": self.s3_uri, "file_type": "json"}
        doc = Document(page_content=content, metadata=metadata)

        return doc


def process_json(processing_params: ProcessingParameters):
    """Process text content and split into documents.
    
    Args:
        processing_params: ProcessingParameters object containing the bucket and key
        
    Returns:
        List of processed documents.
    """
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    suffix = Path(key).suffix
    
    # Create a temporary file with .txt suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)
    
    # Use the loader with the local file path
    loader = CustomJsonLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc = loader.load()
    doc_list = [doc]
    
    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)

    return doc_list