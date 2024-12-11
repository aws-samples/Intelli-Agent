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

import boto3
from boto3.dynamodb.conditions import Key
from botocore.paginate import TokenEncoder

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


class PaginationConfig:
    @staticmethod
    def get_query_parameter(event: Dict[str, Any], parameter_name: str, default_value: Any = None) -> Any:
        """Extract query parameter from event with default value"""
        if event.get("queryStringParameters") and parameter_name in event["queryStringParameters"]:
            return event["queryStringParameters"][parameter_name]
        return default_value

    @classmethod
    def get_pagination_config(cls, event: Dict[str, Any]) -> Dict[str, Any]:
        """Build pagination configuration from event parameters"""
        return {
            "MaxItems": int(cls.get_query_parameter(event, "max_items", Config.DEFAULT_MAX_ITEMS)),
            "PageSize": int(cls.get_query_parameter(event, "page_size", Config.DEFAULT_PAGE_SIZE)),
            "StartingToken": cls.get_query_parameter(event, "starting_token"),
        }


class ChatHistoryManager:
    """Handles chat history related database operations"""

    @staticmethod
    def get_session(session_id: str, user_id: str) -> Optional[Dict]:
        """Retrieve session details from DynamoDB"""
        response = aws_resources.sessions_table.get_item(Key={"sessionId": session_id, "userId": user_id})
        return response.get("Item")

    @staticmethod
    def get_message(message_id: str, session_id: str) -> Optional[Dict]:
        """Retrieve message details from DynamoDB"""
        response = aws_resources.messages_table.get_item(Key={"messageId": message_id, "sessionId": session_id})
        return response.get("Item")

    @staticmethod
    def list_sessions(user_id: str, pagination_config: Dict[str, Any]) -> Dict[str, Any]:
        """List sessions for a user with pagination"""
        paginator = aws_resources.dynamodb_client.get_paginator("query")

        response_iterator = paginator.paginate(
            TableName=Config.SESSIONS_TABLE_NAME,
            IndexName=Config.SESSIONS_BY_TIMESTAMP_INDEX,
            KeyConditionExpression="userId = :user_id",
            ExpressionAttributeValues={":user_id": {"S": user_id}},
            ScanIndexForward=False,
            PaginationConfig=pagination_config,
        )

        return ChatHistoryManager._process_paginated_response(
            response_iterator,
            ["sessionId", "userId", "createTimestamp", "latestQuestion", "chatbotId"],
            pagination_config=pagination_config,
        )

    @staticmethod
    def list_messages(session_id: str, pagination_config: Dict[str, Any]) -> Dict[str, Any]:
        """List messages for a session with pagination"""
        paginator = aws_resources.dynamodb_client.get_paginator("query")

        response_iterator = paginator.paginate(
            TableName=Config.MESSAGES_TABLE_NAME,
            IndexName=Config.MESSAGES_BY_SESSION_ID_INDEX,
            KeyConditionExpression="sessionId = :session_id",
            ExpressionAttributeValues={":session_id": {"S": session_id}},
            ScanIndexForward=False,
            PaginationConfig=pagination_config,
        )

        return ChatHistoryManager._process_paginated_response(
            response_iterator,
            ["messageId", "role", "content", "createTimestamp", "chatbotId"],
            pagination_config=pagination_config,
            is_messages_list=True,
        )

    @staticmethod
    def _process_paginated_response(
        response_iterator, keys: list, pagination_config: Dict[str, Any] = None, is_messages_list: bool = False
    ) -> Dict[str, Any]:
        """Process paginated responses from DynamoDB"""
        output = {}
        processed_items = []

        for page in response_iterator:
            items = page["Items"]

            for item in items:
                processed_item = {key: item.get(key, {"S": ""})["S"] for key in keys}
                # special handling for AI messages while listing messages
                if is_messages_list and item.get("role", {}).get("S") == "ai":
                    processed_item["additional_kwargs"] = json.loads(item["additional_kwargs"]["S"])
                processed_items.append(processed_item)

            if "LastEvaluatedKey" in page:
                output["LastEvaluatedKey"] = token_encoder.encode({"ExclusiveStartKey": page["LastEvaluatedKey"]})
            break

        # Sort based on createTimestamp
        # For sessions list: descending order (newest first)
        # For messages list: ascending order (oldest first)
        if "createTimestamp" in keys:
            processed_items.sort(
                key=lambda x: x["createTimestamp"],
                reverse=not is_messages_list,  # False for messages (ascending), True for sessions (descending)
            )

        output["Items"] = processed_items
        output["Config"] = pagination_config
        output["Count"] = len(processed_items)
        return output

    @staticmethod
    def add_feedback(
        session_id: str, user_id: str, message_id: str, feedback_type: str, feedback_reason: str, suggest_message: Dict
    ) -> Dict[str, Any]:
        """Add feedback to a message"""
        # First verify the session belongs to the user
        session = ChatHistoryManager.get_session(session_id, user_id)
        if not session:
            return {"added": False, "error": "Session not found or unauthorized"}

        message = ChatHistoryManager.get_message(message_id, session_id)
        if not message:
            return {"added": False, "error": "Message not found"}

        try:
            current_timestamp = datetime.utcnow().isoformat() + "Z"

            # Update message with feedback
            aws_resources.messages_table.update_item(
                Key={"messageId": message_id, "sessionId": session_id},
                UpdateExpression="SET feedbackType = :ft, feedbackReason = :fr, suggestMessage = :sm, lastModifiedTimestamp = :t",
                ExpressionAttributeValues={
                    ":ft": feedback_type,
                    ":fr": feedback_reason,
                    ":sm": suggest_message,
                    ":t": current_timestamp,
                },
            )

            # Update session last modified time
            aws_resources.sessions_table.update_item(
                Key={"sessionId": session_id, "userId": user_id},
                UpdateExpression="SET lastModifiedTimestamp = :t",
                ExpressionAttributeValues={":t": current_timestamp},
            )

            return {"added": True}
        except Exception as e:
            logger.error("Error adding feedback: %s", str(e))
            return {"added": False, "error": str(e)}


