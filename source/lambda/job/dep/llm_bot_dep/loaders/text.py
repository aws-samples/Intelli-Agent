import logging
import re
from typing import List, Optional

from langchain.docstore.document import Document
from langchain.document_loaders.text import TextLoader

from ..splitter_utils import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class CustomTextLoader(TextLoader):
    """Load text file.

    Args:
        file_content: Text file content.

        encoding: File encoding to use. If `None`, the file will be loaded
        with the default system encoding.

        autodetect_encoding: Whether to try to autodetect the file encoding
            if the specified encoding fails.
    """

    def __init__(
        self,
        file_path: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def load(self, text_content: str) -> List[Document]:
        """Load from file path."""
        metadata = {"file_path": self.file_path, "file_type": "txt"}

        return Document(page_content=text_content, metadata=metadata)


def pre_process_text(text_content: str) -> str:
    # Clean up text content
    text_content = re.sub(r"\s+", " ", text_content)
    text_content = re.sub(r"\n+", "\n", text_content)

    return text_content.strip()


def process_text(file_content: str, **kwargs):
    clean_text = pre_process_text(file_content)
    bucket = kwargs["bucket"]
    key = kwargs["key"]
    loader = CustomTextLoader(file_path=f"s3://{bucket}/{key}")
    doc = loader.load(clean_text)

    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
