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
        file_type: str,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.aws_path = aws_path
        self.file_type = file_type

    def load(self) -> Document:
        """Load from file path."""
        import boto3
        bedrock_client = boto3.client("bedrock-runtime")
        with open(self.file_path, "rb") as image_file:
            image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        image_prompt = '''
You are a seasoned image analysis expert. Your task is to carefully observe the given illustration and proceed as follows:
1. Clearly describe the content details shown in this picture.
2. If there are any words in the picture, make sure to accurately include these words in the description.
3. If there are a table in the picture, convert it to markdown format. For example: 
| heading1 | heading2 |
| - | - |
| field1 | field2 |
'''.strip()
        if "png" == self.file_type:
            media_type = "image/png"
        elif "jpeg" == self.file_type or "jpg" == self.file_type:
            media_type = "image/jpeg"
        elif "webp" == self.file_type:
            media_type = "image/webp"
        else:
            raise ValueError("Invalid file type: " + self.file_type)
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
                                    "media_type": media_type,
                                    "data": encoded_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": image_prompt
                            },
                        ],
                    }
                ],
            }
        )
        accept = "application/json"
        contentType = "application/json"
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body,
            accept=accept,
            contentType=contentType,
        )

        response_body = json.loads(response.get("body").read())
        logger.info(response_body["content"][0]["text"])
        metadata = {"file_path": self.aws_path, "file_type": self.file_type}

        return Document(page_content=response_body["content"][0]["text"], metadata=metadata)


def process_image(s3, **kwargs):
    bucket_name = kwargs["bucket"]
    key = kwargs["key"]
    file_type = kwargs["image_file_type"]
    _, file_extension = os.path.splitext(key)
    
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    random_uuid = str(uuid.uuid4())[:8]
    local_path = f"/tmp/image-{timestamp_str}-{random_uuid}{file_extension}"

    s3.download_file(bucket_name, key, local_path)
    logger.info("File downloaded to " + local_path)
    loader = CustomImageLoader(
        file_path=local_path,
        aws_path=f"s3://{bucket_name}/{key}",
        file_type=file_type
    )
    doc = loader.load()
    splitter = MarkdownHeaderTextSplitter(kwargs["res_bucket"])
    doc_list = splitter.split_text(doc)

    return doc_list
