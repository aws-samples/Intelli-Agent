import os
import json

from main import process_pdf_pipeline
from aikits_utils import lambda_return

def handler(event, context):
    if 'body' not in event:
        return lambda_return(400, 'invalid param')
    try:
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']
        
        if 's3_bucket' not in body or 'object_key' not in body:
            return lambda_return(400, 'Must specify the `s3_bucket` and `object_key` for the file')
        
    except:
        return lambda_return(400, 'invalid param')
    
    output = process_pdf_pipeline(body)

    return lambda_return(200, json.dumps(output))