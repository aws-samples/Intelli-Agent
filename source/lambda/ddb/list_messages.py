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
messages_table_name = os.getenv("MESSAGES_TABLE_NAME")
messages_table_gsi_name = os.getenv("MESSAGES_BY_SESSION_ID_INDEX_NAME")

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

    max_items = get_query_parameter(event, "max_items", DEFAULT_MAX_ITEMS)
    page_size = get_query_parameter(event, "page_size", DEFAULT_SIZE)
    starting_token = get_query_parameter(event, "starting_token")
    session_id = get_query_parameter(event, "session_id")

    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }

    # Use query after adding a filter
    paginator = client.get_paginator("query")

    response_iterator = paginator.paginate(
        TableName=messages_table_name,
        IndexName=messages_table_gsi_name,
        PaginationConfig=config,
        KeyConditionExpression="sessionId = :session_id",
        ExpressionAttributeValues={":session_id": {"S": session_id}},
        ScanIndexForward=False,
    )

    output = {}
    for page in response_iterator:
        print(page)
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in ["role", "content", "createTimestamp"]:
                item_json[key] = item[key]["S"]
            if item["role"]["S"] == "ai":
                item_json["additional_kwargs"] = json.loads(item["additional_kwargs"]["S"])
            page_json.append(item_json)

        if "LastEvaluatedKey" in page:
            output["LastEvaluatedKey"] = encoder.encode(
                {"ExclusiveStartKey": page["LastEvaluatedKey"]}
            )
        break

    chat_history = sorted(page_json, key=lambda x: x["createTimestamp"])
    output["Items"] = chat_history
    output["Config"] = config
    output["Count"] = len(chat_history)

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
