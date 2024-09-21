import logging
import xml.etree.ElementTree as ET
from typing import List, Optional

from langchain.docstore.document import Document
from langchain.document_loaders.text import TextLoader

from ..splitter_utils import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class CustomXmlLoader(TextLoader):
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

    def parse_xml_string(self, xml_string):
        """
        convert xml string to python dictionary
        """

        root = ET.fromstring(xml_string)
        result = {}
        for child in root:
            if child.text and child.text.strip():
                result[child.tag] = child.text.strip()
            else:
                result[child.tag] = None
        return result

    def load(self, text_content: str) -> List[Document]:
        """Load from file path."""
        metadata = {"file_path": self.file_path, "file_type": "xml"}
        parsed_xml = self.parse_xml_string(text_content)
        metadata["id"] = parsed_xml["id"]
        metadata["category"] = parsed_xml["category"]
        metadata["style"] = parsed_xml["style"]
        metadata["price"] = parsed_xml["price"]
        metadata["url"] = parsed_xml["url"]

        return Document(page_content=text_content, metadata=metadata)


def process_xml(file_content: str, **kwargs):
    clean_text = file_content
    bucket = kwargs["bucket"]
    key = kwargs["key"]
    loader = CustomXmlLoader(file_path=f"s3://{bucket}/{key}")
    doc = loader.load(clean_text)

    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
