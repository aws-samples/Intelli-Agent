import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3

client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE"))


def handler(event, context):
    # First check the event for possible S3 created event
    input_payload = {}
    print(event)
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    if "Records" in event:
        print("S3 event detected")
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        parts = key.split("/")
        workspace_id = parts[-2] if len(parts) >= 2 else key

        if key.endswith("/"):
            print("This is a folder, skip")
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
                "workspaceId": workspace_id,
                "operationType": "update",
            }
        elif event["Records"][0]["eventName"].startswith("ObjectRemoved:"):
            key = unquote_plus(key)

            input_body = {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
                "workspaceId": workspace_id,
                "operationType": "delete",
            }
    else:
        print("API Gateway event detected")
        authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            cognito_groups = claims["cognito:groups"]
            cognito_groups_list = cognito_groups.split(",")
        else:
            raise Exception("Invalid authorizer type")
        # Parse the body from the event object
        input_body = json.loads(event["body"])

        workspace_id = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
        input_body["workspaceId"] = (
            workspace_id
            if "workspaceId" not in input_body
            else input_body["workspaceId"]
        )

    input_body["tableItemId"] = context.aws_request_id
    input_payload = json.dumps(input_body)
    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=input_payload
    )

    if "tableItemId" in input_body:
        del input_body["tableItemId"]
    execution_id = response["executionArn"].split(":")[-1]
    create_time = str(datetime.now(timezone.utc))
    input_body["sfnExecutionId"] = execution_id
    input_body["executionStatus"] = "IN-PROGRESS"
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
