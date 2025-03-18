# lambda/init_data.py
from datetime import datetime, timezone
import json
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    model_table_name = os.environ['MODEL_TABLE_NAME']
    chat_bot_table_name = os.environ['CHATBOT_TABLE_NAME']
    index_table_name = os.environ['INDEX_TABLE_NAME']
    model = json.loads(os.environ['MODEL_INFO'])
    chat_bot_table = dynamodb.Table(chat_bot_table_name)
    model_table = dynamodb.Table(model_table_name)
    index_table = dynamodb.Table(index_table_name)
    time_str = str(datetime.now(timezone.utc))
    embeddings_models = model.get("embeddingsModels")
    embeddings_model = embeddings_models[0] if embeddings_models and isinstance(embeddings_models, list) and len(embeddings_models) > 0 else None
    rerank_models = model.get("rerankModels")
    rerank_model = rerank_models[0] if rerank_models and isinstance(rerank_models, list) and len(rerank_models) > 0 else None
    vlm_models = model.get("vlms")
    vlm_model = vlm_models[0] if vlm_models and isinstance(vlm_models, list) and len(vlm_models) > 0 else None
    
    try:
        # Item={**item_key, **body}
        model_table.put_item(Item={
            "groupName": "Admin",
            "modelId": "admin-embedding",
            "createTime": time_str,
            "modelType": "embedding",
            "parameter": {
                "modelId": embeddings_model.get("id"),
                "apiKeyArn": "",
                "baseUrl": "",
                "modelDimension": embeddings_model.get("dimensions"),
                "modelEndpoint": "",
                "modelProvider": embeddings_model.get("provider")
            },
            "status": "ACTIVE",
            "updateTime": time_str
        })
        model_table.put_item(Item={
            "groupName": "Admin",
            "modelId": "admin-rerank",
            "createTime": time_str,
            "modelType": "embedding",
            "parameter": {
                "modelId": rerank_model.get("id"),
                "apiKeyArn": "",
                "baseUrl": "",
                "modelEndpoint": "",
                "modelProvider": rerank_model.get("provider")
            },
            "status": "ACTIVE",
            "updateTime": time_str
        })
        model_table.put_item(Item={
            "groupName": "Admin",
            "modelId": "admin-vlm",
            "createTime": time_str,
            "modelType": "vlm",
            "parameter": {
                "modelId": vlm_model.get("id"),
                "apiKeyArn": "",
                "baseUrl": "",
                "modelEndpoint": "",
                "modelProvider": vlm_model.get("provider")
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
        "rerankModelId": "admin-rerank",
        "vlmModelId": "admin-vlm",
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
                 "embedding": "admin-embedding",
                 "rerank": "admin-rerank"
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
                 "embedding": "admin-embedding",
                 "rerank": "admin-rerank"
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
                 "embedding": "admin-embedding",
                 "rerank": "admin-rerank"
            }, 
            "status": "ACTIVE",
            "tag": "admin-qq-default"
        })


        return {'status': 'SUCCESS'}
    except ClientError as e:
        print(f"Insert failed: {e.response['Error']['Message']}")
        raise
