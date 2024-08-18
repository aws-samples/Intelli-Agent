import json
import logging
import os

import boto3

QUEUE_URL = os.environ["SQS_QUEUE_URL"]
aws_region = os.environ["AWS_REGION"]
sqs = boto3.client("sqs", region_name=aws_region)
logger = logging.getLogger()
logger.setLevel("INFO")


def send_msg(queue_url, event):
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(event),
    )

    return response


def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    event_body = json.loads(event["body"])

    if "user_id" not in event_body:
        authorizer_type = (
            event["requestContext"].get("authorizer", {}).get("authorizerType")
        )
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            cognito_username = claims["cognito:username"]
        else:
            cognito_username = "default_user_id"

        event_body["user_id"] = cognito_username
    updated_event_body_str = json.dumps(event_body, ensure_ascii=False)
    event["body"] = updated_event_body_str
    send_msg(QUEUE_URL, event)

    return {"statusCode": 200, "body": "Messages sent to SQS"}
