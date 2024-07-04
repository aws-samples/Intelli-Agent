import json
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from utils.ddb_utils import create_item_if_not_exist
from utils.embeddings import get_embedding_info
from constant import KBType, Status, IndexType, ModelType
import boto3


client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE"))
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
create_time = str(datetime.now(timezone.utc))


def initiate_model(model_table, group_name, model_id):
    embedding_info = get_embedding_info(embedding_endpoint)
    create_item_if_not_exist(
        model_table,
        {
            "groupName": group_name, 
            "modelId": model_id
        },
        {
            "groupName": group_name, 
            "modelId": model_id,
            "modelType": ModelType.EMBEDDING.value,
            "parameter": embedding_info,
            "createTime": create_time,
            "updateTime": create_time,
            "status": Status.ACTIVE.value
        }
    )    


def initiate_index(index_table, group_name, index_id, model_id):
    create_item_if_not_exist(
        index_table,
        {
            "groupName": group_name, 
            "indexId": index_id
        },
        {
            "groupName": group_name, 
            "indexId": index_id,
            "indexType": IndexType.QD.value,
            "kbType": KBType.AOS.value,
            "modelIds": {
                "embedding": model_id
            },
            "createTime": create_time,
            "status": Status.ACTIVE.value
        }
    )


def initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id):
    qq_index_id = f"{chatbot_id}-qq"
    intention_index_id = f"{chatbot_id}-intention"
    create_item_if_not_exist(
        chatbot_table,
        {
            "groupName": group_name, 
            "chatbotId": chatbot_id
        },
        {
            "groupName": group_name, 
            "chatbotId": chatbot_id,
            "languages": [ "zh" ],
            "indexIds": {
                IndexType.QD.value: index_id,
                IndexType.QQ.value: qq_index_id,
                IndexType.INTENTION.value: intention_index_id
            },
            "createTime": create_time,
            "updateTime": create_time,
            "status": Status.ACTIVE.value
        }
    )


def handler(event, context):
    # Check the event for possible S3 created event
    input_payload = {}
    print(event)
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    if "Records" in event:
        print("S3 event detected")
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        parts = key.split("/")
        group_name = parts[-2] if len(parts) >= 2 else key
        # Update it after supporting create multiple chatbots in one group
        chatbot_id = group_name.lower()
        index_id = f"{chatbot_id}-qd-online"

        if key.endswith("/"):
            print("This is a folder, skip")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "This is a folder, skip",
                    }
                ),
            }
        elif event["Records"][0]["eventName"].startswith("ObjectCreated:"):
            key = unquote_plus(key)

            input_body = {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
                "groupName": group_name,
                "chatbotId": chatbot_id,
                "indexId": index_id,
                "operationType": "update",
            }
        elif event["Records"][0]["eventName"].startswith("ObjectRemoved:"):
            key = unquote_plus(key)

            input_body = {
                "s3Bucket": bucket,
                "s3Prefix": key,
                "offline": "false",
                "qaEnhance": "false",
                "groupName": group_name,
                "chatbotId": chatbot_id,
                "indexId": index_id,
                "operationType": "delete",
            }
    else:
        print("API Gateway event detected")
        authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            cognito_groups = claims["cognito:groups"]
            cognito_groups_list = cognito_groups.split(",")
        else:
            raise Exception("Invalid authorizer type")
        # Parse the body from the event object
        input_body = json.loads(event["body"])

        group_name = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
        chatbot_id = group_name.lower()
        index_id = f"{chatbot_id}-qd-offline"
        input_body["indexId"] = index_id
        input_body["groupName"] = (
            group_name
            if "groupName" not in input_body
            else input_body["groupName"]
        )
    
    model_id = f"{chatbot_id}-embedding"
    initiate_model(model_table, group_name, index_id)
    initiate_index(index_table, group_name, index_id, model_id)
    initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id)

    input_body["tableItemId"] = context.aws_request_id
    input_body["chatbotId"] = chatbot_id
    input_payload = json.dumps(input_body)
    response = client.start_execution(
        stateMachineArn=os.environ["sfn_arn"], input=input_payload
    )

    # Update execution table item
    if "tableItemId" in input_body:
        del input_body["tableItemId"]
    execution_id = response["executionArn"].split(":")[-1]
    input_body["sfnExecutionId"] = execution_id
    input_body["executionStatus"] = "IN-PROGRESS"
    input_body["indexId"] = index_id
    input_body["executionId"] = context.aws_request_id
    input_body["uiStatus"] = "ACTIVE"
    input_body["createTime"] = create_time

    execution_table.put_item(Item=input_body)

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "execution_id": context.aws_request_id,
                "step_function_arn": response["executionArn"],
                "input_payload": input_payload,
            }
        ),
    }
