"""
Lambda function for managing execution pipelines and associated documents.
Provides REST API endpoints for CRUD operations on execution pipelines,
handling document management in DynamoDB and OpenSearch.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.paginate import TokenEncoder
from constant import ExecutionStatus, OperationType, UiStatus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class AwsResources:
    """Centralized AWS resource management"""

    sfn_client = boto3.client("stepfunctions")
    dynamodb = boto3.resource("dynamodb")
    dynamodb_client = boto3.client("dynamodb")

    def __post_init__(self):
        # Initialize DynamoDB tables
        self.execution_table = self.dynamodb.Table(Config.EXECUTION_TABLE_NAME)
        self.object_table = self.dynamodb.Table(Config.ETL_OBJECT_TABLE_NAME)


class Config:
    """Configuration constants"""

    SFN_ARN = os.environ["SFN_ARN"]
    EXECUTION_TABLE_NAME = os.environ["EXECUTION_TABLE"]
    ETL_OBJECT_TABLE_NAME = os.environ["ETL_OBJECT_TABLE"]
    ETL_OBJECT_INDEX = os.environ["ETL_OBJECT_INDEX"]
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


class AuthorizationHelper:
    @staticmethod
    def get_cognito_groups(event: Dict[str, Any]) -> List[str]:
        """Extract and validate Cognito groups from event authorizer"""
        authorizer = event["requestContext"].get("authorizer", {})
        authorizer_type = authorizer.get("authorizerType")

        if authorizer_type != "lambda_authorizer":
            logger.error("Invalid authorizer type")
            raise ValueError("Invalid authorizer type")

        claims = json.loads(authorizer["claims"])

        if "use_api_key" in claims:
            return [claims.get("GroupName", "Admin")]

        return claims["cognito:groups"].split(",")


class ExecutionManager:
    """Handles execution-related database operations"""

    @staticmethod
    def get_execution(execution_id: str) -> Optional[Dict]:
        """Retrieve execution details from DynamoDB"""
        response = aws_resources.execution_table.get_item(Key={"executionId": execution_id})
        return response.get("Item")

    @staticmethod
    def update_execution_status(execution_id: str, execution_status: str, ui_status: str) -> Dict:
        """Update execution status in DynamoDB"""
        return aws_resources.execution_table.update_item(
            Key={"executionId": execution_id},
            UpdateExpression="SET executionStatus = :execution_status, uiStatus = :ui_status",
            ExpressionAttributeValues={":execution_status": execution_status, ":ui_status": ui_status},
            ReturnValues="UPDATED_NEW",
        )

    @staticmethod
    def delete_execution(execution_id: str) -> None:
        """Initiate execution deletion process"""
        execution = ExecutionManager.get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        # Update status to indicate deletion in progress
        ExecutionManager.update_execution_status(execution_id, ExecutionStatus.DELETING.value, UiStatus.ACTIVE.value)

        # Prepare deletion input for Step Function
        deletion_input = {
            "s3Bucket": execution["s3Bucket"],
            "s3Prefix": execution["s3Prefix"],
            "chatbotId": execution["chatbotId"],
            "indexType": execution["indexType"],
            "operationType": OperationType.DELETE.value,
            "indexId": execution["indexId"],
            "groupName": execution["groupName"],
            "tableItemId": execution["executionId"],
            "embeddingModelType": execution["embeddingModelType"],
            "offline": "true",
        }

        aws_resources.sfn_client.start_execution(stateMachineArn=Config.SFN_ARN, input=json.dumps(deletion_input))

    @staticmethod
    def get_filtered_executions(
        paginator, cognito_groups: List[str], pagination_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get filtered executions based on user groups"""
        if "Admin" in cognito_groups:
            response_iterator = paginator.paginate(
                TableName=Config.EXECUTION_TABLE_NAME,
                PaginationConfig=pagination_config,
                FilterExpression="uiStatus = :active",
                ExpressionAttributeValues={":active": {"S": "ACTIVE"}},
            )
        else:
            response_iterator = paginator.paginate(
                TableName=Config.EXECUTION_TABLE_NAME,
                PaginationConfig=pagination_config,
                FilterExpression="uiStatus = :active AND groupName = :group_id",
                ExpressionAttributeValues={
                    ":active": {"S": "ACTIVE"},
                    ":group_id": {"S": cognito_groups[0]},
                },
            )

        output = {}
        encoder = TokenEncoder()

        for page in response_iterator:
            page_items = page["Items"]
            processed_items = []

            for item in page_items:
                processed_item = {key: value["S"] for key, value in item.items()}
                processed_items.append(processed_item)

            output["Items"] = processed_items
            output["Count"] = page["Count"]
            output["Config"] = pagination_config

            if "LastEvaluatedKey" in page:
                output["LastEvaluatedKey"] = encoder.encode({"ExclusiveStartKey": page["LastEvaluatedKey"]})

        return output

    @staticmethod
    def update_execution(execution_id: str, update_s3_bucket: str, update_s3_prefix: str) -> Dict[str, Any]:
        """Update execution details in DynamoDB

        Args:
            execution_id: The ID of the execution to update
            update_s3_bucket: The new S3 bucket
            update_s3_prefix: The new S3 prefix

        Returns:
            Updated execution item

        Raises:
            ValueError: If execution not found or invalid update data
        """
        # Verify execution exists
        execution = ExecutionManager.get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        ExecutionManager.update_execution_status(execution_id, ExecutionStatus.UPDATING.value, UiStatus.ACTIVE.value)

        existing_s3_bucket = execution["s3Bucket"]
        existing_s3_prefix = execution["s3Prefix"]

        if existing_s3_bucket == update_s3_bucket and existing_s3_prefix == update_s3_prefix:
            update_execution_input = {
                "s3Bucket": execution["s3Bucket"],
                "s3Prefix": execution["s3Prefix"],
                "chatbotId": execution["chatbotId"],
                "indexType": execution["indexType"],
                "operationType": OperationType.UPDATE.value,
                "indexId": execution["indexId"],
                "groupName": execution["groupName"],
                "tableItemId": execution["executionId"],
                "embeddingModelType": execution["embeddingModelType"],
                "offline": "true",
            }

            aws_resources.sfn_client.start_execution(
                stateMachineArn=Config.SFN_ARN, input=json.dumps(update_execution_input)
            )
        else:
            # Prepare deletion input for Step Function
            deletion_input = {
                "s3Bucket": execution["s3Bucket"],
                "s3Prefix": execution["s3Prefix"],
                "chatbotId": execution["chatbotId"],
                "indexType": execution["indexType"],
                "operationType": OperationType.DELETE.value,
                "indexId": execution["indexId"],
                "groupName": execution["groupName"],
                "tableItemId": execution["executionId"],
                "embeddingModelType": execution["embeddingModelType"],
                "offline": "true",
            }

            aws_resources.sfn_client.start_execution(stateMachineArn=Config.SFN_ARN, input=json.dumps(deletion_input))

            # Create new execution for the updated S3 bucket and prefix
            update_execution_input = {
                "s3Bucket": update_s3_bucket,
                "s3Prefix": update_s3_prefix,
                "chatbotId": execution["chatbotId"],
                "indexType": execution["indexType"],
                "operationType": OperationType.CREATE.value,
                "indexId": execution["indexId"],
                "groupName": execution["groupName"],
                "tableItemId": execution["executionId"],
                "embeddingModelType": execution["embeddingModelType"],
                "offline": "true",
            }

            aws_resources.sfn_client.start_execution(
                stateMachineArn=Config.SFN_ARN, input=json.dumps(update_execution_input)
            )

        return {"Message": "Update process initiated", "execution_id": execution_id}


