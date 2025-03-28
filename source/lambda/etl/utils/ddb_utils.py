import json
import logging
from datetime import datetime, timezone

from constant import KBType, ModelType, UiStatus
from utils.embeddings import get_embedding_dimension

logger = logging.getLogger(__name__)


def item_exist(ddb_table, item_key: dict):
    response = ddb_table.get_item(Key=item_key)
    item = response.get("Item")

    return item


def create_item(ddb_table, item_key: dict, body: dict):
    ddb_table.put_item(Item={**item_key, **body})


def update_model(model_table, item_key, model_parameter):
    update_time = str(datetime.now(timezone.utc))
    model_table.update_item(
        Key=item_key,
        UpdateExpression="SET #parameter = :parameter, #updateTime = :updateTime",
        ExpressionAttributeNames={
            "#parameter": "parameter",
            "#updateTime": "updateTime",
        },
        ExpressionAttributeValues={
            ":parameter": model_parameter,
            ":updateTime": update_time,
        },
    )


def initiate_embedding_model(
    *,
    model_table,
    group_name,
    model_item_id,
    embedding_model_provider,
    embedding_model_id,
    embedding_model_endpoint,
    base_url,
    api_key_arn,
    create_time,
    additional_config,
):
    embedding_model_dimension = get_embedding_dimension(embedding_model_id)[
        "modelDimension"
    ]
    embedding_info = {
        "modelProvider": embedding_model_provider,
        "modelId": embedding_model_id,
        "modelEndpoint": embedding_model_endpoint,
        "baseUrl": base_url,
        "apiKeyArn": api_key_arn,
        "modelDimension": embedding_model_dimension,
    }

    try:
        additional_config_dict = json.loads(additional_config)
    except Exception as e:
        logger.error(f"Error parsing additional config: {e}")
        additional_config_dict = {}

    # add all key vakue pair from additional_config_dict to embedding_info
    embedding_info.update(additional_config_dict)

    item_content = {
        "groupName": group_name,
        "modelId": model_item_id,
        "modelType": ModelType.EMBEDDING.value,
        "parameter": embedding_info,
        "createTime": create_time,
        "updateTime": create_time,
        "status": UiStatus.ACTIVE.value,
    }
    if embedding_info["modelId"] == "bce-embedding-base_v1":
        item_content["parameter"]["targetModel"] = "bce_embedding_model.tar.gz"
    create_item(
        model_table,
        {"groupName": group_name, "modelId": model_item_id},
        item_content,
    )
    return embedding_info["modelProvider"]


def initiate_rerank_model(
    *,
    model_table,
    group_name,
    model_item_id,
    rerank_model_provider,
    rerank_model_id,
    rerank_model_endpoint,
    base_url,
    api_key_arn,
    create_time,
    additional_config,
):
    rerank_info = {
        "modelProvider": rerank_model_provider,
        "modelId": rerank_model_id,
        "modelEndpoint": rerank_model_endpoint,
        "baseUrl": base_url,
        "apiKeyArn": api_key_arn,
    }
    try:
        additional_config_dict = json.loads(additional_config)
    except Exception as e:
        logger.error(f"Error parsing additional config: {e}")
        additional_config_dict = {}

    rerank_info.update(additional_config_dict)

    item_content = {
        "groupName": group_name,
        "modelId": model_item_id,
        "modelType": ModelType.RERANK.value,
        "parameter": rerank_info,
        "createTime": create_time,
        "updateTime": create_time,
        "status": UiStatus.ACTIVE.value,
    }
    if rerank_info["modelId"] == "bge-reranker-large":
        item_content["parameter"]["targetModel"] = "bge_reranker_model.tar.gz"
    create_item(
        model_table,
        {"groupName": group_name, "modelId": model_item_id},
        item_content,
    )
    return rerank_info["modelProvider"]


