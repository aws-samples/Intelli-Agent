import base64
import logging
from pathlib import Path

import boto3
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from llm_bot_dep.figure_llm import figureUnderstand, upload_image_to_s3
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter

bedrock_client = boto3.client("bedrock-runtime")
logger = logging.getLogger(__name__)


class CustomImageLoader(BaseLoader):
    """Load image file such as png, jpeg, jpg."""

    def __init__(
        self,
        s3_client,
        aws_path: str,
        file_type: str,
    ):
        """Initialize with S3 parameters."""
        self.s3_client = s3_client
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
        response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        image_bytes = response["Body"].read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        # Initialize figureUnderstand and process image
        figure_llm = figureUnderstand()
        # Using empty context and generic tag since we're processing standalone images
        understanding = figure_llm.figure_understand(img=encoded_image, context="", tag="[IMAGE]", s3_link="0.jpg")

        # Upload image directly using image_bytes
        object_key = upload_image_to_s3(image_bytes, bucket_name, file_name, "image", 0, is_bytes=True)
        understanding = understanding.replace("<link>0.jpg</link>", f"<link>{object_key}</link>")
        logger.info("Generated understanding: %s", understanding)
        metadata = {"file_path": self.aws_path, "file_type": self.file_type}

        return Document(page_content=understanding, metadata=metadata)


def process_image(s3, **kwargs):
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    portal_bucket_name = kwargs["portal_bucket_name"]
    file_type = kwargs["image_file_type"]
    file_name = Path(key).stem
    loader = CustomImageLoader(s3_client=s3, aws_path=f"s3://{bucket_name}/{key}", file_type=file_type)
    doc = loader.load(portal_bucket_name, file_name)
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
