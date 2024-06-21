import logging
from typing import Optional

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader

from .splitter_utils import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class CustomMarkdownLoader(BaseLoader):
    """Load markdown file.

    Args:
        file_content: File content in markdown file.

        encoding: File encoding to use. If `None`, the file will be loaded
        with the default system encoding.

        autodetect_encoding: Whether to try to autodetect the file encoding
            if the specified encoding fails.
    """

    def __init__(
        self,
        aws_path: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        self.aws_path = aws_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def load(self, content: str) -> Document:
        """Load from file path."""
        metadata = {"file_path": self.aws_path, "file_type": "md"}

        return Document(page_content=content, metadata=metadata)


def process_md(file_content: str, **kwargs):
    bucket = kwargs["bucket"]
    key = kwargs["key"]
    loader = CustomMarkdownLoader(aws_path=f"s3://{bucket}/{key}")
    doc = loader.load(file_content)
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
