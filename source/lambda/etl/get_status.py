import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)
state_machine_arn = os.environ["sfn_arn"]


def lambda_handler(event, context):
    execution_id = event["queryStringParameters"]["executionId"]
    sf_client = boto3.client("stepfunctions")
    execution_arn = (
        state_machine_arn.replace("stateMachine", "execution") + ":" + execution_id
    )

    try:
        response = sf_client.describe_execution(executionArn=execution_arn)

        execution_status = response["status"]
        logger.info(f"Execution Status: {execution_status}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"execution_id": execution_id, "execution_status": execution_status}
            ),
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")

        return {"statusCode": 500, "body": json.dumps(f"Error: {str(e)}")}
