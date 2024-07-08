import json
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
from utils.ddb_utils import create_item_if_not_exist
from utils.embeddings import get_embedding_info
from constant import KBType, Status, IndexType, ModelType, IndexTag
import boto3
import logging


client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")
execution_table = dynamodb.Table(os.environ.get("EXECUTION_TABLE"))
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE"))
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
create_time = str(datetime.now(timezone.utc))
logger = logging.getLogger()
logger.setLevel(logging.INFO)



def initiate_model(model_table, group_name, model_id):
    embedding_info = get_embedding_info(embedding_endpoint)
    embedding_info["ModelEndpoint"] = embedding_endpoint
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
    return embedding_info["ModelType"]


def initiate_index(index_table, group_name, index_id, model_id, index_type, tag):
    create_item_if_not_exist(
        index_table,
        {
            "groupName": group_name, 
            "indexId": index_id
        },
        {
            "groupName": group_name, 
            "indexId": index_id,
            "indexType": index_type,
            "kbType": KBType.AOS.value,
            "modelIds": {
                "embedding": model_id
            },
            "tag": tag,
            "createTime": create_time,
            "status": Status.ACTIVE.value
        }
    )


def initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id, index_type, tag):
    is_existed, item = create_item_if_not_exist(
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
                index_type: {
                    "count": 1,
                    "value": {
                        IndexTag.COMMON.value: index_id
                    }
                }
            },
            "createTime": create_time,
            "updateTime": create_time,
            "status": Status.ACTIVE.value
        }
    )

    if is_existed:
        index_id_dict = item.get("indexIds", {})
        append_index = True
        if index_type in index_id_dict:
            # Append it with the same index type
            for key in index_id_dict[index_type]["value"].keys():
                if key == tag:
                    append_index = False
                    break
            
            if append_index:
                item["indexIds"][index_type]["value"][tag] = index_id
                item["indexIds"][index_type]["count"] = len(item["indexIds"][index_type]["value"])
                chatbot_table.put_item(Item=item)
        else:
            # Add a new index type
            item["indexIds"][index_type] = {
                "count": 1,
                "value": {
                    tag: index_id
                }
            }
            chatbot_table.put_item(Item=item)


def handler(event, context):
    # Check the event for possible S3 created event
    input_payload = {}
    logger.info(event)
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }
 
    if "Records" in event:
        logger.info("S3 event detected")
        # TODO, Aggregate the bucket and key from the event object for S3 created event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]
        parts = key.split("/")
        group_name = parts[-2] if len(parts) >= 2 else key
        # Update it after supporting create multiple chatbots in one group
        chatbot_id = group_name.lower()
        index_id = f"{chatbot_id}-qd-online"
        index_type = IndexType.QD.value
        tag = IndexTag.COMMON.value

        if key.endswith("/"):
            logger.info("This is a folder, skip")
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
        logger.info("API Gateway event detected")
        authorizer_type = event["requestContext"]["authorizer"].get("authorizerType")
        if authorizer_type == "lambda_authorizer":
            claims = json.loads(event["requestContext"]["authorizer"]["claims"])
            cognito_groups = claims["cognito:groups"]
            cognito_groups_list = cognito_groups.split(",")
        else:
            raise Exception("Invalid authorizer type")
        # Parse the body from the event object
        input_body = json.loads(event["body"])
        if "indexType" not in input_body or \
            input_body["indexType"] not in [IndexType.QD.value, IndexType.QQ.value, IndexType.INTENTION.value]:
            return {
                "statusCode": 400,
                "headers": resp_header,
                "body": f"Invalid indexType, valid values are {IndexType.QD.value}, {IndexType.QQ.value}, {IndexType.INTENTION.value}"
            }
        index_type = input_body["indexType"]
        tag = input_body.get("tag", IndexTag.COMMON.value)
        group_name = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
        chatbot_id = input_body.get("chatbotId", group_name.lower())
        
        if "indexId" in input_body:
            index_id = input_body["indexId"]
        else:
            # Use default index id if not specified in the request
            index_id = f"{chatbot_id}-qd-offline"
            if index_type == IndexType.QQ.value:
                index_id = f"{chatbot_id}-qq-offline"
            elif index_type == IndexType.INTENTION.value:
                index_id = f"{chatbot_id}-intention-offline"

        input_body["indexId"] = index_id
        input_body["groupName"] = (
            group_name
            if "groupName" not in input_body
            else input_body["groupName"]
        )
    
    model_id = f"{chatbot_id}-embedding"
    embedding_model_type = initiate_model(model_table, group_name, model_id)
    initiate_index(index_table, group_name, index_id, model_id, index_type, tag)
    initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id, index_type, tag)

    input_body["tableItemId"] = context.aws_request_id
    input_body["chatbotId"] = chatbot_id
    input_body["embeddingModelType"] = embedding_model_type
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
