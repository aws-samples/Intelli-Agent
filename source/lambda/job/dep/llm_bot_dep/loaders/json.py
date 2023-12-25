import json
import logging
from typing import List, Optional
import copy

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from ..splitter_utils import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


class CustomJsonLoader(BaseLoader):
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
        res_bucket: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
    ):
        """Initialize with file path."""
        self.aws_path = aws_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding
        self.splitter = MarkdownHeaderTextSplitter(res_bucket)

    def load(self, content: str):
        """Load from file path."""
        metadata = {
                    "content_type": "paragraph",
                    "heading_hierarchy": {},
                    "figure_list": [],
                    "chunk_id": "$$",
                    "file_path": "",
                    "keywords": [],
                    "summary": "",
                    "file_type": "json"
                }
        json_type = "repost"

        items = json.loads(content)
        document_list = []

        sample_item = items[0]
        if "source" in sample_item:
            json_type = "repost"
        elif "url" in sample_item:
            json_type = "userguide"
    
        for item in items:
            content = item['content']
            source_url = item['source'] if 'source' in item else item.get('url', 'N/A')
            source_url = source_url if isinstance(source_url, str) else "N/A"

            item_metadata = copy.deepcopy(metadata)
            item_metadata['file_path'] = source_url

            for key, values in item.items():
                if key not in ['content', 'source', 'url']:
                    item_metadata[key] = values
            
            if json_type == "userguide":
                document_list.extend(self.splitter.split_text(Document(page_content=content, metadata=item_metadata)))
            else:
                document_list.append(Document(page_content=content, metadata=item_metadata))

        return document_list


def process_json(file_content: str, **kwargs):
    bucket = kwargs['bucket']
    key = kwargs['key']
    res_bucket = kwargs['res_bucket']
    loader = CustomJsonLoader(aws_path=f"s3://{bucket}/{key}", res_bucket=res_bucket)
    raw_doc_list = loader.load(file_content)
    doc_list = []
    splitter = MarkdownHeaderTextSplitter(kwargs['res_bucket'])

    for raw_doc in raw_doc_list:
        doc_list.extend(splitter.split_text(raw_doc))

    return doc_list