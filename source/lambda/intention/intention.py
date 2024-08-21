import json
import os
import time
import boto3
from botocore.paginate import TokenEncoder
from common_logic.common_utils.logger_utils import get_logger

DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
DEFAULT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ROOT_RESOURCE = "/intention"
PRESIGNED_URL_RESOURCE = f"{ROOT_RESOURCE}/execution-presigned-url"
EXECUTION_RESOURCE = f"{ROOT_RESOURCE}/executions"
logger = get_logger(__name__)
encoder = TokenEncoder()

dynamodb_resource = boto3.resource("dynamodb")
intention_table_name = os.getenv("INTENTION_TABLE_NAME","intention")
intention_table = dynamodb_resource.Table(intention_table_name)

dynamodb_client = boto3.client("dynamodb")
s3_client = boto3.client("s3")
s3_bucket_name = os.environ.get("S3_BUCKET")

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}

def lambda_handler(event, context):
    logger.info(event)
    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        email = claims["email"]
        cognito_groups = claims["cognito:groups"]
        cognito_groups_list = cognito_groups.split(",")
    else:
        cognito_groups_list = ["Admin"]
    #     group_name = claims["cognito:groups"] #Agree to only be in one group
    # else:
    #     group_name = "Admin"
    http_method = event["httpMethod"]
    resource:str = event["resource"]
    chatbot_id = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
    if resource == PRESIGNED_URL_RESOURCE:
        input_body = json.loads(event["body"])
        file_name = "intentions/" + chatbot_id + "/" + input_body["file_name"]
        output = __gen_presigned_url(file_name, 
                                     input_body.get("content_type", DEFAULT_CONTENT_TYPE),
                                     input_body.get("expiration", 60*60))
    elif resource == EXECUTION_RESOURCE:
        if http_method == "POST":
            output = __create_execution(event, context, email)
        else:
            output = __list_execution(event, chatbot_id)
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

def __get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value

def __gen_presigned_url(object_name: str, content_type: str, expiration: int):
    return s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": s3_bucket_name, "Key": object_name, "ContentType": content_type},
        ExpiresIn=expiration,
        HttpMethod="PUT",
    )


def __list_execution(event, group_name):
    max_items = __get_query_parameter(event, "MaxItems", DEFAULT_MAX_ITEMS)
    page_size = __get_query_parameter(event, "PageSize", DEFAULT_SIZE)
    starting_token = __get_query_parameter(event, "StartingToken")
    config = {
        "MaxItems": int(max_items),
        "PageSize": int(page_size),
        "StartingToken": starting_token,
    }
    paginator = dynamodb_client.get_paginator("query")
    response_iterator = paginator.paginate(
        TableName=intention_table_name,
        PaginationConfig=config,
        KeyConditionExpression="groupName = :groupName",
        ExpressionAttributeValues={":groupName": {"S": group_name}},
        ScanIndexForward=False,
    )
    output = {}
    for page in response_iterator:
        page_items = page["Items"]
        page_json = []
        for item in page_items:
            item_json = {}
            for key in list(item.keys()):
                if key in ["Intention"]:
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


def __create_execution(event, context, email):
    input_body = json.loads(event["body"])
    execution_detail = {}
    execution_detail["tableItemId"] = context.aws_request_id
    execution_detail["botId"] = input_body.get("botId")
    execution_detail["index"] = input_body.get("index")
    execution_detail["modelId"] = input_body.get("modelId")
    execution_detail["fileName"] = input_body.get("file")
    execution_detail["tag"] = input_body.get("tag")
    # write to ddb(meta data)
    intention_table.put_item(
        Item={
            "GroupName": execution_detail["botId"],
            "SortKey": f'{execution_detail["botId"]}__{execution_detail["modelId"]}',
            "ModelId": execution_detail["modelId"],
            "Tag": execution_detail["tag"],
            "File": f'{input_body.get("s3Bucket")}{input_body.get("s3Prefix")}',
            "LastModifiedBy": email,
            "LastModifiedTime": str(int(time.time())),
        }
    )
    intention_table_name.put_item(Item=input_body)

    # write to aos(vectorData)


    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": execution_detail["tableItemId"],
                "input_payload": json.dumps(execution_detail),
                "result": "success"
            }
        ),
    }
