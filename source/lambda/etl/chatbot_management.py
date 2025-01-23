import json
import logging
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.paginate import TokenEncoder
from constant import IndexType, EmbeddingModelType
from utils.ddb_utils import (
    initiate_chatbot,
    initiate_index,
    initiate_model
)
from constant import ModelProvider


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
    request_body = json.loads(event["body"])
    chatbot_id = request_body.get("chatbotId", group_name.lower())
    model_provider = request_body.get("modelProvider", ModelProvider.BEDROCK.value)
    base_url = request_body.get("baseUrl", "")
    api_endpoint = request_body.get("apiEndpoint", "")
    api_key_arn = request_body.get("apiKeyArn", "")
    chatbot_description = request_body.get(
        "chatbotDescription", "Answer question based on search result"
    )
    chatbot_embedding = request_body.get("modelId", embedding_endpoint)
    model_id = f"{chatbot_id}-embedding"
    # model_id = request_body.get("modelId", f"{chatbot_id}-embedding")
    create_time = str(datetime.now(timezone.utc))

    model_type = initiate_model(
        model_table,
        group_name,
        model_id,
        chatbot_embedding,
        model_provider,
        base_url,
        api_endpoint,
        api_key_arn,
        create_time
    )
    index = request_body.get("index", {"qq":{"admin-qq-default": "Answer question based on search result"},"qd":{"admin-qd-default": "Answer question based on search result"},"intention":{"admin-intention-default": "Answer question based on search result"}})
    for index_type in index:
        index_ids = list(index[index_type].keys())
        initiate_chatbot(
            chatbot_table,
            group_name,
            chatbot_id,
            chatbot_description,
            index_type,
            index_ids,
            create_time,
        )
        for index_id in index_ids:
            tag = index_id
            initiate_index(
                index_table,
                group_name,
                index_id,
                model_id,
                index_type,
                tag,
                index.get(index_type,{}).get(index_id),
                create_time
            )
    return {
        "chatbotId": chatbot_id,
        "groupName": group_name,
        "indexIds": index_ids,
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

    update_time = datetime.fromisoformat(chatbot_item.get("updateTime", "")).strftime("%Y/%m/%d %H:%M:%S")
    if chatbot_item and model_item:
        chatbot_index_ids = chatbot_item.get("indexIds", {})
        model = model_item.get("parameter", {})
        model_endpoint = model.get("ModelEndpoint", {})
        model_name = model.get("ModelName", {})
        chatbot_index = []
        for key, value in chatbot_index_ids.items():
            v = value.get('value',{})
            # name = list(v.keys())[0]
            for index in list(v.keys()):
                index_detail = index_table.get_item(
                    Key={"groupName": group_name, "indexId": index}
                ).get("Item")

                chatbot_index.append({
                    "name": index,
                    "type": key,
                    "description": index_detail.get("description", ""),
                    "tag": v.get(index)
                })
        response = {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "updateTime": update_time,
            "model": {
                "model_endpoint": model_endpoint,
                "model_name": model_name
            },
            "index": chatbot_index,
        }
    else:
        response = {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "updateTime": update_time,
            "index": chatbot_index,
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
    output = {}
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
    elif resource == CHATBOTCHECK_DEFAULT:
        output = __validate_default_chatbot(event, group_name)
    elif resource == CHATBOTINDEXCHECK_RESOURCE:
        output = __validate_index(event, group_name)
    elif resource == CHATBOTEDIT_RESOURCE:
        output = __edit_chatbot(event, group_name)
    elif resource.startswith(CHATBOTLISTINDEX_RESOURCE):
        output = __list_index(event, group_name)

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
    
def __validate_index(event, group_name):
    input_body = json.loads(event["body"])
    model = input_body.get("model")
    index = input_body.get("index")
    response = index_table.scan(
        FilterExpression=Attr('indexId').eq(index)
    )
    items = response.get('Items')
    if items:
        for item in items:
            if item['groupName'] != group_name:
                return {
                    "result": False,
                    "reason": 1
                }
            else:
                if item.get("modelIds", {}).get("embedding", "") != model:
                    return {
                        "result": False,
                        "reason": 2
                    }
    return {
        "result": True,
        "reason": None
    }

def __edit_chatbot(event, group_name):
    input_body = json.loads(event["body"])
    index = input_body["index"]
    chatbot_id = input_body["chatbotId"]
    model_id = input_body["modelId"]
    chatbot_description = input_body.get(
        "chatbotDescription", "Answer question based on search result"
    )
    update_time = str(datetime.now(timezone.utc))
    # {
    #       chatbotId: chatbotDetail.chatbotId,
    #       modelId: chatbotDetail.model,
    #       modelName: chatbotDetail.model,
    #       indexList: tmpIndexList.map(({status,...rest})=> rest),
    #     }
    # 1.删除index表旧的index
    index_dict = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
    ).get("Item").get("indexIds",{})
    for key in index_dict:
        value = index_dict.get(key,{}).get("value",{})
        for k in value:
            print(f"start delete index>>>>: {k}")
            index_table.delete_item(
                Key={
                    "groupName": group_name,
                    "indexId": k,
                }
            )
    

    # 2.更新chatbot表
    # indexList
    for index_type in index:
        index_ids = list(index[index_type].keys())
        initiate_chatbot(
            chatbot_table,
            group_name,
            chatbot_id,
            chatbot_description,
            index_type,
            index_ids,
            update_time,
        )
        for index_id in index_ids:
            tag = index_id
            initiate_index(
                index_table,
                group_name,
                index_id,
                f"{chatbot_id}-embedding",
                index_type,
                tag,
                index.get(index_type,{}).get(index_id),
                update_time
            )

    # 3.更新index表
    return {
        "chatbotId": chatbot_id,
        "groupName": group_name,
        "indexIds": index_ids,
        "Message": "OK",  # Need to be OK for the frontend to know the chatbot is created successfully and redirect to the chatbot management page
    }

def __list_index(event, group_name):
    chatbot_id = event.get("path", "").split("/").pop()
    max_items = __get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = __get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = __get_query_parameter(event, "StartingToken")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    chatbot_item = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
        ).get("Item")
    chatbot_index_ids = chatbot_item.get("indexIds", {})
    index_list = []
    for key, value in chatbot_index_ids.items():
        v = value.get('value',{})
        # name = list(v.keys())[0]
        for index in list(v.keys()):
            index_detail = index_table.get_item(
                Key={"groupName": group_name, "indexId": index}
            ).get("Item")

            index_list.append({
                "name": index,
                "type": key,
                "description": index_detail.get("description", ""),
                "tag": v.get(index)
            })
    output={}
    # # Use query after adding a filter
    # paginator = dynamodb_client.get_paginator("query")
    # # chatbot->index->model
    # response_iterator = paginator.paginate(
    #     TableName=chatbot_table_name,
    #     PaginationConfig=config,
    #     KeyConditionExpression="groupName = :GroupName AND chatbotId = :ChatbotId",
    #     ExpressionAttributeValues={":GroupName": {"S": group_name},":ChatbotId": {"S": chatbot_id}},
    #     ScanIndexForward=False,
    # )

    # output = {}

    # for page in response_iterator:
    #     page_items = page["Items"]
    #     page_json = []
    #     for item in page_items:
    #         item_json = {}
    #         chatbot_index_ids = item.get("indexIds", {})
    #         for key, value in chatbot_index_ids.items():
    #             v = value.get('value',{})
    #             # name = list(v.keys())[0]
    #             for index in list(v.keys()):
    #                 index_detail = index_table.get_item(
    #                     Key={"groupName": group_name, "indexId": index}
    #                 ).get("Item")

    #                 page_json.append({
    #                     "name": index,
    #                     "type": key,
    #                     "description": index_detail.get("description", ""),
    #                     "tag": v.get(index)
    #                 })
    #         # item_json["ChatbotId"] = chatbot_id
    #         # chatbot_model_item = model_table.get_item(
    #         #     Key={
    #         #         "groupName": group_name,
    #         #         "modelId": f"{chatbot_id}-embedding",
    #         #     }
    #         # ).get("Item")
    #         # item_json["ModelName"] = chatbot_model_item.get("parameter", {}).get(
    #         #     "ModelEndpoint", ""
    #         # )
    #         # item_json["ModelId"] = chatbot_model_item.get("modelId", "")
    #         # item_json["LastModifiedTime"] = item.get(
    #         #     "updateTime", {"S": ""})["S"]
    #         page_json.append(item_json)
    #     output["Items"] = page_json
    #     if "LastEvaluatedKey" in page:
    #         output["LastEvaluatedKey"] = encoder.encode(
    #             {"ExclusiveStartKey": page["LastEvaluatedKey"]}
    #         )
    #     break

    output["Items"] = index_list
    output["Count"] = len(index_list)
    return output

def __validate_default_chatbot(event, group_name):
    chatbot_item = chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": group_name.lower()}
        ).get("Item")
    return True if chatbot_item else False

def __validate_chatbot(event, group_name):
    input_body = json.loads(event["body"])
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
                "reason": 0
            }
    index_set = set()
    for index_type in index:
        index_set |= set(list(index[index_type].split(",")))

    response = index_table.scan(
        FilterExpression=Attr('indexId').is_in(list(index_set))
    )
    items = response.get('Items')
    if items:
        for item in items:
            if item['groupName'] != group_name:
                return {
                    "result": False,
                    "item": __find_invalid_index(index, item['indexId']),
                    "reason": 1
                }
            else:
                if item.get("modelIds", {}).get("embedding", "") != model:
                    return {
                        "result": False,
                        "item": __find_invalid_index(index, item['indexId']),
                        "reason": 2
                    }
    return {
        "result": True,
        "item": None,
        "reason": None
    }


def __find_invalid_index(index, index_id):
    for key, value in index.items():
        if index_id in value.split(","):
            return index_id
    return None

def __get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value
