import logging
import tempfile
from pathlib import Path
from typing import Iterator, List, Optional, Union

from langchain_community.document_loaders.text import TextLoader
from langchain_core.documents import Document
from llm_bot_dep.schemas.processing_parameters import ProcessingParameters
from llm_bot_dep.utils.s3_utils import download_file_from_s3

logger = logging.getLogger(__name__)


class CustomMarkdownLoader(TextLoader):
    """Load markdown from a file path.

    Args:
        file_path: Path to the file to load.
        s3_uri: S3 URI of the file to load.
        encoding: File encoding to use. If `None`, the file will be loaded with the default system encoding.
        autodetect_encoding: Whether to try to autodetect the file encoding if the specified encoding fails.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        s3_uri: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        super().__init__(file_path, encoding, autodetect_encoding)

    def lazy_load(self) -> Iterator[Document]:
        """Load from file path."""
        # Load from file using parent class's implementation
        for doc in super().lazy_load():
            doc.metadata = {"file_path": self.s3_uri, "file_type": "md"}
            yield doc

    def load(self) -> List[Document]:
        """Load from file path.
        
        Returns:
            List of Document objects.
        """
        return list(self.lazy_load())


def process_md(processing_params: ProcessingParameters):
    """Process text content and split into documents.
    
    Args:
        processing_params: ProcessingParameters object containing the bucket and key
        
    Returns:
        List of processed documents.
    """
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    suffix = Path(key).suffix
    
    # Create a temporary file with .md suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)
    
    # Use the loader with the local file path
    loader = CustomMarkdownLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc = loader.load()
    doc_list = [doc]
    
    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)

    return doc_list
