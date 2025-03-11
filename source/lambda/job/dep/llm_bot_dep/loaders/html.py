
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

import markdownify
from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader
from llm_bot_dep.figure_llm import process_markdown_images_with_llm
from llm_bot_dep.schemas.processing_parameters import (
    ProcessingParameters,
    VLLMParameters,
)
from llm_bot_dep.utils.s3_utils import (
    download_file_from_s3,
    load_content_from_file,
    parse_s3_uri,
)

logger = logging.getLogger(__name__)


class CustomHtmlLoader(BaseLoader):
    """Load `HTML` files using `Unstructured`.

    You can run the loader in one of two modes: "single" and "elements".
    If you use "single" mode, the document will be returned as a single
    langchain Document object. If you use "elements" mode, the unstructured
    library will split the document into elements such as Title and NarrativeText.
    You can pass in additional unstructured kwargs after mode to apply
    different unstructured settings.

    """

    def __init__(self, file_path: str, s3_uri: str):
        """Initialize with file path."""
        self.file_path = file_path
        self.s3_uri = s3_uri

    def clean_html(self, html_str: str) -> str:
        # Filter out DOCTYPE
        html_str = " ".join(html_str.split())
        re_doctype = re.compile(r"<!DOCTYPE .*?>", re.S)
        s = re_doctype.sub("", html_str)

        # Filter out CDATA
        re_cdata = re.compile("//<!\[CDATA\[[^>]*//\]\]>", re.I)
        s = re_cdata.sub("", s)

        # Filter out script
        re_script = re.compile("<\s*script[^>]*>[^<]*<\s*/\s*script\s*>", re.I)
        s = re_script.sub("", s)

        # Filter out style
        re_style = re.compile("<\s*style[^>]*>[^<]*<\s*/\s*style\s*>", re.I)
        s = re_style.sub("", s)

        # Filter out HTML comments
        re_comment = re.compile("<!--[^>]*-->")
        s = re_comment.sub("", s)

        # Remove extra blank lines
        blank_line = re.compile("\n+")
        s = blank_line.sub("\n", s)

        # Remove blank image
        img_src = re.compile('<img src="" />')
        s = img_src.sub("", s)

        return s.strip()

    def load(self, image_result_bucket_name: str, file_content: Optional[str] = None, vllm_params: VLLMParameters = None):
        if file_content is None:
            file_content = load_content_from_file(self.file_path)
        html_content = self.clean_html(file_content)
        # Set escape_underscores and escape_asterisks to False to avoid converting
        # underscores and asterisks to HTML entities, especially avoid converting
        # markdown links to invalid links.
        # Ref: https://pypi.org/project/markdownify/
        file_content = markdownify.markdownify(
            html_content,
            heading_style="ATX",
            escape_underscores=False,
            escape_asterisks=False,
        )
        _, object_key = parse_s3_uri(self.s3_uri)
        file_name = Path(object_key).stem
        file_content = process_markdown_images_with_llm(
            file_content, image_result_bucket_name, file_name, vllm_params
        )
        doc = Document(
            page_content=file_content,
            metadata={"file_type": "html", "file_path": self.s3_uri},
        )

        return doc


def process_html(processing_params: ProcessingParameters):
    """Process html content and split into documents.
    
    Args:
        processing_params: ProcessingParameters object containing the bucket and key
        
    Returns:
        List of processed documents.
    """
    bucket = processing_params.source_bucket_name
    key = processing_params.source_object_key
    vllm_params = processing_params.vllm_parameters
    suffix = Path(key).suffix
    
    # Create a temporary file with .html suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        local_path = temp_file.name
    
    # Download the file locally
    download_file_from_s3(bucket, key, local_path)
    
    # Use the loader with the local file path
    loader = CustomHtmlLoader(file_path=local_path, s3_uri=f"s3://{bucket}/{key}")
    doc = loader.load(image_result_bucket_name=processing_params.portal_bucket_name, vllm_params=vllm_params)
    doc_list = [doc]
    # Clean up the temporary file
    Path(local_path).unlink(missing_ok=True)

    return doc_list
