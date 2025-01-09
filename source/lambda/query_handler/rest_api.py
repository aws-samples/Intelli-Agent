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


class CustomerChatManager:
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
    def list_pending_sessions(event, pagination_config: Dict[str, Any]) -> Dict[str, Any]:
        """List pending sessions and active sessions assigned to current agent"""
        claims = event['requestContext']['authorizer']['claims']
        claims_json = json.loads(claims)
        agent_id = claims_json.get("sub")

        response = aws_resources.sessions_table.scan(
            FilterExpression="(#st = :pending_status) OR (#st = :active_status AND agentId = :agent_id)",
            ExpressionAttributeValues={
                ':pending_status': 'Pending',
                ':active_status': 'Active',
                ':agent_id': agent_id
            },
            ExpressionAttributeNames={
                '#st': 'status'
            }
        )

        items = response.get('Items', [])
        
        # Sort by createTimestamp in descending order (newest first)
        items.sort(key=lambda x: x['createTimestamp'], reverse=True)
        
        return {
            "Items": items,
            "Count": len(items)
        }

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

        return CustomerChatManager._process_paginated_response(
            response_iterator,
            ["messageId", "role", "content", "createTimestamp"],
            pagination_config=pagination_config,
            is_messages_list=True,
        )

    @staticmethod
    def select_session(event, pagination_config: Dict[str, Any]):
        body = json.loads(event['body'])
        session_id = body.get('session_id')
        claims = event['requestContext']['authorizer']['claims']
        claims_json = json.loads(claims)
        agent_id = claims_json.get("sub")
        timestamp = datetime.utcnow().isoformat()

        logger.info("start to update ddb")
        aws_resources.sessions_table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression="SET agentId = :agent_id, #st = :status, lastModifiedTimestamp = :ts",
            ExpressionAttributeValues={
                ':agent_id': agent_id,
                ':status': 'Active',
                ':ts': timestamp
            },
            ExpressionAttributeNames={
                '#st': 'status'
            }
        )

        logger.info("start to list message")
        return CustomerChatManager.list_messages(session_id, pagination_config)



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
                if is_messages_list and item.get("role", {}).get("S") == "agent":
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
        """Handle GET /customer-sessions/sessions endpoint"""
        try:
            pagination_config = PaginationConfig.get_pagination_config(event)
            result = CustomerChatManager.list_pending_sessions(event, pagination_config)
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def list_messages(event: Dict) -> Dict:
        """Handle GET /customer-sessions/{sessionId}/messages endpoint"""
        try:
            session_id = event["pathParameters"]["sessionId"]
            pagination_config = PaginationConfig.get_pagination_config(event)
            result = CustomerChatManager.list_messages(session_id, pagination_config)
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def select_session(event: Dict) -> Dict:
        """Handle POST /customer-sessions/{session_id} endpoint"""
        try:
            pagination_config = PaginationConfig.get_pagination_config(event)
            result = CustomerChatManager.select_session(event, pagination_config)
            return ApiResponse.success(result)
        except Exception as e:
            return ApiResponse.error(str(e))



def lambda_handler(event: Dict, context: Any) -> Dict:
    """Routes API requests to appropriate handlers based on HTTP method and path"""
    logger.info("Received event: %s", json.dumps(event))

    routes = {
        ("GET", "/customer-sessions"): ApiHandler.list_sessions,
        ("GET", "/customer-sessions/{sessionId}/messages"): ApiHandler.list_messages,
        ("POST", "/customer-sessions"): ApiHandler.select_session,
    }

    handler = routes.get((event["httpMethod"], event["resource"]))
    if not handler:
        return ApiResponse.error("Route not found", 404)

    return handler(event)
