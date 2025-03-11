import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, TypedDict

import boto3
from constant import ExecutionStatus, IndexType, UiStatus
from utils.parameter_utils import get_query_parameter

# Initialize AWS resources once
client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE_NAME"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
sfn_arn = os.environ.get("SFN_ARN")


# Consolidate constants at the top
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}

# Initialize logging at the top level
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_index_type(index_type: str) -> bool:
    """Validate if the provided index type is supported."""
    valid_types = [
        IndexType.QD.value,
        IndexType.QQ.value,
        IndexType.INTENTION.value,
    ]
    return index_type in valid_types


def get_etl_info(group_name: str, chatbot_id: str, index_type: str):
    """
    Retrieve the index id, model type, and model endpoint for the given chatbot and index type.
    These will be further used to perform knowledge ingestion to opensearch.
    Returns: Tuple of (index_id, model_type, model_endpoint)
    """

    chatbot_item = chatbot_table.get_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    ).get("Item")

    model_item = model_table.get_item(
        Key={"groupName": group_name, "modelId": f"{chatbot_id}-embedding"}
    ).get("Item")

    if not (chatbot_item and model_item):
        raise ValueError("Chatbot or model not found")

    model = model_item.get("parameter", {})
    specific_type_indices = (
        chatbot_item.get("indexIds", {}).get(index_type, {}).get("value", {})
    )

    if not specific_type_indices:
        raise ValueError("No indices found for the given index type")

    return (
        next(iter(specific_type_indices.values())),  # First index ID
        model.get("ModelType"),
        model.get("ModelEndpoint"),
    )


def create_execution_record(
    execution_id: str, input_body: Dict, sfn_execution_id: str
) -> None:
    """Create execution record in DynamoDB."""
    execution_record = {
        **input_body,
        "sfnExecutionId": sfn_execution_id,
        "executionStatus": ExecutionStatus.IN_PROGRESS.value,
        "executionId": execution_id,
        "uiStatus": UiStatus.ACTIVE.value,
        "createTime": str(datetime.now(timezone.utc)),
    }
    del execution_record["tableItemId"]
    execution_table.put_item(Item=execution_record)


def handler(event: Dict, context) -> Dict:
    """Main Lambda handler for ETL operations."""
    logger.info(event)

    try:
        # Validate and extract authorization
        authorizer = event["requestContext"].get("authorizer", {})
        if authorizer.get("authorizerType") != "lambda_authorizer":
            raise ValueError("Invalid authorizer type")

        claims = json.loads(authorizer.get("claims", {}))
        if "use_api_key" in claims:
            group_name = get_query_parameter(event, "GroupName", "Admin")
            cognito_groups_list = [group_name]
        else:
            cognito_groups_list = claims["cognito:groups"].split(",")

        # Process input
        input_body = json.loads(event["body"])
        index_type = input_body.get("indexType")

        if not validate_index_type(index_type):
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": f"Invalid indexType, valid values are {', '.join([t.value for t in IndexType])}",
            }
            
        # Validate OpenAI model provider requirements
        if input_body.get("modelProvider") == "openai":
            required_fields = ["modelId", "modelSecretName", "modelApiUrl"]
            missing_fields = [field for field in required_fields if not input_body.get(field)]
            if missing_fields:
                raise ValueError(f"When using OpenAI provider, the following fields are required: {', '.join(missing_fields)}")

        group_name = input_body.get("groupName") or (
            "Admin"
            if "Admin" in cognito_groups_list
            else cognito_groups_list[0]
        )
        chatbot_id = input_body.get("chatbotId", group_name.lower())
        index_id, embedding_model_type, embedding_endpoint = get_etl_info(
            group_name, chatbot_id, index_type
        )

        # Update input body with processed values
        input_body.update(
            {
                "chatbotId": chatbot_id,
                "groupName": group_name,
                "tableItemId": context.aws_request_id,
                "indexId": index_id,
                "embeddingModelType": embedding_model_type,
                "embeddingEndpoint": embedding_endpoint,
            }
        )

        # Start step function and create execution record
        sfn_response = client.start_execution(
            stateMachineArn=sfn_arn, input=json.dumps(input_body)
        )

        execution_id = context.aws_request_id
        create_execution_record(
            execution_id,
            input_body,
            sfn_response["executionArn"].split(":")[-1],
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {
                    "execution_id": execution_id,
                    "step_function_arn": sfn_response["executionArn"],
                    "input_payload": input_body,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)}),
        }
