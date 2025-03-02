# lambda/init_data.py
from datetime import datetime, timezone
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    model_table_name = os.environ['MODEL_TABLE_NAME']
    chat_bot_table_name = os.environ['CHATBOT_TABLE_NAME']
    index_table_name = os.environ['INDEX_TABLE_NAME']
    chat_bot_table = dynamodb.Table(chat_bot_table_name)
    model_table = dynamodb.Table(model_table_name)
    index_table = dynamodb.Table(index_table_name)
    time_str = str(datetime.now(timezone.utc))
    
    try:
        # Item={**item_key, **body}
        model_table.put_item(Item={
            "groupName": "Admin",
            "modelId": "admin-embedding",
            "createTime": time_str,
            "modelType": "embedding_and_rerank",
            "parameter": {
             "ApiKeyArn": "",
             "BaseUrl": "",
             "ModelDimension": 768,
             "ModelEndpoint": "bce-embedding-and-bge-reranker-43972-endpoint",
             "ModelName": "bce_embedding_model.tar.gz",
             "ModelProvider": "SageMaker",
             "ModelType": "bce",
             "TargetModel": "bce_embedding_model.tar.gz"
            },
            "status": "ACTIVE",
            "updateTime": time_str
        })
        chat_bot_table.put_item(Item={
        "groupName": "Admin",
        "chatbotId": "admin",
        "chatbotDescription": "Answer question based on search result",
        "createTime": time_str,
        "indexIds": {
            "intention": {
                "count": 1,
                "value": {
                    "admin-intention-default": "admin-intention-default"
                }
            },
            "qd": {
                "count": 1,
                "value": {
                    "admin-qd-default": "admin-qd-default"
                }
            },
            "qq": {
                "count": 1,
                "value": {
                    "admin-qq-default": "admin-qq-default"
                }
            }
        },
        "status": "ACTIVE",
        "updateTime":  time_str
        })
        index_table.put_item(Item={
            "groupName": "Admin",
            "indexId": "admin-intention-default",
            "createTime": time_str,
            "description": "Answer question based on search result",
            "indexType": "intention",
            "kbType": "aos",
            "modelIds": {
                 "embedding": "admin-embedding"
            }, 
            "status": "ACTIVE",
         "tag": "admin-intention-default"
        })
        index_table.put_item(Item={
            "groupName": "Admin",
            "indexId": "admin-qd-default",
            "createTime": time_str,
            "description": "Answer question based on search result",
            "indexType": "qd",
            "kbType": "aos",
            "modelIds": {
                 "embedding": "admin-embedding"
            }, 
            "status": "ACTIVE",
           "tag": "admin-qd-default"
        })
        index_table.put_item(Item={
            "groupName": "Admin",
            "indexId": "admin-qq-default",
            "createTime": time_str,
            "description": "Answer question based on search result",
            "indexType": "qq",
            "kbType": "aos",
            "modelIds": {
                 "embedding": "admin-embedding"
            }, 
            "status": "ACTIVE",
            "tag": "admin-qq-default"
        })


        return {'status': 'SUCCESS'}
    except ClientError as e:
        print(f"Insert failed: {e.response['Error']['Message']}")
        raise
