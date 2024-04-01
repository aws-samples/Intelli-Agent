import json
import logging
import os
import uuid
from datetime import datetime
from typing import List

import boto3

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

    def create_workspace_open_search(
        self,
        workspace_id: str,
        embeddings_model_endpoint: str,
        embeddings_model_provider: str,
        embeddings_model_name: str,
        embeddings_model_dimensions: int,
        embedding_model_type: str,
        languages: List[str],
        open_search_index_type: str,
        workspace_offline_flag: str,
        workspace_file_types: List[str] = [],
    ):

        if workspace_offline_flag == "true":
            open_search_index_name = f"{workspace_id}-offline"
        else:
            open_search_index_name = f"{workspace_id}-online"
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        item = {
            "workspace_id": workspace_id,
            "object_type": WORKSPACE_OBJECT_TYPE,
            "format_version": 1,
            "name": workspace_id,
            "engine": "opensearch",
            "status": "submitted",
            "embeddings_model_endpoint": embeddings_model_endpoint,
            "embeddings_model_provider": embeddings_model_provider,
            "embeddings_model_name": embeddings_model_name,
            "embeddings_model_dimensions": embeddings_model_dimensions,
            "model_type": embedding_model_type,
            "languages": languages,
            "workspace_file_types": workspace_file_types,
            "index_type": open_search_index_type,
            "open_search_index_name": open_search_index_name,
            "metric": "l2",
            "aoss_engine": "nmslib",
            "documents": 0,
            "vectors": 0,
            "size_in_bytes": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        response = self.workspace_table.put_item(Item=item)

        logging.info(f"Created workspace with response: {response}")

        return open_search_index_name

    def update_workspace_open_search(
        self,
        workspace_id: str,
        embeddings_model_endpoint: str,
        embeddings_model_provider: str,
        embeddings_model_name: str,
        embeddings_model_dimensions: int,
        embedding_model_type: str,
        languages: List[str],
        open_search_index_type: str,
        workspace_offline_flag: str,
        workspace_file_types: List[str] = [],
    ):
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        item = self.get_workspace(workspace_id)
        # If the item not exist, create the item
        if not item:
            open_search_index_name = self.create_workspace_open_search(
                workspace_id,
                embeddings_model_endpoint,
                embeddings_model_provider,
                embeddings_model_name,
                embeddings_model_dimensions,
                embedding_model_type,
                languages,
                open_search_index_type,
                workspace_offline_flag,
                workspace_file_types,
            )

        else:
            # Get the current workspace_file_types, or an empty list if it doesn't exist
            current_workspace_file_types = item.get("workspace_file_types", [])
            open_search_index_name = item.get("open_search_index_name")

            # Append the new workspace_file_types and remove duplicates
            updated_workspace_file_types = list(
                set(current_workspace_file_types + workspace_file_types)
            )

            # Update the item
            response = self.workspace_table.update_item(
                Key={
                    "workspace_id": workspace_id,
                    "object_type": WORKSPACE_OBJECT_TYPE,
                },
                UpdateExpression="SET workspace_file_types = :wft, updated_at = :uat",
                ExpressionAttributeValues={
                    ":wft": updated_workspace_file_types,
                    ":uat": timestamp,
                },
                ReturnValues="ALL_NEW",
            )

            logging.info(f"Updated workspace with response: {response}")

        return open_search_index_name