class ApiResponse:
    """Standardized API response handler"""

    @staticmethod
    def success(data: Any, status_code: int = 200) -> Dict:
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps(data, cls=DecimalEncoder)}

    @staticmethod
    def error(message: str, status_code: int = 500) -> Dict:
        logger.error("Error: %s", message)
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps({"error": str(message)})}


class ApiHandler:
    """API endpoint handlers"""

    @staticmethod
    def list_sessions(event: Dict) -> Dict:
        """Handle GET /chat-history/sessions endpoint"""
        try:
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            user_id = claims["cognito:username"]
            pagination_config = PaginationConfig.get_pagination_config(event)
            result = ChatHistoryManager.list_sessions(user_id, pagination_config)
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def list_messages(event: Dict) -> Dict:
        """Handle GET /chat-history/sessions/{sessionId}/messages endpoint"""
        try:
            session_id = event["pathParameters"]["sessionId"]
            pagination_config = PaginationConfig.get_pagination_config(event)
            result = ChatHistoryManager.list_messages(session_id, pagination_config)
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def add_feedback(event: Dict) -> Dict:
        """Handle POST /sessions/{sessionId}/messages/{messageId}/feedback endpoint"""
        try:
            # Extract path parameters
            session_id = event["pathParameters"]["sessionId"]
            message_id = event["pathParameters"]["messageId"]
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            user_id = claims["cognito:username"]

            # Parse request body
            body = json.loads(event["body"])
            result = ChatHistoryManager.add_feedback(
                session_id=session_id,
                user_id=user_id,
                message_id=message_id,
                feedback_type=body["feedback_type"],
                feedback_reason=body["feedback_reason"],
                suggest_message=body["suggest_message"],
            )
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Routes API requests to appropriate handlers based on HTTP method and path"""
    logger.info("Received event: %s", json.dumps(event))

    routes = {
        # More RESTful paths
        ("GET", "/sessions"): ApiHandler.list_sessions,
        ("GET", "/sessions/{sessionId}/messages"): ApiHandler.list_messages,
        ("POST", "/sessions/{sessionId}/messages/{messageId}/feedback"): ApiHandler.add_feedback,
    }

    handler = routes.get((event["httpMethod"], event["resource"]))
    if not handler:
        return ApiResponse.error("Route not found", 404)

    return handler(event)
