import logging
import os
import json
import boto3
from datetime import datetime, timezone
from utils.ddb_utils import initiate_index, initiate_model, initiate_chatbot, is_chatbot_existed
from constant import IndexType


logger = logging.getLogger()
logger.setLevel(logging.INFO)
region_name = os.environ.get("AWS_REGION")
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
dynamodb = boto3.resource("dynamodb", region_name=region_name)
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))


def lambda_handler(event, context):
    logger.info(f"event:{event}")
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }
    input_body = json.loads(event["body"])
    if "groupName" not in input_body:
        return {
            "statusCode": 400,
            "headers": resp_header,
            "body": json.dumps(
                {
                    "message": "No groupName in the body, please specify a groupName, e.g. Admin"
                }
            ),
        }

    group_name = input_body["groupName"]
    chatbot_id = group_name.lower()
    if is_chatbot_existed(chatbot_table, group_name, chatbot_id):
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(
                {
                    "chatbotId": chatbot_id,
                    "groupName": group_name,
                    "message": "Chatbot existed",
                }
            ),
        }

    model_id = f"{chatbot_id}-embedding"
    create_time = str(datetime.now(timezone.utc))
    initiate_model(model_table, group_name, model_id, embedding_endpoint, create_time)

    index_id_list = {}
    # Iterate over all enum members and create DDB metadata
    for member in IndexType.__members__.values():
        index_type = member.value
        index_id = tag = f"{chatbot_id}-{index_type}-default"
        index_id_list[index_type] = index_id
        initiate_index(index_table, group_name, index_id, model_id, index_type, tag, create_time)
        initiate_chatbot(chatbot_table, group_name, chatbot_id, index_id, index_type, tag, create_time)

    return {
        "statusCode": 200,
        "headers": resp_header,
        "body": json.dumps(
            {
                "chatbotId": chatbot_id,
                "groupName": group_name,
                "indexIds": index_id_list,
                "message": "Chatbot created",
            }
        ),
    }
