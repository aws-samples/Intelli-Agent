import json
import logging
import os

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)
sfn_client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")

sfn_arn = os.environ.get("SFN_ARN")
table_name = os.environ.get("EXECUTION_TABLE")
table = dynamodb.Table(table_name)

def get_execution_item(execution_id):
    execution_item = table.get_item(Key={"executionId": execution_id})
    if "Item" not in execution_item:
        return None
    return execution_item["Item"]


def update_execution_item(execution_id, execution_status, ui_status):
    response =table.update_item(
        Key={"executionId": execution_id},
        UpdateExpression="SET executionStatus = :execution_status, uiStatus = :ui_status",
        ExpressionAttributeValues={":execution_status": execution_status, ":ui_status": ui_status},
        ReturnValues="UPDATED_NEW"
    )
    return response

def delete_execution_pipeline(execution_id):
    execution_item = get_execution_item(execution_id)
    if not execution_item:
        raise Exception(f"Execution {execution_id} not found")

    # Update execution item
    update_execution_item(execution_id, "DELETED", "INACTIVE")

    # delete document from opensearch using step function
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
        "offline": "true"
    }
    sfn_client.start_execution(
        stateMachineArn=sfn_arn,
        input=json.dumps(delete_document_sfn_input)
    )

        

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
            delete_execution_pipeline(execution_id)
        output = {
            "message": "The deletion of specified documents has started",
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
