import logging
import uuid
from datetime import datetime
from typing import List, Optional

import mammoth
from docx import Document as pyDocument
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader

from llm_bot_dep.loaders.html import CustomHtmlLoader
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
        aws_path: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.aws_path = aws_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def clean_document(self, doc: pyDocument):
        """Clean document including removing header and footer for each page

        Args:
            doc (Document): The document to clean
        """
        # Remove headers and footers
        for section in doc.sections:
            if section.header is not None:
                for paragraph in section.header.paragraphs:
                    paragraph.clear()

            if section.footer is not None:
                for paragraph in section.footer.paragraphs:
                    paragraph.clear()

    def load(self) -> List[Document]:
        """Load from file path."""
        metadata = {"file_path": self.aws_path, "file_type": "docx"}

        def _convert_image(image):
            # Images are excluded
            return {"src": ""}

        pyDoc = pyDocument(self.file_path)
        self.clean_document(pyDoc)
        pyDoc.save(self.file_path)

        with open(self.file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(
                docx_file, convert_image=mammoth.images.img_element(_convert_image)
            )
            html_content = result.value
            loader = CustomHtmlLoader(aws_path=self.aws_path)
            doc = loader.load(html_content)
            doc.metadata = metadata

        return doc


def process_doc(s3, **kwargs):
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    local_path = f"/tmp/doc-{timestamp_str}-{random_uuid}.docx"

    s3.download_file(bucket_name, key, local_path)
    loader = CustomDocLoader(file_path=local_path, aws_path=f"s3://{bucket_name}/{key}")
    doc = loader.load()
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
