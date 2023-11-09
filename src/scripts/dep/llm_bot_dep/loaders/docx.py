import logging
from typing import List, Optional
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from llm_bot_dep.loaders.html import CustomHtmlLoader
import mammoth
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class CustomDocLoader(BaseLoader):
    """Load docx file.

    Args:
        file_content: File content in docx file.

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

    def load(self, content: str) -> List[Document]:
        """Load from file path."""
        metadata = {"file_path": self.file_path, "file_type": "docx"}

        def _convert_image(image):
            # Images are excluded
            return {"src": ""}

        html_content = mammoth.convert_to_html(
            content, convert_image=mammoth.images.img_element(_convert_image))
        loader = CustomHtmlLoader()
        doc = loader.load(html_content)
        doc.metadata = metadata

        return doc


def process_doc(file_content: str, **kwargs):
    loader = CustomDocLoader(file_path=kwargs['bucket'] + "/" + kwargs['key'])
    doc = loader.load(file_content)
    splitter = MarkdownHeaderTextSplitter()
    doc_list = splitter.split_text(doc)

    return doc_list
