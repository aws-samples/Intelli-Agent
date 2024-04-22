import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('EXECUTION_TABLE')
execution_table = dynamodb.Table(table_name)

def paginate_dynamodb_table(name, page_size=10, last_evaluated_key = None):
    response = dynamodb.query(
        TableName=name,
        Limit=page_size,
        ExclusiveStartKey=last_evaluated_key
    )
    items = response.get('Items', [])
    last_evaluated_key = response.get('LastEvaluatedKey')

    return items, last_evaluated_key


def lambda_handler(event, context):
    logger.info(event)
    paginate_dynamodb_table(table_name, page_size=10)

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
            "body": json.dumps(
                {}
            ),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))

        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }

