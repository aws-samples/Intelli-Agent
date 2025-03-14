import json
import logging
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.paginate import TokenEncoder
from constant import EmbeddingModelType, ModelProvider
from utils.ddb_utils import (
    initiate_chatbot,
    initiate_embedding_model,
    initiate_index,
    initiate_rerank_model,
    initiate_vlm_model,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
region_name = os.environ.get("AWS_REGION")
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
dynamodb = boto3.resource("dynamodb", region_name=region_name)
dynamodb_client = boto3.client("dynamodb")
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
chatbot_table_name = os.getenv("CHATBOT_TABLE_NAME", "chatbot")
chatbot_table = dynamodb.Table(chatbot_table_name)
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))

DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
ROOT_RESOURCE = "/chatbot-management"
# CHATBOT_RESOURCE = "/chatbot-management/chatbot"
EMBEDDING_MODELS_RESOURCE = f"{ROOT_RESOURCE}/embeddings"
# INDEXES_RESOURCE = f"{ROOT_RESOURCE}/indexes"
CHATBOTS_RESOURCE = f"{ROOT_RESOURCE}/chatbots"
# DETAILS_RESOURCE = f"{ROOT_RESOURCE}/chatbot"
CHATBOTCHECK_RESOURCE = f"{ROOT_RESOURCE}/check-chatbot"
CHATBOTINDEXCHECK_RESOURCE = f"{ROOT_RESOURCE}/check-index"
CHATBOTLISTINDEX_RESOURCE = f"{ROOT_RESOURCE}/indexes"
CHATBOTEDIT_RESOURCE = f"{ROOT_RESOURCE}/edit-chatbot"
CHATBOTCHECK_DEFAULT = f"{ROOT_RESOURCE}/default-chatbot"
logger = logging.getLogger(__name__)
encoder = TokenEncoder()

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}


def create_chatbot(event, group_name):
    """Create a new chatbot with associated embedding, rerank, and VLM models.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with chatbot creation details
    """
    request_body = json.loads(event["body"])
    chatbot_id = request_body.get("chatbotId", group_name.lower())
    create_time = str(datetime.now(timezone.utc))
    chatbot_description = request_body.get(
        "chatbotDescription", "Answer question based on search result"
    )

    # Initiate embedding model
    embedding_model_info = request_body.get("embeddingModelInfo", {})
    embedding_model_provider = embedding_model_info.get(
        "modelProvider", ModelProvider.BEDROCK.value
    )
    embedding_base_url = embedding_model_info.get("baseUrl", "")
    embedding_api_key_arn = embedding_model_info.get("apiKeyArn", "")
    embedding_model_id = embedding_model_info.get("modelId", embedding_endpoint)
    embedding_additional_config = embedding_model_info.get(
        "additionalConfig", ""
    )

    initiate_embedding_model(
        model_table=model_table,
        group_name=group_name,
        model_id=f"{chatbot_id}-embedding",
        embedding_endpoint=embedding_model_id,
        model_provider=embedding_model_provider,
        base_url=embedding_base_url,
        api_key_arn=embedding_api_key_arn,
        create_time=create_time,
        additional_config=embedding_additional_config,
    )

    # Initialize rerank model
    rerank_model_info = request_body.get("rerankModelInfo", {})
    rerank_model_provider = rerank_model_info.get(
        "modelProvider", ModelProvider.BEDROCK.value
    )
    rerank_base_url = rerank_model_info.get("baseUrl", "")
    rerank_api_key_arn = rerank_model_info.get("apiKeyArn", "")
    rerank_model_id = rerank_model_info.get("modelId", "")
    rerank_additional_config = rerank_model_info.get("additionalConfig", "")

    initiate_rerank_model(
        model_table=model_table,
        group_name=group_name,
        model_id=f"{chatbot_id}-rerank",
        rerank_endpoint=rerank_model_id,
        model_provider=rerank_model_provider,
        base_url=rerank_base_url,
        api_key_arn=rerank_api_key_arn,
        create_time=create_time,
        additional_config=rerank_additional_config,
    )

    # Initialize VLM model
    vlm_model_info = request_body.get("vlmModelInfo", {})
    vlm_model_provider = vlm_model_info.get(
        "modelProvider", ModelProvider.BEDROCK.value
    )
    vlm_base_url = vlm_model_info.get("baseUrl", "")
    vlm_api_key_arn = vlm_model_info.get("apiKeyArn", "")
    vlm_model_id = vlm_model_info.get("modelId", "")

    initiate_vlm_model(
        model_table=model_table,
        group_name=group_name,
        model_id=f"{chatbot_id}-vlm",
        vlm_endpoint=vlm_model_id,
        model_provider=vlm_model_provider,
        base_url=vlm_base_url,
        api_key_arn=vlm_api_key_arn,
        create_time=create_time,
    )

    # Create indexes and associate with chatbot
    index = request_body.get(
        "index",
        {
            "qq": {
                "admin-qq-default": "Answer question based on search result"
            },
            "qd": {
                "admin-qd-default": "Answer question based on search result"
            },
            "intention": {
                "admin-intention-default": "Answer question based on search result"
            },
        },
    )

    index_ids = []
    indexes = []
    for index_type in index:
        type_index_ids = [
            index_id.lower() for index_id in list(index[index_type].keys())
        ]
        index_ids.extend(type_index_ids)

        initiate_chatbot(
            chatbot_table=chatbot_table,
            group_name=group_name,
            chatbot_id=chatbot_id,
            chatbot_description=chatbot_description,
            index_type=index_type,
            index_id_list=type_index_ids,
            embedding_model_id=f"{chatbot_id}-embedding",
            rerank_model_id=f"{chatbot_id}-rerank",
            vlm_model_id=f"{chatbot_id}-vlm",
            create_time=create_time,
        )

        for index_id in type_index_ids:
            tag = index_id
            initiate_index(
                index_table=index_table,
                group_name=group_name,
                index_id=index_id,
                model_id=f"{chatbot_id}-embedding",
                index_type=index_type,
                tag=tag,
                description=index[index_type].get(index_id),
                create_time=create_time,
            )

            indexes.append(
                {
                    "id": index_id,
                    "type": index_type,
                    "description": index[index_type].get(index_id),
                    "tag": tag,
                }
            )

    return {
        "groupName": group_name,
        "chatbotId": chatbot_id,
        "updateTime": create_time,
        "embeddingModel": {
            "modelId": f"{chatbot_id}-embedding",
            "modelEndpoint": embedding_model_id,
            "modelName": embedding_model_id,
            "modelProvider": embedding_model_provider,
            "baseUrl": embedding_base_url,
        },
        "rerankModel": {
            "modelId": f"{chatbot_id}-rerank",
            "modelEndpoint": rerank_model_id,
            "modelName": "",
            "modelProvider": rerank_model_provider,
            "baseUrl": rerank_base_url,
        },
        "vlmModel": {
            "modelId": f"{chatbot_id}-vlm",
            "modelEndpoint": vlm_model_id,
            "modelName": "",
            "modelProvider": vlm_model_provider,
            "baseUrl": vlm_base_url,
        },
        "indexes": indexes,
        "message": "OK",  # Keep this for frontend compatibility
    }


def list_embedding_models():
    """List available embedding models.

    Returns:
        List of available embedding model types
    """
    return [EmbeddingModelType.BEDROCK_TITAN_V1]


def get_model_info(group_name, chatbot_id, model_type):
    """Get model information for a specific model type.

    Args:
        group_name: User group name
        chatbot_id: Chatbot ID
        model_type: Type of model (embedding, rerank, vlm)

    Returns:
        Dict with model information
    """
    model_id = f"{chatbot_id}-{model_type}"
    model_item = model_table.get_item(
        Key={"groupName": group_name, "modelId": model_id}
    ).get("Item", {})

    model_parameter = model_item.get("parameter", {})

    return {
        "modelId": model_id,
        "modelEndpoint": model_parameter.get("ModelEndpoint", ""),
        "modelName": model_parameter.get("ModelName", ""),
        "modelProvider": model_parameter.get("ModelProvider", ""),
        "baseUrl": model_parameter.get("BaseUrl", ""),
    }


def list_chatbots(event, group_name):
    """List all chatbots for a group with pagination.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with paginated chatbot list
    """
    max_items = get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "StartingToken")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    paginator = dynamodb_client.get_paginator("query")
    # chatbot->index->model
    response_iterator = paginator.paginate(
        TableName=chatbot_table_name,
        PaginationConfig=config,
        KeyConditionExpression="groupName = :GroupName",
        ExpressionAttributeValues={":GroupName": {"S": group_name}},
        ScanIndexForward=False,
    )

    chatbots = []
    last_evaluated_key = None

    for page in response_iterator:
        page_items = page["Items"]

        for item in page_items:
            chatbot_id = item.get("chatbotId", {"S": ""})["S"]
            update_time = item.get("updateTime", {"S": ""})["S"]

            # Get model information
            embedding_model = get_model_info(
                group_name, chatbot_id, "embedding"
            )
            rerank_model = get_model_info(group_name, chatbot_id, "rerank")
            vlm_model = get_model_info(group_name, chatbot_id, "vlm")

            # Get indexes
            indexes = get_chatbot_indexes(group_name, chatbot_id)

            chatbot = {
                "chatbotId": chatbot_id,
                "groupName": group_name,
                "updateTime": update_time,
                "embeddingModel": embedding_model,
                "rerankModel": rerank_model,
                "vlmModel": vlm_model,
                "indexes": indexes,
            }
            chatbots.append(chatbot)

        if "LastEvaluatedKey" in page:
            last_evaluated_key = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )
        break

    # Sort by update time (newest first)
    chatbots.sort(key=lambda x: x["updateTime"], reverse=True)

    result = {
        "items": chatbots,
        "count": len(chatbots),
        "chatbotIds": [chatbot["chatbotId"] for chatbot in chatbots],
        "config": config,
    }

    if last_evaluated_key:
        result["lastEvaluatedKey"] = last_evaluated_key

    return result


def get_chatbot_indexes(group_name, chatbot_id):
    """Get indexes associated with a chatbot.

    Args:
        group_name: User group name
        chatbot_id: Chatbot ID

    Returns:
        List of index information
    """
    chatbot_item = chatbot_table.get_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    ).get("Item", {})

    chatbot_index_ids = chatbot_item.get("indexIds", {})
    indexes = []

    for index_type, value in chatbot_index_ids.items():
        index_values = value.get("value", {})

        for index_id, tag in index_values.items():
            index_detail = index_table.get_item(
                Key={"groupName": group_name, "indexId": index_id}
            ).get("Item", {})

            indexes.append(
                {
                    "id": index_id,
                    "type": index_type,
                    "description": index_detail.get("description", ""),
                    "tag": tag,
                }
            )

    return indexes


def get_chatbot(event, group_name):
    """Get detailed information about a specific chatbot.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with chatbot details
    """
    chatbot_id = event.get("pathParameters", {}).get("proxy")
    if not chatbot_id:
        return {
            "groupName": group_name,
            "chatbotId": None,
            "updateTime": "",
            "embeddingModel": {},
            "rerankModel": {},
            "vlmModel": {},
            "indexes": [],
        }

    chatbot_item = chatbot_table.get_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    ).get("Item", {})

    if not chatbot_item:
        return {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "updateTime": "",
            "embeddingModel": {},
            "rerankModel": {},
            "vlmModel": {},
            "indexes": [],
        }

    # Get model information
    embedding_model = get_model_info(group_name, chatbot_id, "embedding")
    rerank_model = get_model_info(group_name, chatbot_id, "rerank")
    vlm_model = get_model_info(group_name, chatbot_id, "vlm")

    # Get indexes
    indexes = get_chatbot_indexes(group_name, chatbot_id)

    return {
        "groupName": group_name,
        "chatbotId": chatbot_id,
        "updateTime": chatbot_item.get("updateTime", ""),
        "embeddingModel": embedding_model,
        "rerankModel": rerank_model,
        "vlmModel": vlm_model,
        "indexes": indexes,
    }


def delete_chatbot(event, group_name):
    """Delete a chatbot.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        DynamoDB response
    """
    chatbot_id = event["path"].split("/")[-1]

    # TODO: Consider deleting associated models and indexes

    response = chatbot_table.delete_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    )
    return response


def validate_index(event, group_name):
    """Validate if an index can be used with a specific model.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with validation result
    """
    input_body = json.loads(event["body"])
    model = input_body.get("model")
    index = input_body.get("index")

    response = index_table.scan(FilterExpression=Attr("indexId").eq(index))
    items = response.get("Items", [])

    if items:
        for item in items:
            if item["groupName"] != group_name:
                return {
                    "result": False,
                    "reason": 1,
                }  # Index belongs to another group
            elif item.get("modelIds", {}).get("embedding", "") != model:
                return {
                    "result": False,
                    "reason": 2,
                }  # Index uses different model

    return {"result": True, "reason": None}


def edit_chatbot(event, group_name):
    """Edit an existing chatbot.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with edit result
    """
    input_body = json.loads(event["body"])
    index = input_body["index"]
    chatbot_id = input_body["chatbotId"]
    model_id = input_body["modelId"]
    chatbot_description = input_body.get(
        "chatbotDescription", "Answer question based on search result"
    )
    update_time = str(datetime.now(timezone.utc))

    # 1. Delete old indexes
    chatbot_item = chatbot_table.get_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    ).get("Item", {})

    index_dict = chatbot_item.get("indexIds", {})
    for key in index_dict:
        value = index_dict.get(key, {}).get("value", {})
        for k in value:
            logger.info(f"Deleting index: {k}")
            index_table.delete_item(
                Key={
                    "groupName": group_name,
                    "indexId": k,
                }
            )

    # 2. Update chatbot and create new indexes
    index_ids = []
    for index_type in index:
        type_index_ids = [
            index_id.lower() for index_id in list(index[index_type].keys())
        ]
        index_ids.extend(type_index_ids)

        initiate_chatbot(
            chatbot_table,
            group_name,
            chatbot_id,
            chatbot_description,
            index_type,
            type_index_ids,
            update_time,
        )

        for index_id in type_index_ids:
            tag = index_id
            initiate_index(
                index_table,
                group_name,
                index_id,
                f"{chatbot_id}-embedding",
                index_type,
                tag,
                index[index_type].get(index_id),
                update_time,
            )

    return {
        "chatbotId": chatbot_id,
        "groupName": group_name,
        "indexIds": index_ids,
        "message": "OK",
    }


