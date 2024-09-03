import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from utils.parameter_utils import get_query_parameter

import boto3
from constant import IndexTag, IndexType
from utils.ddb_utils import initiate_chatbot, initiate_index, initiate_model

client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE_NAME"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
create_time = str(datetime.now(timezone.utc))
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    # Check the event for possible S3 created event
    input_payload = {}
    logger.info(event)
    tag = IndexTag.COMMON.value
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    if "Records" in event:
        logger.info("S3 event detected")
        # This is the legacy codes which can handle files in S3 bucket,
        # the S3 eventbridge is removed, re-add it if needed
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        parts = key.split("/")
        group_name = parts[-2] if len(parts) >= 2 else key
        # Update it after supporting create multiple chatbots in one group
        chatbot_id = group_name.lower()
        index_id = f"{chatbot_id}-qd-default"
        index_type = IndexType.QD.value

        if key.endswith("/"):
            logger.info("This is a folder, skip")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "This is a folder, skip",
                    }
                ),
            }
        elif event["Records"][0]["eventName"].startswith("ObjectCreated:"):
            key = unquote_plus(key)

            input_body = {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
                "groupName": group_name,
                "chatbotId": chatbot_id,
                "indexId": index_id,
                "operationType": "update",
            }
        elif event["Records"][0]["eventName"].startswith("ObjectRemoved:"):
            key = unquote_plus(key)

            input_body = {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
                "groupName": group_name,
                "chatbotId": chatbot_id,
                "indexId": index_id,
                "operationType": "delete",
            }
    else:
        logger.info("API Gateway event detected")
        authorizer_type = (
            event["requestContext"].get("authorizer", {}).get("authorizerType")
        )
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            if "use_api_key" in claims:
                group_name = get_query_parameter(event, "GroupName", "Admin")
                cognito_groups_list = [group_name]
            else:
                cognito_groups = claims["cognito:groups"]
                cognito_groups_list = cognito_groups.split(",")
        else:
            logger.error("Invalid authorizer type")
            return {
                "statusCode": 403,
                "headers": resp_header,
                "body": json.dumps({"error": "Invalid authorizer type"}),
            }

        # Parse the body from the event object
        input_body = json.loads(event["body"])
        if "indexType" not in input_body or input_body["indexType"] not in [
            IndexType.QD.value,
            IndexType.QQ.value,
            IndexType.INTENTION.value,
        ]:
            return {
                "statusCode": 400,
                "headers": resp_header,
                "body": (
                    f"Invalid indexType, valid values are "
                    f"{IndexType.QD.value}, {IndexType.QQ.value}, "
                    f"{IndexType.INTENTION.value}"
                ),
            }
        index_type = input_body["indexType"]
        group_name = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
        chatbot_id = input_body.get("chatbotId", group_name.lower())

        if "indexId" in input_body:
            index_id = input_body["indexId"]
        else:
            # Use default index id if not specified in the request
            index_id = f"{chatbot_id}-qd-default"
            if index_type == IndexType.QQ.value:
                index_id = f"{chatbot_id}-qq-default"
            elif index_type == IndexType.INTENTION.value:
                index_id = f"{chatbot_id}-intention-default"

        if "tag" in input_body:
            tag = input_body["tag"]

        input_body["indexId"] = index_id
        input_body["groupName"] = (
            group_name if "groupName" not in input_body else input_body["groupName"]
        )

    model_id = f"{chatbot_id}-embedding"
    embedding_model_type = initiate_model(
        model_table, group_name, model_id, embedding_endpoint, create_time
    )
    initiate_index(
        index_table, group_name, index_id, model_id, index_type, tag, create_time
    )
    initiate_chatbot(
        chatbot_table, group_name, chatbot_id, index_id, index_type, tag, create_time
    )

    input_body["tableItemId"] = context.aws_request_id
    input_body["chatbotId"] = chatbot_id
    input_body["embeddingModelType"] = embedding_model_type
    input_payload = json.dumps(input_body)
    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=input_payload
    )

    # Update execution table item
    if "tableItemId" in input_body:
        del input_body["tableItemId"]
    execution_id = response["executionArn"].split(":")[-1]
    input_body["sfnExecutionId"] = execution_id
    input_body["executionStatus"] = "IN-PROGRESS"
    input_body["indexId"] = index_id
    input_body["executionId"] = context.aws_request_id
    input_body["uiStatus"] = "ACTIVE"
    input_body["createTime"] = create_time

    execution_table.put_item(Item=input_body)

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": context.aws_request_id,
                "step_function_arn": response["executionArn"],
                "input_payload": input_payload,
            }
        ),
    }
