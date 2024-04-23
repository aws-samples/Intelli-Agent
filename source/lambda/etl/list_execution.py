import json
import logging
import os

import boto3
from botocore.paginate import TokenEncoder


DEFAULT_MAX_ITEM = 50
DEFAULT_SIZE = 50
logger = logging.getLogger()
logger.setLevel(logging.INFO)
client = boto3.client('dynamodb')
table_name = os.environ.get('EXECUTION_TABLE')
encoder = TokenEncoder()


def lambda_handler(event, context):
    logger.info(event)
    page_size = DEFAULT_SIZE
    max_item = DEFAULT_MAX_ITEM


    if event["queryStringParameters"] != None:
        if "size" in event["queryStringParameters"]:
            page_size = int(event["queryStringParameters"]["size"])
        
        if "total" in event["queryStringParameters"]:
            max_item = int(event["queryStringParameters"]["total"])

    config = {
        "MaxItems": max_item,
        "PageSize": page_size
    }
            
    if event["queryStringParameters"] != None and "token" in event["queryStringParameters"]:
        config["StartingToken"] = event["queryStringParameters"]["token"]
    
    # Use query after adding a filter
    paginator = client.get_paginator('scan')
    response_iterator = paginator.paginate(
        TableName=table_name,
        PaginationConfig=config
    )
    
    output = {}
    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in item.keys():
                item_json[key] = item[key]["S"]
            page_json.append(item_json)
        # Return the latest page
        output["Items"] = page_json
        output["Count"] = page["Count"]
        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode({"ExclusiveStartKey": page["LastEvaluatedKey"]})

    output["config"] = config

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))

        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }
