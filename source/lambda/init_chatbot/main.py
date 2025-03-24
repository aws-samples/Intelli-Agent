# lambda/init_data.py
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")


def handler(event, context):
    model_table_name = os.environ["MODEL_TABLE_NAME"]
    chat_bot_table_name = os.environ["CHATBOT_TABLE_NAME"]
    index_table_name = os.environ["INDEX_TABLE_NAME"]
    model = json.loads(os.environ["MODEL_INFO"])
    chat_bot_table = dynamodb.Table(chat_bot_table_name)
    model_table = dynamodb.Table(model_table_name)
    index_table = dynamodb.Table(index_table_name)
    time_str = str(datetime.now(timezone.utc))
    embeddings_models = model.get("embeddingsModels")
    embeddings_model = (
        embeddings_models[0]
        if embeddings_models and isinstance(embeddings_models, list) and len(embeddings_models) > 0
        else {}
    )
    rerank_models = model.get("rerankModels")
    rerank_model = (
        rerank_models[0] if rerank_models and isinstance(rerank_models, list) and len(rerank_models) > 0 else {}
    )
    vlm_models = model.get("vlms")
    vlm_model = vlm_models[0] if vlm_models and isinstance(vlm_models, list) and len(vlm_models) > 0 else {}
    embedding_model_id = embeddings_model.get("id")
    rerank_model_id = rerank_model.get("id")
    vlm_model_id = vlm_model.get("id")
    try:
        # Item={**item_key, **body}
        model_table.put_item(
            Item={
                "groupName": "Admin",
                "modelId": "admin-embedding",
                "createTime": time_str,
                "modelType": "embedding",
                "parameter": {
                    "apiKeyArn": "",
                    "baseUrl": "",
                    "modelId": embedding_model_id,
                    "targetModel": __gen_target_model(embedding_model_id),
                    "modelDimension": embeddings_model.get("dimensions"),
                    "modelEndpoint": embeddings_model.get("modelEndpoint"),
                    "modelProvider": embeddings_model.get("provider"),
                },
                "status": "ACTIVE",
                "updateTime": time_str,
            }
        )
        model_table.put_item(
            Item={
                "groupName": "Admin",
                "modelId": "admin-rerank",
                "createTime": time_str,
                "modelType": "rerank",
                "parameter": {
                    "apiKeyArn": "",
                    "baseUrl": "",
                    "modelId": rerank_model_id,
                    "targetModel": __gen_target_model(rerank_model_id),
                    "modelEndpoint": rerank_model.get("modelEndpoint"),
                    "modelProvider": rerank_model.get("provider"),
                },
                "status": "ACTIVE",
                "updateTime": time_str,
            }
        )
        model_table.put_item(
            Item={
                "groupName": "Admin",
                "modelId": "admin-vlm",
                "createTime": time_str,
                "modelType": "vlm",
                "parameter": {
                    "apiKeyArn": "",
                    "baseUrl": "",
                    "modelId": vlm_model_id,
                    "modelEndpoint": "",
                    "modelProvider": vlm_model.get("provider"),
                },
                "status": "ACTIVE",
                "updateTime": time_str,
            }
        )
        chat_bot_table.put_item(
            Item={
                "groupName": "Admin",
                "chatbotId": "admin",
                "chatbotDescription": "Answer question based on search result",
                "createTime": time_str,
                "indexIds": {
                    "intention": {"count": 1, "value": {"admin-intention-default": "admin-intention-default"}},
                    "qd": {"count": 1, "value": {"admin-qd-default": "admin-qd-default"}},
                    "qq": {"count": 1, "value": {"admin-qq-default": "admin-qq-default"}},
                },
                "embeddingModelId": "admin-embedding",
                "rerankModelId": "admin-rerank",
                "vlmModelId": "admin-vlm",
                "status": "ACTIVE",
                "updateTime": time_str,
            }
        )
        index_table.put_item(
            Item={
                "groupName": "Admin",
                "indexId": "admin-intention-default",
                "createTime": time_str,
                "description": "Answer question based on search result",
                "indexType": "intention",
                "kbType": "aos",
                "modelIds": {"embedding": "admin-embedding", "rerank": "admin-rerank"},
                "status": "ACTIVE",
                "tag": "admin-intention-default",
            }
        )
        index_table.put_item(
            Item={
                "groupName": "Admin",
                "indexId": "admin-qd-default",
                "createTime": time_str,
                "description": "Answer question based on search result",
                "indexType": "qd",
                "kbType": "aos",
                "modelIds": {"embedding": "admin-embedding", "rerank": "admin-rerank"},
                "status": "ACTIVE",
                "tag": "admin-qd-default",
            }
        )
        index_table.put_item(
            Item={
                "groupName": "Admin",
                "indexId": "admin-qq-default",
                "createTime": time_str,
                "description": "Answer question based on search result",
                "indexType": "qq",
                "kbType": "aos",
                "modelIds": {"embedding": "admin-embedding", "rerank": "admin-rerank"},
                "status": "ACTIVE",
                "tag": "admin-qq-default",
            }
        )

        return {"status": "SUCCESS"}
    except ClientError as e:
        print(f"Insert failed: {e.response['Error']['Message']}")
        raise


def __gen_target_model(model_id: str):
    if model_id == "bce-embedding-base_v1":
        return "bce_embedding_model.tar.gz"
    elif model_id == "bge-reranker-large":
        return "bge_reranker_model.tar.gz"
    else:
        return ""
