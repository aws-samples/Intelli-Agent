import json
import logging
import os

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("EXECUTION_TABLE")
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    logger.info(event)
    input_body = json.loads(event["body"])
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        for execution_id in input_body["executionId"]:
            table.update_item(
                Key={"executionId": execution_id},
                UpdateExpression="SET uiStatus = :new_status",
                ExpressionAttributeValues={":new_status": "INACTIVE"},
                ReturnValues="UPDATED_NEW"
            )
        output = {
            "message": "The deletion has completed",
            "data": input_body["executionId"]
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
