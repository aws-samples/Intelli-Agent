import json
import logging
import os

import boto3
from botocore.paginate import TokenEncoder

DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
logger = logging.getLogger()
logger.setLevel(logging.INFO)
client = boto3.client("dynamodb")
encoder = TokenEncoder()

dynamodb = boto3.resource("dynamodb")
sessions_table_name = os.getenv("SESSIONS_TABLE_NAME")
sessions_table_gsi_name = os.getenv("SESSIONS_BY_TIMESTAMP_INDEX_NAME")

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


def lambda_handler(event, context):

    logger.info(event)
    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])        
        if "use_api_key" in claims:
            cognito_username = get_query_parameter(event, "UserName", "default_user_id")
        else:
            cognito_username = claims["cognito:username"]
    else:
        logger.error("Invalid authorizer type")
        raise

    max_items = get_query_parameter(event, "max_items", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "page_size", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "starting_token")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = client.get_paginator("query")

    response_iterator = paginator.paginate(
        TableName=sessions_table_name,
        IndexName=sessions_table_gsi_name,
        PaginationConfig=config,
        KeyConditionExpression="userId = :user_id",
        ExpressionAttributeValues={":user_id": {"S": cognito_username}},
        ScanIndexForward=False,
    )

    output = {}

    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in ["sessionId", "userId", "createTimestamp", "latestQuestion"]:
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