def initiate_vlm_model(
    *,
    model_table,
    group_name,
    model_item_id,
    vlm_model_provider,
    vlm_model_id,
    vlm_model_endpoint,
    base_url,
    api_key_arn,
    create_time,
):
    vlm_info = {
        "modelProvider": vlm_model_provider,
        "modelId": vlm_model_id,
        "modelEndpoint": vlm_model_endpoint,
        "baseUrl": base_url,
        "apiKeyArn": api_key_arn,
    }

    item_content = {
        "groupName": group_name,
        "modelId": model_item_id,
        "modelType": ModelType.VLM.value,
        "parameter": vlm_info,
        "createTime": create_time,
        "updateTime": create_time,
        "status": UiStatus.ACTIVE.value,
    }
    create_item(
        model_table,
        {"groupName": group_name, "modelId": model_item_id},
        item_content,
    )
    return vlm_info["modelProvider"]


def initiate_index(
    *,
    index_table,
    group_name,
    index_id,
    embedding_model_item_id,
    rerank_model_item_id,
    index_type,
    tag,
    description,
    create_time=None,
):
    existing_item = item_exist(
        index_table, {"groupName": group_name, "indexId": index_id}
    )

    if not existing_item:
        if not create_time:
            create_time = str(datetime.now(timezone.utc))

        db_body = {
            "groupName": group_name,
            "indexId": index_id,
            "indexType": index_type,
            "kbType": KBType.AOS.value,
            "modelIds": {
                "embedding": embedding_model_item_id,
                "rerank": rerank_model_item_id,
            },
            "tag": tag,
            "description": description,
            "createTime": create_time,
            "status": UiStatus.ACTIVE.value,
        }
        # if index_type != IndexType.INTENTION.value:
        #     db_body["description"] = description

        create_item(
            index_table, {"groupName": group_name, "indexId": index_id}, db_body
        )


def create_item_if_not_exist(ddb_table, item_key: dict, body: str):
    response = ddb_table.get_item(Key=item_key)
    item = response.get("Item")
    if not item:
        ddb_table.put_item(Item=body)
        return False, item
    return True, item


def initiate_chatbot(
    *,
    chatbot_table,
    group_name,
    chatbot_id,
    chatbot_description,
    index_type,
    index_id_list,
    embedding_model_id,
    rerank_model_id,
    vlm_model_id,
    create_time=None,
):
    existing_item = item_exist(
        chatbot_table, {"groupName": group_name, "chatbotId": chatbot_id}
    )
    if existing_item:
        chatbot_table.update_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id},
            UpdateExpression="SET #indexIds.#indexType = :indexIdTypeDict, #updateTime = :updateTime",
            ExpressionAttributeNames={
                "#indexIds": "indexIds",
                "#indexType": index_type,
                "#updateTime": "updateTime",
            },
            ExpressionAttributeValues={
                ":indexIdTypeDict": {
                    "count": len(index_id_list),
                    "value": {index_id: index_id for index_id in index_id_list},
                },
                ":updateTime": str(datetime.now(timezone.utc)),
            },
        )
    else:
        if not create_time:
            create_time = str(datetime.now(timezone.utc))
        create_item(
            chatbot_table,
            {"groupName": group_name, "chatbotId": chatbot_id},
            {
                "groupName": group_name,
                "chatbotId": chatbot_id,
                "chatbotDescription": chatbot_description,
                "indexIds": {
                    index_type: {
                        "count": len(index_id_list),
                        "value": {
                            index_id: index_id for index_id in index_id_list
                        },
                    }
                },
                "embeddingModelId": embedding_model_id,
                "rerankModelId": rerank_model_id,
                "vlmModelId": vlm_model_id,
                "createTime": create_time,
                "updateTime": create_time,
                "status": UiStatus.ACTIVE.value,
            },
        )


def is_chatbot_existed(ddb_table, group_name: str, chatbot_id: str):
    response = ddb_table.get_item(
        Key={
            "groupName": group_name,
            "chatbotId": chatbot_id,
        },
    )
    item = response.get("Item")
    if not item:
        return False
    return True
