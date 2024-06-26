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
table_name = os.environ.get("EXECUTION_TABLE")
encoder = TokenEncoder()


def get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value


def lambda_handler(event, context):
    logger.info(event)

    authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        group_id = claims["cognito:groups"]
        cognito_groups_list = group_id.split(",")
    else:
        raise Exception(
            "Invalid authorizer type. This API should only be invoked by the lambda authorizer"
        )
    logger.info(f"Group ID: {group_id}")

    max_items = get_query_parameter(event, "max_items", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "page_size", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "starting_token")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = client.get_paginator("scan")

    if "Admin" in cognito_groups_list:
        response_iterator = paginator.paginate(
            TableName=table_name,
            PaginationConfig=config,
            FilterExpression="uiStatus = :active",
            ExpressionAttributeValues={":active": {"S": "ACTIVE"}},
        )
    else:
        response_iterator = paginator.paginate(
            TableName=table_name,
            PaginationConfig=config,
            FilterExpression="uiStatus = :active AND groupId = :group_id",
            ExpressionAttributeValues={
                ":active": {"S": "ACTIVE"},
                ":group_id": {"S": group_id},
            },
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

    output["Config"] = config

    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

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