def list_indexes(event, group_name):
    """List indexes associated with a chatbot.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with index list
    """
    chatbot_id = event.get("path", "").split("/").pop()
    indexes = get_chatbot_indexes(group_name, chatbot_id)

    return {
        "items": indexes,
        "count": len(indexes),
        "indexes": indexes,  # Added for consistency with other endpoints
    }


def validate_default_chatbot(event, group_name):
    """Check if a default chatbot exists for the group.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Boolean indicating if default chatbot exists
    """
    chatbot_item = chatbot_table.get_item(
        Key={"groupName": group_name, "chatbotId": group_name.lower()}
    ).get("Item")

    return True if chatbot_item else False


def validate_chatbot(event, group_name):
    """Validate chatbot creation parameters.

    Args:
        event: API Gateway event
        group_name: User group name

    Returns:
        Dict with validation result
    """
    input_body = json.loads(event["body"])
    chatbot_id = input_body.get("chatbotId")
    chatbot_type = input_body.get("type")
    model = input_body.get("model")
    index = input_body.get("index")

    if not chatbot_id or not chatbot_type or not model or not index:
        logger.error("Invalid parameters.")
        raise ValueError("Missing required parameters")

    # Check if chatbot already exists for creation
    if chatbot_type == "create":
        chatbot_item = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
        ).get("Item")
        if chatbot_item:
            return {"result": False, "item": "chatbotName", "reason": 0}

    # Validate indexes
    index_set = set()
    for index_type in index:
        index_set |= set(list(index[index_type].split(",")))

    response = index_table.scan(
        FilterExpression=Attr("indexId").is_in(list(index_set))
    )
    items = response.get("Items", [])

    if items:
        for item in items:
            if item["groupName"] != group_name:
                return {
                    "result": False,
                    "item": find_invalid_index(index, item["indexId"]),
                    "reason": 1,  # Index belongs to another group
                }
            elif item.get("modelIds", {}).get("embedding", "") != model:
                return {
                    "result": False,
                    "item": find_invalid_index(index, item["indexId"]),
                    "reason": 2,  # Index uses different model
                }

    return {"result": True, "item": None, "reason": None}


def find_invalid_index(index, index_id):
    """Find which index category contains the invalid index.

    Args:
        index: Dict of index categories
        index_id: ID of the invalid index

    Returns:
        Index ID if found, None otherwise
    """
    for key, value in index.items():
        if index_id in value.split(","):
            return index_id
    return None


def get_query_parameter(event, parameter_name, default_value=None):
    """Get a query parameter from the event.

    Args:
        event: API Gateway event
        parameter_name: Name of the parameter
        default_value: Default value if parameter not found

    Returns:
        Parameter value or default
    """
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value


def lambda_handler(event, context):
    """Main handler for chatbot management API.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        logger.debug(f"Event: {event}")

        # Get user information from authorizer
        authorizer_type = (
            event["requestContext"].get("authorizer", {}).get("authorizerType")
        )
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])

        if "use_api_key" in claims:
            group_name = get_query_parameter(event, "GroupName", "Admin")
        else:
            group_name = claims[
                "cognito:groups"
            ]  # Assume user is in only one group

        http_method = event["httpMethod"]
        resource = event["resource"]
        output = {}

        # Route request to appropriate handler
        if resource == EMBEDDING_MODELS_RESOURCE:
            output = list_embedding_models()
        elif resource.startswith(CHATBOTS_RESOURCE):
            if http_method == "POST":
                output = create_chatbot(event, group_name)
            elif http_method == "GET":
                if resource == CHATBOTS_RESOURCE:
                    output = list_chatbots(event, group_name)
                else:
                    output = get_chatbot(event, group_name)
            elif http_method == "DELETE":
                output = delete_chatbot(event, group_name)
        elif resource == CHATBOTCHECK_RESOURCE:
            output = validate_chatbot(event, group_name)
        elif resource == CHATBOTCHECK_DEFAULT:
            output = validate_default_chatbot(event, group_name)
        elif resource == CHATBOTINDEXCHECK_RESOURCE:
            output = validate_index(event, group_name)
        elif resource == CHATBOTEDIT_RESOURCE:
            output = edit_chatbot(event, group_name)
        elif resource.startswith(CHATBOTLISTINDEX_RESOURCE):
            output = list_indexes(event, group_name)

        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps({"error": str(e)}),
        }
