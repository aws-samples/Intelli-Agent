import logging
from typing import List, Optional
import uuid
from datetime import datetime
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
import json
from llm_bot_dep.splitter_utils import MarkdownHeaderTextSplitter
import boto3
import base64
import os


bedrock_client = boto3.client("bedrock-runtime")
logger = logging.getLogger(__name__)


class CustomImageLoader(BaseLoader):
    """Load image file such as png, jpeg, jpg."""

    def __init__(
        self,
        file_path: str,
        aws_path: str,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.aws_path = aws_path

    def load(self) -> Document:
        """Load from file path."""
        with open(self.file_path, "rb") as image_file:
            image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": encoded_image,
                                },
                            },
                            {"type": "text", "text": "What is in this image?"},
                        ],
                    }
                ],
            }
        )

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body
        )

        response_body = json.loads(response.get("body").read())

        print(response_body['content'][0]['text'])
        metadata = {"file_path": self.aws_path, "file_type": "md"}

        return Document(page_content=response_body, metadata=metadata)


def process_image(s3, **kwargs):
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    _, file_extension = os.path.splitext(key)
    
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    local_path = f"/tmp/image-{timestamp_str}-{random_uuid}{file_extension}"

    s3.download_file(bucket_name, key, local_path)
    loader = CustomImageLoader(file_path=local_path, aws_path=f"s3://{bucket}/{key}")
    doc = loader.load()
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
