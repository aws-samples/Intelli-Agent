import boto3
import sys
from awsglue.utils import getResolvedOptions

# Parse arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET', 'S3_PREFIX'])
s3_bucket = args['S3_BUCKET']
s3_prefix = args['S3_PREFIX']

def get_total_length(bucket, prefix):
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    
    total_length = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            total_length += obj['Size']
    
    return total_length

# Get the total length
print(f'Getting total length of files in {s3_bucket}/{s3_prefix}...')
total_length = get_total_length(s3_bucket, s3_prefix)

# Print the total length
print(f'Total length of files in {s3_bucket}/{s3_prefix}: {total_length} bytes')
