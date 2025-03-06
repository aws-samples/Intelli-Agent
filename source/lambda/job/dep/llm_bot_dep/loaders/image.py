import base64
import logging
from datetime import datetime
from pathlib import Path

import boto3
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from llm_bot_dep.figure_llm import (
    figureUnderstand,
    load_content_from_s3,
    upload_image_to_s3,
)
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter
from llm_bot_dep.utils.s3_utils import put_object_to_s3

bedrock_client = boto3.client("bedrock-runtime")
logger = logging.getLogger(__name__)


class CustomImageLoader(BaseLoader):
    """Load image file such as png, jpeg, jpg."""

    def __init__(
        self,
        aws_path: str,
        file_type: str,
    ):
        """Initialize with S3 parameters."""
        self.aws_path = aws_path
        self.file_type = file_type

    def load(self, bucket_name: str, file_name: str) -> Document:
        """Load directly from S3."""
        # Parse bucket and key from aws_path
        # aws_path format: s3://bucket-name/path/to/key
        aws_path = self.aws_path.replace("s3://", "")
        path_parts = aws_path.split("/", 1)
        s3_bucket = path_parts[0]
        s3_key = path_parts[1]

        # Read image from S3
        image_bytes = load_content_from_s3(s3_bucket, s3_key).encode("utf-8")
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        # Initialize figureUnderstand and process image
        figure_llm = figureUnderstand()
        # Using empty context and generic tag since we're processing standalone images
        understanding = figure_llm.figure_understand(
            img=encoded_image, context="", tag="[IMAGE]", s3_link="0.jpg"
        )

        # Upload image directly using image_bytes
        hour_timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        image_name = (
            f"{0:05d}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.jpg"
        )
        object_key = f"{file_name}/image/{hour_timestamp}/{image_name}"
        put_object_to_s3(bucket_name, object_key, image_bytes)
        understanding = understanding.replace(
            "<link>0.jpg</link>", f"<link>{object_key}</link>"
        )
        logger.info("Generated understanding: %s", understanding)
        metadata = {"file_path": self.aws_path, "file_type": self.file_type}

        return Document(page_content=understanding, metadata=metadata)


def process_image(**kwargs):
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    portal_bucket_name = kwargs["portal_bucket_name"]
    file_type = kwargs["image_file_type"]
    file_name = Path(key).stem
    loader = CustomImageLoader(
        aws_path=f"s3://{bucket_name}/{key}", file_type=file_type
    )
    doc = loader.load(portal_bucket_name, file_name)
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
