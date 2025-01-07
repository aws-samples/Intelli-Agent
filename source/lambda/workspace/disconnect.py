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
    logger.info(f"Disconnect: {event}")
    connection_id = event['requestContext']['connectionId']
    session_id = f"session_{connection_id}"
    response = session_table.get_item(Key={'sessionId': session_id})
    if 'Item' in response:
        session = response['Item']
        logger.info(session)
        
        # Mark the session as closed
        session_table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression="SET status = :status, lastModifiedTimestamp = :timestamp",
            ExpressionAttributeValues={
                ':status': 'Closed',
                ':timestamp': datetime.utcnow().isoformat()
            }
        )    

    return {"statusCode": 200, "body": json.dumps("Disconnected.")}
