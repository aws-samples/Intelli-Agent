import json
import os
from datetime import datetime
import boto3
from botocore.paginate import TokenEncoder
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.prompt_utils import get_all_templates, EXPORT_MODEL_IDS, EXPORT_SCENES

DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
ROOT_RESOURCE = "/prompt-management"
MODELS_RESOURCE = f"{ROOT_RESOURCE}/models"
SCENES_RESOURCE = f"{ROOT_RESOURCE}/scenes"
PROMPTS_RESOURCE = f"{ROOT_RESOURCE}/prompts"
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


def __put_prompt(event, group_name, email):
    body = json.loads(event["body"])
    model_id = body.get("ModelId")
    scene = body.get("Scene")
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    prompt_table.put_item(
                Item={
                    "GroupName": group_name,
                    "SortKey": f"{model_id}__{scene}",
                    "ModelId": model_id,
                    "Scene": scene,
                    "Prompt": body.get("Prompt"),
                    "LastModifiedBy": email,
                    "LastModifiedTime": formatted_time,
                }
            )
    return {"Message":"OK"}


def __list_model():
    return EXPORT_MODEL_IDS


def __list_scene():
    return EXPORT_SCENES


def __list_prompt(event, group_name):
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
        TableName=prompt_table_name,
        PaginationConfig=config,
        KeyConditionExpression="GroupName = :GroupName",
        ExpressionAttributeValues={":GroupName": {"S": group_name}},
        ScanIndexForward=False,
    )

    output = {}

    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in list(item.keys()):
                if key in ["Prompt"]:
                    continue
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


def __get_prompt(event, group_name):
    sort_key = event["path"].replace(f"{PROMPTS_RESOURCE}/", "").strip().replace("/","__")
    response = prompt_table.get_item(
            Key={"GroupName": group_name, "SortKey": sort_key}
        )
    item = response.get("Item")
    if item:
        return item
    keys = sort_key.split("__")
    default_prompt = get_all_templates().get(keys[0],{}).get(keys[1])
    response_prompt = {
        "GroupName": group_name,
        "SortKey": sort_key,
        "ModelId": keys[0],
        "Scene": keys[1],
        "Prompt": default_prompt,
    }
    return response_prompt


def __delete_prompt(event, group_name):
    sort_key = event["path"].replace(f"{PROMPTS_RESOURCE}/", "").strip().replace("/","__")
    response = prompt_table.delete_item(
            Key={"GroupName": group_name, "SortKey": sort_key}
        )
    return {"Message":"OK"}


def lambda_handler(event, context):
    logger.info(event)
    authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        email = claims["email"]
        group_name = claims["cognito:groups"] #Agree to only be in one group
    else:
        raise Exception("Invalid authorizer type")
    http_method = event["httpMethod"]
    resource:str = event["resource"]
    if resource == MODELS_RESOURCE:
        output = __list_model()
    elif resource == SCENES_RESOURCE:
        output = __list_scene()
    elif resource.startswith(PROMPTS_RESOURCE):
        if http_method == "POST":
            output = __put_prompt(event, group_name, email)
        elif http_method == "GET":
            if event["resource"] == PROMPTS_RESOURCE:
                output = __list_prompt(event, group_name)
            else:
                output = __get_prompt(event, group_name)
        elif http_method == "DELETE":
            output = __delete_prompt(event, group_name)

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