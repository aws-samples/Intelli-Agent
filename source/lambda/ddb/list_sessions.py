import json
import logging
import os

import boto3
from botocore.paginate import TokenEncoder

DEFAULT_MAX_ITEM = 50
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
    page_size = DEFAULT_SIZE
    max_item = DEFAULT_MAX_ITEM
    authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        cognito_username = claims["cognito:username"]
        cognito_groups = claims["cognito:groups"]
        cognito_groups_list = cognito_groups.split(",")
    else:
        raise Exception("Invalid authorizer type")

    page_size = get_query_parameter(event, "size")
    max_item = get_query_parameter(event, "total")
    starting_token = get_query_parameter(event, "token")

    config = {
        "MaxItems": int(max_item),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = client.get_paginator("scan")

    if "Admin" in cognito_groups_list:
        response_iterator = paginator.paginate(
            TableName=sessions_table_name,
            PaginationConfig=config,
            FilterExpression="uiStatus = :active",
            ExpressionAttributeValues={":active": {"S": "ACTIVE"}},
        )
    else:
        response_iterator = paginator.paginate(
            TableName=sessions_table_name,
            IndexName=sessions_table_gsi_name,
            PaginationConfig=config,
            KeyConditionExpression="userId = :user_id",
            ExpressionAttributeValues={":user_id": cognito_username},
        )

    output = {}
    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in item.keys():
                item_json[key] = item[key]["S"]
            page_json.append(item_json)
        # Return the latest page
        output["Items"] = page_json
        output["Count"] = page["Count"]
        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )

    output["config"] = config

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
