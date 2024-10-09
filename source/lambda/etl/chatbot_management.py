import json
import logging
import os
import time
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.paginate import TokenEncoder
from constant import IndexType, EmbeddingModelType
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
# CHATBOT_RESOURCE = "/chatbot-management/chatbot"
EMBEDDING_MODELS_RESOURCE = f"{ROOT_RESOURCE}/embeddings"
INDEXES_RESOURCE = f"{ROOT_RESOURCE}/indexes"
CHATBOTS_RESOURCE = f"{ROOT_RESOURCE}/chatbots"
# DETAILS_RESOURCE = f"{ROOT_RESOURCE}/chatbot"
CHATBOTCHECK_RESOURCE = f"{ROOT_RESOURCE}/check-chatbot"
logger = logging.getLogger(__name__)
encoder = TokenEncoder()

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}


def create_chatbot(event, group_name):
    request_body = json.loads(event["body"])
    chatbot_id = request_body.get("chatbotId", group_name.lower())
    chatbot_description = request_body.get(
        "chatbotDescription", "Answer question based on search result"
    )
    chatbot_embedding = request_body.get("modelId", embedding_endpoint)
    model_id = f"{chatbot_id}-embedding"
    # model_id = request_body.get("modelId", f"{chatbot_id}-embedding")
    create_time = str(datetime.now(timezone.utc))

    model_type = initiate_model(
        model_table, group_name, model_id, chatbot_embedding, create_time)

    index_id_list = {}
    # Iterate over all enum members and create DDB metadata
    for member in IndexType.__members__.values():
        index_type = member.value
        index_ids = (
            request_body.get("index", {})
            .get(index_type, f"{chatbot_id}-{index_type}-default")
            # .get("index", f"{chatbot_id}-{index_type}-default")
        )
        index_id_list[index_type] = index_ids
        initiate_chatbot(
            chatbot_table,
            group_name,
            chatbot_id,
            chatbot_description,
            index_type,
            index_ids.split(","),
            create_time,
        )
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

    return {
        "chatbotId": chatbot_id,
        "groupName": group_name,
        "indexIds": index_id_list,
        "modelType": model_type,
        "Message": "OK",  # Need to be OK for the frontend to know the chatbot is created successfully and redirect to the chatbot management page
    }


def __list_embedding_model():
    return [EmbeddingModelType.BEDROCK_TITAN_V1]


def __list_chatbot(event, group_name):
    max_items = __get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = __get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = __get_query_parameter(event, "StartingToken")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = dynamodb_client.get_paginator("query")
    # chatbot->index->model
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
            chatbot_id = item.get("chatbotId", {"S": ""})["S"]
            index_dict = list(item.get("indexIds", {}).get("M", {}).get(
                "intention", {}).get("M", {}).get("value", {}).values())[0]
            index_id = list(index_dict.keys())[0]
            index_table_item = index_table.get_item(
                Key={
                    "groupName": group_name,
                    "indexId": index_id,
                }
            )
            model_id = index_table_item.get("Item", {}).get(
                "modelIds", {}).get("embedding", "")
            item_json["ChatbotId"] = chatbot_id
            chatbot_model_item = model_table.get_item(
                Key={
                    "groupName": group_name,
                    "modelId": f"{chatbot_id}-embedding",
                }
            ).get("Item")
            item_json["ModelName"] = chatbot_model_item.get("parameter", {}).get(
                "ModelEndpoint", ""
            )
            item_json["ModelId"] = chatbot_model_item.get("modelId", "")
            item_json["LastModifiedTime"] = item.get(
                "updateTime", {"S": ""})["S"]
            page_json.append(item_json)
        page_json.sort(key=lambda x: x["LastModifiedTime"], reverse=True)
        output["Items"] = page_json
        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )
        break

    output["Config"] = config
    output["Count"] = len(page_json)
    output["chatbot_ids"] = [item["ChatbotId"] for item in page_json]
    return output


def merge_index(chatbot_index_ids, key):
    return ",".join(list(chatbot_index_ids.get(key, {}).get("value", {}).values()))


