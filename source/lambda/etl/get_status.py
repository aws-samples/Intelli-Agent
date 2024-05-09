import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
state_machine_arn = os.environ["sfn_arn"]


def lambda_handler(event, context):
    execution_id = event["queryStringParameters"]["executionId"]
    sf_client = boto3.client("stepfunctions")
    execution_arn = (
        state_machine_arn.replace("stateMachine", "execution") + ":" + execution_id
    )

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        response = sf_client.describe_execution(executionArn=execution_arn)

        execution_status = response["status"]
        logger.info("Execution Status: %s", execution_status)

        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(
                {"execution_id": execution_id, "execution_status": execution_status}
            ),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))

        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }
