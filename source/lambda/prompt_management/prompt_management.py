import json
import os

import boto3
from botocore.paginate import TokenEncoder
from common_utils.logger_utils import get_logger
from common_utils.prompt_utils import get_all_templates

DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
logger = get_logger("main")
dynamodb_client = boto3.client("dynamodb")
encoder = TokenEncoder()

dynamodb_resource = boto3.resource("dynamodb")
prompt_table_name = os.getenv("PROMPT_TABLE_NAME","prompt")
prompt_table = dynamodb_resource.Table(prompt_table_name)

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


def __put(event, user_id):
    body = json.loads(event["body"])
    model_id = body.get("model_id")
    task_type = body.get("task_type")
    prompt_table.put_item(
                Item={
                    "userId": user_id,
                    "sortKey": f"{model_id}__{task_type}",
                    "modelId": model_id,
                    "taskType": task_type,
                    "prompt": body.get("prompt"),
                }
            )
    return {"message":"OK"}


def __list(event, user_id):
    max_items = get_query_parameter(event, "max_items", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "page_size", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "starting_token")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = dynamodb_client.get_paginator("query")

    response_iterator = paginator.paginate(
        TableName=prompt_table_name,
        PaginationConfig=config,
        KeyConditionExpression="userId = :user_id",
        ExpressionAttributeValues={":user_id": {"S": user_id}},
        ScanIndexForward=False,
    )

    output = {}

    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in ["modelId", "taskType"]:
                item_json[key] = item.get(key, {"S": ""})["S"]
            page_json.append(item_json)
        output["Items"] = page_json
        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )
        break

    output["Config"] = config
    output["Count"] = len(page_json)
    return output


def __get(event, user_id):
    sort_key = event["path"].replace("/prompt/", "").strip().replace("/","__")
    response = prompt_table.get_item(
            Key={"userId": user_id, "sortKey": sort_key}
        )
    item = response.get("Item")
    if item:
        return item
    keys = sort_key.split("__")
    default_prompt = get_all_templates().get(sort_key)
    response_prompt = {
        "modelId": keys[0],
        "taskType": keys[1],
        "prompt": default_prompt,
        "sortKey": sort_key,
        "userId": user_id,
    }
    return response_prompt


def __delete_prompt(event, user_id):
    sort_key = event["path"].replace("/prompt/", "").strip().replace("/","__")
    response = prompt_table.delete_item(
            Key={"userId": user_id, "sortKey": sort_key}
        )
    return {"message":"OK"}


def lambda_handler(event, context):
    logger.info(event)
    authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        user_id = claims["cognito:username"]
    else:
        raise Exception("Invalid authorizer type")
    http_method = event["httpMethod"]
    if http_method == "POST":
        output = __put(event, user_id)
    elif http_method == "GET":
        if event["resource"] == "/prompt":
            output = __list(event, user_id)
        else:
            output = __get(event, user_id)
    elif http_method == "DELETE":
        output = __delete_prompt(event, user_id)

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