def __get_chatbot(event, group_name):
    chatbot_id = event.get("pathParameters", {}).get("proxy")
    if chatbot_id:
        chatbot_item = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
        ).get("Item")
        model_item = model_table.get_item(
            Key={"groupName": group_name, "modelId": f'{chatbot_id}-embedding'}
        ).get("Item")
    else:
        chatbot_item = None
        model_item = None

    if chatbot_item and model_item:
        chatbot_index_ids = chatbot_item.get("indexIds", {})
        model = model_item.get("parameter", {})
        model_endpoint = model.get("ModelEndpoint", {})
        model_name = model.get("ModelName", {})
        response = {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "model": {
                "model_endpoint": model_endpoint,
                "model_name": model_name
            },
            "index": {
                "intention": merge_index(chatbot_index_ids, "intention"),
                "qq":  merge_index(chatbot_index_ids, "qq"),
                "qd": merge_index(chatbot_index_ids, "qd")
            },
        }
    else:
        response = {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "index": {
                "inention": f"{chatbot_id}-intention-default",
                "qq": f"{chatbot_id}-qq-default",
                "qd": f"{chatbot_id}-qd-default"
            },
        }
    return response


def __delete_chatbot(event, group_name):
    chatbot_id = event["path"].split("/")[-1]

    response = chatbot_table.delete_item(
        Key={"groupName": group_name, "chatbotId": chatbot_id}
    )
    return response


def lambda_handler(event, context):
    # logger.info(f"event:{event}")
    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])

    if "use_api_key" in claims:
        group_name = __get_query_parameter(event, "GroupName", "Admin")
    else:
        email = claims["email"]
        group_name = claims["cognito:groups"]  # Agree to only be in one group
    http_method = event["httpMethod"]
    resource: str = event["resource"]

    if resource == EMBEDDING_MODELS_RESOURCE:
        output = __list_embedding_model()
    elif resource.startswith(CHATBOTS_RESOURCE):
        if http_method == "POST":
            output = create_chatbot(event, group_name)
        elif http_method == "GET":
            if resource == CHATBOTS_RESOURCE:
                output = __list_chatbot(event, group_name)
            else:
                output = __get_chatbot(event, group_name)
        elif http_method == "DELETE":
            output = __delete_chatbot(event, group_name)
    elif resource == CHATBOTCHECK_RESOURCE:
        output = __validate_chatbot(event, group_name)

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


def __validate_chatbot(event, group_name):
    input_body = json.loads(event["body"])
    # chabotName
    chatbot_id = input_body.get("chatbotId")
    chatbot_type = input_body.get("type")
    model = input_body.get("model")
    index = input_body.get("index")
    if not chatbot_id or not chatbot_type or not model or not index:
        logger.error("Invalid paramater.")
        raise

    if chatbot_type == "create":
        chatbot_item = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
        ).get("Item")
        if chatbot_item:
            return {
                "result": False,
                "item": "chatbotName",
                "Message": "repeat"
            }
    # index
    # index_ids=[]
    index_set = set()
    for member in IndexType.__members__.values():
        index_type = member.value
        index_list = index.get(index_type).split(",")
        # index_ids.append({
        #     index_type: index_list
        # })
        index_set |= set(index_list)
        # index_ids.append(index.get(index_type))
        # .get("index", f"{chatbot_id}-{index_type}-default")

    response = index_table.scan(
        FilterExpression=Attr('indexId').is_in(list(index_set))
    )
    items = response.get('Items')
    if items:
        for item in items:
            if item['groupName'] != group_name:
                # 其他人用了index，报错
                return {
                    "result": False,
                    "item": __find_key(index, item['indexId']),
                    "Message": "repeat in other group name"
                }
            else:
                if item.get("modelIds", {}).get("embedding", "") != model:
                    # 自己用了index，但是模型 不对，报错
                    return {
                        "result": False,
                        "item": __find_key(index, item['indexId']),
                        "Message": "used by other models"
                    }
    return {
        "result": True,
        "item": None,
        "Message": None
    }


def __find_key(index, index_id):
    for key, value in index.items():
        if index_id in value.split(","):
            return key
    return None

# def __chatbot_details(chatbot_id, group_name):
#     res={chatbot_id:chatbot_id}
#     index = chatbot_table.get_item(
#          Key={"groupName": group_name,
#               "chatbotId": chatbot_id
#               }
#         ).get("Item",{}).get("indexIds")
#     for key, value in index.items():
#         value.get("value",{}).get("M",{}).keys()
#         res[key]=""
#     return res


def __get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value
