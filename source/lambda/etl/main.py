import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

supported_file_types = ["pdf", "txt", "doc", "md", "html", "json", "jsonl", "csv"]
default_embedding_endpoint = os.environ.get("DEFAULT_EMBEDDING_ENDPOINT")


def get_job_number(event, file_count):
    job_number = event.get("JobNumber", 50)

    if file_count < job_number:
        job_number = file_count

    return job_number


# Offline lambda function to count the number of files in the S3 bucket
def lambda_handler(event, context):
    logger.info(f"event:{event}")
    # Retrieve bucket name and prefix from the event object passed by Step Function
    bucket_name = event["s3Bucket"]
    prefix = event["s3Prefix"]
    # fetch index from event with default value none
    workspace_id = event["workspaceId"]
    index_type = event.get("indexType", "qd")
    operation_type = event.get("operationType", "create")
    embedding_endpoint = event.get("embeddingEndpoint", default_embedding_endpoint)

    if "offline" not in event:
        raise ValueError("offline is not in the event")
    elif event["offline"].lower() == "true":

        # Initialize the file count
        file_count = 0

        # Paginate through the list of objects in the bucket with the specified prefix
        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        # Count the files, note skip the prefix with slash, which is the folder name
        for page in page_iterator:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                file_type = key.split(".")[-1].lower()  # Extract file extension
                if key.endswith("/") or file_type not in supported_file_types:
                    continue

                file_count += 1
        file_count = 1 if file_count == 0 else file_count
        job_number = get_job_number(event, file_count)

        batch_file_number = (file_count - 1) // job_number + 1

        # convert the fileCount into an array of numbers "fileIndices": [0, 1, 2, ..., 10], an array from 0 to fileCount-1
        batch_indices = list(range(job_number))

        # This response should match the expected input schema of the downstream tasks in the Step Functions workflow
        return {
            "s3Bucket": bucket_name,
            "s3Prefix": prefix,
            "fileCount": file_count,
            "workspaceId": workspace_id,
            "qaEnhance": (
                event["qaEnhance"].lower() if "qaEnhance" in event else "false"
            ),
            "offline": event["offline"].lower(),
            "batchFileNumber": str(batch_file_number),
            "batchIndices": batch_indices,
            "indexType": index_type,
            "operationType": operation_type,
            "embeddingEndpoint": embedding_endpoint,
        }
    elif event["offline"].lower() == "false":
        # This response should match the expected input schema of the downstream tasks in the Step Functions workflow
        return {
            "s3Bucket": bucket_name,
            "s3Prefix": prefix,
            "fileCount": "1",
            "workspaceId": workspace_id,
            "qaEnhance": (
                event["qaEnhance"].lower() if "qaEnhance" in event else "false"
            ),
            "offline": "false",
            "batchFileNumber": "1",
            "batchIndices": "0",
            "indexType": index_type,
            "operationType": operation_type,
            "embeddingEndpoint": embedding_endpoint,
        }
    else:
        raise ValueError("offline is not true or false")
