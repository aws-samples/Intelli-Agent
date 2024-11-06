import json
import logging
import os

import boto3
from constant import ExecutionStatus, OperationType, UiStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE"))


def update_execution_item(execution_id, execution_status, ui_status):
    """
    Update the status of an execution item in DynamoDB.

    Args:
        execution_id (str): The ID of the execution to update.
        execution_status (str): The new execution status.
        ui_status (str): The new UI status.

    Returns:
        dict: The response from the DynamoDB update operation.
    """
    response = execution_table.update_item(
        Key={"executionId": execution_id},
        UpdateExpression="SET executionStatus = :execution_status, uiStatus = :ui_status",
        ExpressionAttributeValues={":execution_status": execution_status, ":ui_status": ui_status},
        ReturnValues="UPDATED_NEW",
    )
    return response


def lambda_handler(event, context):
    logger.info(f"event:{event}")
    if len(event["Records"]) != 1:
        raise ValueError(f"Record is not valid, it should only has 1 item, {event}")

    message = json.loads(event["Records"][0]["Sns"]["Message"])
    execution_id = message["executionId"]
    operation_type = message["operationType"]
    if operation_type == OperationType.DELETE.value:
        update_execution_item(execution_id, ExecutionStatus.DELETED.value, UiStatus.INACTIVE.value)
    else:
        update_execution_item(execution_id, ExecutionStatus.COMPLETED.value, UiStatus.ACTIVE.value)

    logger.info(f"DynamoDB update: {response}")
