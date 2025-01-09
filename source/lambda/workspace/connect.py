import json
import logging
import boto3
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource("dynamodb")
session_table = dynamodb.Table(os.environ.get("SESSIONS_TABLE_NAME"))


def lambda_handler(event, context):
    logger.info(f"Connect: {event}")
    connection_id = event["requestContext"]["connectionId"]
    qs_param = event["queryStringParameters"]
    if "session_id" not in qs_param and "user_id" not in qs_param:
        logger.info("Agent connected")
        return {"statusCode": 200, "body": json.dumps("Agent connected.")}

    if "role" in qs_param and qs_param["role"] == "agent":
        logger.info("Agent connected")
        return {"statusCode": 200, "body": json.dumps("Agent connected.")}

    session_id = qs_param["session_id"]
    user_id = qs_param["user_id"]
    timestamp = datetime.utcnow().isoformat()
    session_table.put_item(Item={
        "sessionId": session_id,
        "userId": user_id,
        "connectionId": connection_id,
        "clientType": "web_ui",
        "createTimestamp": timestamp,
        "lastModifiedTimestamp": timestamp,
        "latestQuestion": "",
        "startTime": timestamp,
        "status": "Pending",
        "agentId": ""
    })

    return {"statusCode": 200, "body": json.dumps("User connected.")}
