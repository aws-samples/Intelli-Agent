from datetime import datetime, timezone
from typing import Any

from constant import IndexType, KBType, ModelType, Status
from embeddings import get_embedding_info

def create_item_if_not_exist(ddb_table, item_key: dict, body: str):
    response = ddb_table.get_item(Key=item_key)
    item = response.get("Item")
    if not item:
        ddb_table.put_item(Item=body)
        return False, item
    return True, item

def check_item_exist(ddb_table, item_key: dict):
    response = ddb_table.get_item(Key=item_key)
    item = response.get("Item")
    return True, item if item else False, None


def initiate_model(
    model_table, group_name, model_id, embedding_endpoint, create_time=None
):
    if not create_time:
        create_time = str(datetime.now(timezone.utc))
    embedding_info = dict(get_embedding_info(embedding_endpoint))
    embedding_info["ModelEndpoint"] = embedding_endpoint
    create_item_if_not_exist(
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

    create_item_if_not_exist(
        index_table, {"groupName": group_name, "indexId": index_id}, db_body
    )


def initiate_chatbot(
    chatbot_table, group_name, chatbot_id, index_id, index_type, tag, create_time=None
):
    if not create_time:
        create_time = str(datetime.now(timezone.utc))
    is_existed, item = create_item_if_not_exist(
        chatbot_table,
        {"groupName": group_name, "chatbotId": chatbot_id},
        {
            "groupName": group_name,
            "chatbotId": chatbot_id,
            "languages": ["zh"],
            "indexIds": {index_type: {"count": 1, "value": {tag: index_id}}},
            "createTime": create_time,
            "updateTime": create_time,
            "status": Status.ACTIVE.value,
        },
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
                item["indexIds"][index_type]["count"] = len(
                    item["indexIds"][index_type]["value"]
                )
                chatbot_table.put_item(Item=item)
        else:
            # Add a new index type
            item["indexIds"][index_type] = {"count": 1, "value": {tag: index_id}}
            chatbot_table.put_item(Item=item)


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
