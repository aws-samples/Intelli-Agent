import logging
from typing import List, Optional

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

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
        file_path: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def load(self, content: str) -> Document:
        """Load from file path."""
        metadata = {"file_path": self.file_path, "file_type": "md"}

        return Document(page_content=content, metadata=metadata)


def process_md(file_content: str, **kwargs):
    loader = CustomMarkdownLoader(
        file_path=kwargs['bucket'] + "/" + kwargs['key'])
    doc = loader.load(file_content)
    splitter = MarkdownHeaderTextSplitter()
    doc_list = splitter.split_text(doc)

    return doc_list
