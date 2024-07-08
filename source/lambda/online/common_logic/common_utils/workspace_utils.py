import logging
from datetime import datetime
from typing import List


WORKSPACE_OBJECT_TYPE = "workspace"


class WorkspaceManager:
    def __init__(self, workspace_table):
        self.workspace_table = workspace_table

    def get_workspace(self, workspace_id: str):
        response = self.workspace_table.get_item(
            Key={"workspace_id": workspace_id, "object_type": WORKSPACE_OBJECT_TYPE}
        )
        item = response.get("Item")

        return item

    def get_workspace_id(self, workspace_name: str, embeddings_model_name: str):
        response = self.workspace_table.scan(
            FilterExpression="name = :name and embeddings_model_name = :embeddings_model_name",
            ExpressionAttributeValues={
                ":name": workspace_name,
                ":embeddings_model_name": embeddings_model_name,
            },
        )
        items = response.get("Items")

        if items:
            return items[0]["workspace_id"]
        else:
            return None

