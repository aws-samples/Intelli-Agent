import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from utils.parameter_utils import get_query_parameter
from chatbot_management import create_chatbot
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
sfn_arn = os.environ.get("SFN_ARN")
create_time = str(datetime.now(timezone.utc))


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    # Check the event for possible S3 created event
    input_payload = {}
    logger.info(event)
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

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
    else:
        tag = index_id

    input_body["indexId"] = index_id
    input_body["groupName"] = (
        group_name if "groupName" not in input_body else input_body["groupName"]
    )
    chatbot_event = {
        "body": json.dumps({"group_name": group_name})
    }
    chatbot_result = create_chatbot(chatbot_event, group_name)

    input_body["tableItemId"] = context.aws_request_id
    input_body["chatbotId"] = chatbot_id
    input_body["embeddingModelType"] = chatbot_result["modelType"]
    input_payload = json.dumps(input_body)
    response = client.start_execution(
        stateMachineArn=sfn_arn, input=input_payload
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
