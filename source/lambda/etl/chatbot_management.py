import json
import logging
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.paginate import TokenEncoder
from common_logic.common_utils.constant import EmbeddingModelType
from constant import IndexType
from utils.ddb_utils import (
    initiate_chatbot,
    initiate_index,
    initiate_model,
    is_chatbot_existed,
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
EMBEDDING_MODELS_RESOURCE = f"{ROOT_RESOURCE}/embeddings"
INDEXES_RESOURCE = f"{ROOT_RESOURCE}/indexes"
CHATBOTS_RESOURCE = f"{ROOT_RESOURCE}/chatbots"
logger = logging.getLogger(__name__)
encoder = TokenEncoder()

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}


def get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value


def __create_chatbot(event, group_name):
    request_body = json.loads(event["body"])
    chatbot_id = request_body.get("chatbotId", group_name.lower())
    chatbot_description = request_body.get(
        "chatbotDescription", "Answer question based on search result"
    )
    chatbot_embedding = request_body.get("chatbotEmbedding", embedding_endpoint)
    model_id = f"{chatbot_id}-embedding"
    create_time = str(datetime.now(timezone.utc))

    initiate_model(model_table, group_name, model_id, chatbot_embedding, create_time)

    index_id_list = {}
    # Iterate over all enum members and create DDB metadata
    for member in IndexType.__members__.values():
        index_type = member.value
        index_ids = request_body.get(index_type, f"{chatbot_id}-{index_type}-default")
        index_id_list[index_type] = index_ids
        for index_id in index_ids.split(","):
            tag = index_id
            initiate_index(
                index_table,
                group_name,
                index_id,
                model_id,
                index_type,
                tag,
                create_time,
                chatbot_description,
            )
            initiate_chatbot(
                chatbot_table,
                group_name,
                chatbot_id,
                index_id,
                index_type,
                tag,
                create_time,
            )

    return {
        "chatbotId": chatbot_id,
        "groupName": group_name,
        "indexIds": index_id_list,
        "message": "Chatbot created",
    }


def __list_embedding_model():
    return [EmbeddingModelType.BEDROCK_TITAN_V1]


def __list_chatbot(event, group_name):
    max_items = get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "StartingToken")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = dynamodb_client.get_paginator("query")

    response_iterator = paginator.paginate(
        TableName=chatbot_table_name,
        PaginationConfig=config,
        KeyConditionExpression="groupName = :GroupName",
        ExpressionAttributeValues={":GroupName": {"S": group_name}},
        ScanIndexForward=False,
    )

    output = {}

    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            item_json["chatbotId"] = item.get("chatbotId", {"S": ""})["S"]
            page_json.append(item_json)
        output["Items"] = page_json
        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )
        break

    output["Config"] = config
    output["Count"] = len(page_json)
    output = {"chatbot_ids": ["Admin"]}
    return output


def __get_chatbot(event, group_name):
    return {"Message": "Not Implemented"}


def __delete_chatbot(event, group_name):
    return {"Message": "Not Implemented"}


def lambda_handler(event, context):
    logger.info(f"event:{event}")

    group_name = "Admin"
    http_method = event["httpMethod"]
    resource: str = event["resource"]
    if resource == EMBEDDING_MODELS_RESOURCE:
        output = __list_embedding_model()
    elif resource.startswith(CHATBOTS_RESOURCE):
        if http_method == "POST":
            output = __create_chatbot(event, group_name)
        elif http_method == "GET":
            if resource == CHATBOTS_RESOURCE:
                output = __list_chatbot(event, group_name)
            else:
                output = __get_chatbot(event, group_name)
        elif http_method == "DELETE":
            output = __delete_chatbot(event, group_name)

    try:
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }