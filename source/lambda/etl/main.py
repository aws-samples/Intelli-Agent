import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

# Offline lambda function to count the number of files in the S3 bucket
def lambda_handler(event, context):
    logger.info(f"event:{event}")
    # Retrieve bucket name and prefix from the event object passed by Step Function
    bucket_name = event['s3Bucket']
    prefix = event['s3Prefix']
    # fetch index from event with default value none
    aos_index = event['aosIndex'] if 'aosIndex' in event else None
    
    # Initialize the file count
    file_count = 0
    
    # Paginate through the list of objects in the bucket with the specified prefix
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    
    # Count the files, note skip the prefix with slash, which is the folder name
    for page in page_iterator:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('/'):
                continue
            file_count += 1
    
    # convert the fileCount into an array of numbers "fileIndices": [0, 1, 2, ..., 10], an array from 0 to fileCount-1
    batch_indices = list(range(file_count))

    # This response should match the expected input schema of the downstream tasks in the Step Functions workflow
    return {
        'fileCount': file_count,
        's3Bucket': bucket_name,
        's3Prefix': prefix,
        'qaEnhance': event['qaEnhance'].lower() if 'qaEnhance' in event else 'false',
        # boolean value to indicate if the lambda function is running in offline mode
        'offline': event['offline'].lower(),
        'batchIndices': batch_indices,
        'aosIndex': aos_index
    }