class ApiResponse:
    """Standardized API response handler"""

    @staticmethod
    def success(data: Any, status_code: int = 200) -> Dict:
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps(data)}

    @staticmethod
    def error(message: str, status_code: int = 500) -> Dict:
        logger.error("Error: %s", message)
        return {"statusCode": status_code, "headers": Config.CORS_HEADERS, "body": json.dumps({"error": str(message)})}


class ApiHandler:
    """API endpoint handlers"""

    @staticmethod
    def delete_executions(event: Dict) -> Dict:
        """Handle DELETE /executions endpoint"""
        try:
            execution_ids = json.loads(event["body"])["executionId"]
            for execution_id in execution_ids:
                ExecutionManager.delete_execution(execution_id)

            return ApiResponse.success({"Message": "Deletion process initiated", "ExecutionIds": execution_ids})
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def get_execution_objects(event: Dict) -> Dict:
        """Handle GET /executions/{executionId}/objects endpoint"""
        try:
            execution_id = event["pathParameters"]["executionId"]
            response = aws_resources.object_table.query(
                IndexName=Config.ETL_OBJECT_INDEX, KeyConditionExpression=Key("executionId").eq(execution_id)
            )

            return ApiResponse.success({"Items": response["Items"], "Count": response["Count"]})
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def list_executions(event: Dict) -> Dict:
        """Handle GET /executions endpoint"""
        try:
            # Get cognito groups and pagination config and paginator
            cognito_groups = AuthorizationHelper.get_cognito_groups(event)
            pagination_config = PaginationConfig.get_pagination_config(event)
            paginator = aws_resources.dynamodb_client.get_paginator("scan")

            # Get and process executions
            result = ExecutionManager.get_filtered_executions(paginator, cognito_groups, pagination_config)

            return ApiResponse.success(result)
        except ValueError as ve:
            return ApiResponse.error(str(ve), 403)
        except Exception as e:
            return ApiResponse.error(str(e))

    @staticmethod
    def update_execution(event: Dict) -> Dict:
        """Handle PUT /executions/{executionId} endpoint"""
        try:
            event_body = json.loads(event["body"])
            execution_id = event_body["executionId"]
            update_s3_bucket = event_body["s3Bucket"]
            update_s3_prefix = event_body["s3Prefix"]

            updated_execution = ExecutionManager.update_execution(execution_id, update_s3_bucket, update_s3_prefix)
            return ApiResponse.success(updated_execution)

        except ValueError as ve:
            return ApiResponse.error(str(ve), 400)
        except Exception as e:
            return ApiResponse.error(str(e))


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Routes API requests to appropriate handlers based on HTTP method and path"""
    logger.info("Received event: %s", json.dumps(event))

    routes = {
        ("DELETE", "/knowledge-base/executions"): ApiHandler.delete_executions,
        ("GET", "/knowledge-base/executions/{executionId}"): ApiHandler.get_execution_objects,
        ("GET", "/knowledge-base/executions"): ApiHandler.list_executions,
        ("PUT", "/knowledge-base/executions/{executionId}"): ApiHandler.update_execution,
    }

    handler = routes.get((event["httpMethod"], event["resource"]))
    if not handler:
        return ApiResponse.error("Route not found", 404)

    return handler(event)
