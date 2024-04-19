import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
execution_table = dynamodb.Table(os.environ.get('EXECUTION_TABLE'))


def lambda_handler(event, context):
    logger.info(f"event:{event}")
    if len(event["Records"]) != 1:
        raise ValueError(f"Record is not valid, it should only has 1 item, {event}")
    
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    execution_id = message["executionId"]
    map_result = message["mapResults"]
    status = "SUCCEEDED"
    for result in map_result:
        job_state = result["JobRunState"]
        # Valid value is SUCCEEDED | FAILED
        if "FAILED" == job_state:
            status = "FAILED"
            break
    response = execution_table.update_item(
        Key={"executionId": execution_id},
        UpdateExpression="SET executionStatus = :val",
        ExpressionAttributeValues={
            ':val': status
        },
        ReturnValues="UPDATED_NEW",
    )

    logger.info(f"DynamoDB update: {response}")
