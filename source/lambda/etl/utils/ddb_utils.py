from datetime import datetime, timezone

from constant import IndexTag, IndexType, KBType, ModelType, Status
from utils.embeddings import get_embedding_info


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


def initiate_model(
    model_table, group_name, model_id, embedding_endpoint, create_time=None
):
    existing_item = item_exist(
        model_table, {"groupName": group_name, "modelId": model_id}
    )
    embedding_info = get_embedding_info(embedding_endpoint)
    embedding_info["ModelEndpoint"] = embedding_endpoint
    if existing_item:
        existing_embedding_endpoint = existing_item["parameter"]["ModelEndpoint"]
        if existing_embedding_endpoint != embedding_endpoint:
            embedding_info = get_embedding_info(embedding_endpoint)
            update_model(
                model_table,
                {"groupName": group_name, "modelId": model_id},
                embedding_info,
            )
    else:
        if not create_time:
            create_time = str(datetime.now(timezone.utc))
        create_item(
            model_table,
            {"groupName": group_name, "modelId": model_id},
            {
                "groupName": group_name,
                "modelId": model_id,
                "modelType": ModelType.EMBEDDING.value,
                "parameter": embedding_info,
                "createTime": create_time,
                "updateTime": create_time,
                "status": Status.ACTIVE.value,
            },
        )
    return embedding_info["ModelType"]


def initiate_index(
    index_table,
    group_name,
    index_id,
    model_id,
    index_type,
    tag,
    create_time=None,
    description="",
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
            "modelIds": {"embedding": model_id},
            "tag": tag,
            "createTime": create_time,
            "status": Status.ACTIVE.value,
        }
        if index_type != IndexType.INTENTION.value:
            db_body["description"] = description

        create_item(
            index_table, {"groupName": group_name, "indexId": index_id}, db_body
        )


def initiate_chatbot(
    chatbot_table,
    group_name,
    chatbot_id,
    chatbot_description,
    index_type,
    index_id_list,
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
                        "value": {index_id: index_id for index_id in index_id_list},
                    }
                },
                "createTime": create_time,
                "updateTime": create_time,
                "status": Status.ACTIVE.value,
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
