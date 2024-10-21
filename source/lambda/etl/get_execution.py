import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ETL_OBJECT_TABLE')
index_name = os.environ.get('ETL_OBJECT_INDEX')
object_table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    # API Gateway validates parameters
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        execution_id = event["pathParameters"]["executionId"]
        response = object_table.query(
            IndexName=index_name,
            KeyConditionExpression=Key('executionId').eq(execution_id)
        )
        logger.info(response)
        output = {
            "Items": response["Items"],
            "Count": response["Count"]
        }

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
