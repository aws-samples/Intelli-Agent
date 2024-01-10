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
    send_msg(
        QUEUE_URL,
        event
    )

    return {"statusCode": 200, "body": "Messages sent to SQS"}
