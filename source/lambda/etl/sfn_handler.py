import json
import os

import boto3

client = boto3.client("stepfunctions")


def handler(event, context):
    # First check the event for possible S3 created event
    inputPayload = {}
    if "Records" in event:
        print("S3 created event detected")
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        # Pass the bucket and key to the Step Function, align with the input schema in etl-stack.ts
        inputPayload = json.dumps(
            {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
            }
        )
    else:
        print("API Gateway event detected")
        # Parse the body from the event object
        body = json.loads(event["body"])
        # Pass the parsed body to the Step Function
        inputPayload = json.dumps(body)

    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=inputPayload
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "step_function_arn": response["executionArn"],
                "input_payload": inputPayload,
            }
        ),
    }
