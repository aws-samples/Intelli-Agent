"""
Lambda function for managing chat history operations.
Provides REST API endpoints for listing sessions, messages,
and managing message ratings.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

import boto3
from botocore.paginate import TokenEncoder

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

websocket_url = os.environ.get("WEBSOCKET_URL")
api_client = boto3.client('apigatewaymanagementapi', endpoint_url=websocket_url)


@dataclass
class AwsResources:
    """Centralized AWS resource management"""

    dynamodb = boto3.resource("dynamodb")
    dynamodb_client = boto3.client("dynamodb")

    def __post_init__(self):
        # Initialize DynamoDB tables
        self.sessions_table = self.dynamodb.Table(Config.SESSIONS_TABLE_NAME)
        self.messages_table = self.dynamodb.Table(Config.MESSAGES_TABLE_NAME)


class Config:
    """Configuration constants"""

    SESSIONS_TABLE_NAME = os.environ["SESSIONS_TABLE_NAME"]
    MESSAGES_TABLE_NAME = os.environ["MESSAGES_TABLE_NAME"]
    SESSIONS_BY_TIMESTAMP_INDEX = os.environ["SESSIONS_BY_TIMESTAMP_INDEX_NAME"]
    MESSAGES_BY_SESSION_ID_INDEX = os.environ["MESSAGES_BY_SESSION_ID_INDEX_NAME"]
    DEFAULT_PAGE_SIZE = 50
    DEFAULT_MAX_ITEMS = 50

    CORS_HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }


# Initialize AWS resources
aws_resources = AwsResources()
token_encoder = TokenEncoder()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)



class ApiResponse:
    """Standardized API response handler"""

    @staticmethod
    def success(data: Any, status_code: int = 200) -> Dict:
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps(data, cls=DecimalEncoder)}

    @staticmethod
    def error(message: str, status_code: int = 500) -> Dict:
        logger.error("Error: %s", message)
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps({"error": str(message)})}



def send_message(event, context):
    body = json.loads(event['body'])
    logger.info("Send message body:")
    logger.info(body)
    
    if "user_id" in body:
        user_id = body.get('user_id')
    else:
        user_id = event['requestContext']['authorizer']['claims']['sub']
    content = body.get('query')
    session_id = body.get('session_id')

    timestamp = datetime.utcnow().isoformat()
    aws_resources.sessions_table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression="SET lastModifiedTimestamp = :ts, latestQuestion = :content",
        # UpdateExpression="SET lastModifiedTimestamp = :ts, latestQuestion = :content, #st = :status",
        ExpressionAttributeValues={
            ':ts': timestamp,
            ':content': content
            # ':status': "Pending"
        }
        # ExpressionAttributeNames={
        #     '#st': 'status'
        # }
    )

    # Add message to the Message Table
    message_id = str(uuid.uuid4())
    aws_resources.messages_table.put_item(Item={
        'messageId': message_id,
        'sessionId': session_id,
        'additional_kwargs': "{}",
        'content': content,
        'createTimestamp': timestamp,
        'lastModifiedTimestamp': timestamp,
        'role': 'user'
    })

    return {'statusCode': 200, 'body': json.dumps({'sessionId': session_id, 'messageId': message_id})}


def send_response(event, context):
    body = json.loads(event['body'])
    session_id = body.get('session_id')
    content = body.get('query')
    # agent_id = event['requestContext']['authorizer']['claims']['sub']  # Cognito Agent ID
    timestamp = datetime.utcnow().isoformat()

    # Add message to the Message Table
    message_id = str(uuid.uuid4())
    aws_resources.messages_table.put_item(Item={
        'messageId': message_id,
        'sessionId': session_id,
        'additional_kwargs': "{}",
        'content': content,
        'createTimestamp': timestamp,
        'lastModifiedTimestamp': timestamp,
        'role': 'agent'
    })

    # Retrieve the connection ID for the end customer from the session
    session_response = aws_resources.sessions_table.get_item(Key={'sessionId': session_id})
    if 'Item' not in session_response:
        return {'statusCode': 404, 'body': 'Session not found'}

    session = session_response['Item']
    logger.info(session)
    connection_id = session.get('connectionId')  # Assume connectionId is stored in the session table
    if not connection_id:
        return {'statusCode': 400, 'body': 'No active connection for the session'}
    
    # TODO: can be deleted
    aws_resources.sessions_table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression="SET lastModifiedTimestamp = :ts, latestResponse = :content, #st = :status",
        ExpressionAttributeValues={
            ':ts': timestamp,
            ':content': content,
            ':status': "Active"
        },
        ExpressionAttributeNames={
            '#st': 'status'
        }
    )    

    # Send the message to the customer's WebSocket
    try:
        logger.info("connection start")
        logger.info(connection_id)
        api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                'session_id': session_id,
                'message_id': message_id,
                'query': content,
                'role': 'agent',
                'timestamp': timestamp
            })
        )
        logger.info("connection end")
    except api_client.exceptions.GoneException:
        logger.info("connection failed in except statement")
        # Handle case where the connection is no longer valid
        aws_resources.sessions_table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression="SET #st = :status, lastModifiedTimestamp = :timestamp",
            ExpressionAttributeValues={
                ':status': 'Closed',
                ':timestamp': timestamp
            },
            ExpressionAttributeNames={
                '#st': 'status'
            }
        )
        return {'statusCode': 410, 'body': 'Connection closed'}

    return {'statusCode': 200, 'body': json.dumps({'sessionId': session_id, 'messageId': message_id})}



def lambda_handler(event: Dict, context: Any) -> Dict:
    """Routes API requests to appropriate handlers based on WebSocket API route"""
    logger.info("Received event: %s", json.dumps(event))
    if "Records" in event:
        for record in event["Records"]:
            event_body = json.loads(record["body"])
            logger.info("Websocket event body")
            logger.info(event_body)
            route_key = event_body["requestContext"]["routeKey"]
            if route_key in ["sendMessage", "$default"]:
                send_message(event_body, context)
            else:
                raise ValueError(f"Invalid route key: {route_key}")
    else:
        route_key = event["requestContext"]["routeKey"]
        if route_key == "sendResponse":
            send_response(event, context)
        else:
            raise ValueError(f"Invalid route key: {route_key}")


    return {"test_message": "hi"}
