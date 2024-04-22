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
    logger.info(event)
    # response = object_table.get_item(
    #     Key={
    #         "executionId": ,
    #         "versionId": int(version1)
    #     })
    execution_id = event["queryStringParameters"]["executionId"]
    response = object_table.query(
        IndexName=index_name,
        KeyConditionExpression=Key('executionId').eq(execution_id)
    )
    logger.info(response["Item"])

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
