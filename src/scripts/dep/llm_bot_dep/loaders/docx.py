import logging
from typing import List, Optional
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from llm_bot_dep.loaders.html import CustomHtmlLoader
import mammoth
import uuid
from datetime import datetime
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

    def load(self) -> List[Document]:
        """Load from file path."""
        metadata = {"file_path": self.file_path, "file_type": "docx"}

        def _convert_image(image):
            # Images are excluded
            return {"src": ""}
        
        with open(self.file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(_convert_image))
            html_content = result.value # The generated HTML
            loader = CustomHtmlLoader()
            doc = loader.load(html_content)
            doc.metadata = metadata

        return doc


def process_doc(s3, **kwargs):
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    bucket_name = kwargs['bucket']
    key = kwargs['key']
    local_path = f'/tmp/doc-{timestamp_str}-{random_uuid}.csv'

    s3.download_file(bucket_name, key, local_path)
    loader = CustomDocLoader(file_path=local_path)
    doc = loader.load()
    splitter = MarkdownHeaderTextSplitter()
    doc_list = splitter.split_text(doc)

    return doc_list
