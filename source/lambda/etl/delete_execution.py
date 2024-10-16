"""
Lambda function for deleting execution pipelines and associated documents.

This module handles the deletion of execution pipelines and their corresponding
documents from OpenSearch. It interacts with DynamoDB and Step Functions to
manage the deletion process.
"""

import json
import logging
import os

import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sfn_client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")

# Get environment variables
sfn_arn = os.environ.get("SFN_ARN")
table_name = os.environ.get("EXECUTION_TABLE")
table = dynamodb.Table(table_name)


def get_execution_item(execution_id):
    """
    Retrieve an execution item from DynamoDB.

    Args:
        execution_id (str): The ID of the execution to retrieve.

    Returns:
        dict: The execution item if found, None otherwise.
    """
    execution_item = table.get_item(Key={"executionId": execution_id})
    if "Item" not in execution_item:
        return None
    return execution_item["Item"]


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
    response = table.update_item(
        Key={"executionId": execution_id},
        UpdateExpression="SET executionStatus = :execution_status, uiStatus = :ui_status",
        ExpressionAttributeValues={":execution_status": execution_status, ":ui_status": ui_status},
        ReturnValues="UPDATED_NEW",
    )
    return response


def delete_execution_pipeline(execution_id):
    """
    Delete an execution pipeline and its associated document.

    Args:
        execution_id (str): The ID of the execution to delete.

    Raises:
        Exception: If the execution is not found.
    """
    execution_item = get_execution_item(execution_id)
    if not execution_item:
        raise Exception(f"Execution {execution_id} not found")

    # Update execution item status
    update_execution_item(execution_id, "DELETED", "INACTIVE")

    # Prepare input for Step Function to delete document from OpenSearch
    delete_document_sfn_input = {
        "s3Bucket": execution_item["s3Bucket"],
        "s3Prefix": execution_item["s3Prefix"],
        "chatbotId": execution_item["chatbotId"],
        "indexType": execution_item["indexType"],
        "operationType": "delete",
        "indexId": execution_item["indexId"],
        "groupName": execution_item["groupName"],
        "tableItemId": execution_item["executionId"],
        "embeddingModelType": execution_item["embeddingModelType"],
        "offline": "true",
    }
    sfn_client.start_execution(stateMachineArn=sfn_arn, input=json.dumps(delete_document_sfn_input))


def lambda_handler(event, context):
    """
    AWS Lambda function handler for deleting execution pipelines.

    Args:
        event (dict): The event data passed to the Lambda function.
        context (object): The runtime information of the Lambda function.

    Returns:
        dict: A response object containing the status code, headers, and body.
    """
    logger.info(event)
    input_body = json.loads(event["body"])
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
        # Delete each execution pipeline specified in the input
        for execution_id in input_body["executionId"]:
            delete_execution_pipeline(execution_id)

        # Prepare success response
        output = {"message": "The deletion of specified documents has started", "data": input_body["executionId"]}
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        # Log and return error response
        logger.error("Error: %s", str(e))
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }
