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

    connection_id = event['requestContext']['connectionId']
    session_id = f"session_{connection_id}"
    timestamp = datetime.utcnow().isoformat()
    # TODO: get user id from Cognito
    user_id = "demo"
    session_table.put_item(Item={
        'sessionId': session_id,
        'userId': user_id,
        'clientType': "web_ui",
        'createTimestamp': timestamp,
        'lastModifiedTimestamp': timestamp,
        'latestQuestion': '',
        'startTime': timestamp,
        'status': 'Pending',
        'agentId': ''
    })


    return {"statusCode": 200, "body": json.dumps("Connected.")}
