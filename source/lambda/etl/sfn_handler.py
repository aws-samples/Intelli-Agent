import json
import os
import re
from urllib.parse import unquote

import boto3

client = boto3.client("stepfunctions")


def get_valid_workspace_id(s3_prefix):

    s3_prefix = s3_prefix.lower()
    s3_prefix = re.sub(r'[\\\/*?"<>|\s]', "-", s3_prefix)
    s3_prefix = re.sub(r"^[-_+]", "", s3_prefix)
    s3_prefix = s3_prefix[:200]

    return s3_prefix


def handler(event, context):
    # First check the event for possible S3 created event
    input_payload = {}
    print(event)
    if "Records" in event:
        print("S3 event detected")
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

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
            key = unquote(key)
            key_folder = os.path.dirname(key)

            workspace_id = get_valid_workspace_id(key_folder)
            input_payload = json.dumps(
                {
                    "s3Bucket": bucket,
                    "s3Prefix": key,
                    "offline": "false",
                    "qaEnhance": "false",
                    "workspaceId": workspace_id,
                    "operationType": "update",
                }
            )
        elif event["Records"][0]["eventName"].startswith("ObjectRemoved:"):
            key = unquote(key)
            key_folder = os.path.dirname(key)

            workspace_id = get_valid_workspace_id(key_folder)
            input_payload = json.dumps(
                {
                    "s3Bucket": bucket,
                    "s3Prefix": key,
                    "offline": "false",
                    "qaEnhance": "false",
                    "workspaceId": workspace_id,
                    "operationType": "delete",
                }
            )
    else:
        print("API Gateway event detected")
        # Parse the body from the event object
        body = json.loads(event["body"])
        # Pass the parsed body to the Step Function
        input_payload = json.dumps(body)

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=input_payload
    )

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": response["executionArn"].split(":")[-1],
                "step_function_arn": response["executionArn"],
                "input_payload": input_payload,
            }
        ),
    }
