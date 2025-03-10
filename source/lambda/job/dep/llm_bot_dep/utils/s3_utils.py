import json
import logging
import os
import tempfile
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from langchain_community.document_loaders.helpers import detect_file_encodings

logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")
secrets_client = boto3.client("secretsmanager")


def load_content_from_file(file_path: str, encoding: str = "utf-8"):
    """Load content from a file.
    
    Args:
        file_path: The path to the file.
        encoding: The encoding of the file.
    """
    try:
        with open(file_path, encoding=encoding) as f:
            text = f.read()
    except UnicodeDecodeError as e:
        detected_encodings = detect_file_encodings(file_path)
        for detected_encoding in detected_encodings:
            logger.debug(f"Trying encoding: {detected_encoding.encoding}")
            try:
                with open(file_path, encoding=detected_encoding.encoding) as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError(f"Error loading {file_path}") from e
    except Exception as e:
        raise RuntimeError(f"Error loading {file_path}") from e
    
    return text


def load_content_from_s3(bucket_name, object_key, encoding="utf-8"):
    """
    Load content from an S3 object.

    Args:
        bucket_name (str): Name of the S3 bucket
        object_key (str): S3 object key
        encoding (str): Initial encoding to try

    Returns:
        str: Content of the S3 object
    """
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    content = response["Body"].read()
    
    # Try with the provided encoding first
    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        # If that fails, try to detect the encoding
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(content)
        
        decoded_content = load_content_from_file(temp_file_path)
        os.unlink(temp_file_path)
        return decoded_content


def s3_object_exists(s3_uri):
    """
    Check if an object exists at a given S3 URI.

    Args:
        s3_uri (str): S3 URI to the object (e.g., s3://bucket/folder/file.csv)

    Returns:
        bool: True if the object exists, False otherwise
    """
    bucket_name, object_key = parse_s3_uri(s3_uri)

    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            logger.error(f"Error checking S3 object existence: {e}")
            raise Exception(f"Failed to check S3 object existence: {e}")


def download_file_from_s3(bucket_name, object_key, local_path):
    """
    Download a file from S3 to a local path.

    Args:
        bucket_name (str): Name of the S3 bucket
        object_key (str): S3 object key
        local_path (str): Local file path where the object will be saved

    Returns:
        None
    """
    s3_client.download_file(bucket_name, object_key, local_path)


def upload_file_to_s3(bucket_name, object_key, local_path):
    """
    Upload a file to S3 from a local path.

    Args:
        bucket_name (str): Name of the S3 bucket
        object_key (str): S3 object key
        local_path (str): Local file path of the file to upload

    Returns:
        None
    """
    s3_client.upload_file(local_path, bucket_name, object_key)


def put_object_to_s3(bucket_name, object_key, content):
    """
    Upload content to S3.

    Args:
        bucket_name (str): Name of the S3 bucket
        object_key (str): S3 object key
        content (str): Content to upload

    Returns:
        None
    """
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=content)


def parse_s3_uri(s3_uri):
    """
    Parse an S3 URI into bucket name and object key.

    Args:
        s3_uri (str): S3 URI to parse

    Returns:
        tuple: (bucket_name, object_key)
    """
    parsed = urlparse(s3_uri)
    return parsed.netloc, parsed.path.lstrip("/")
