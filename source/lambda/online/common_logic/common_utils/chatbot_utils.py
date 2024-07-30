import logging
from datetime import datetime
from typing import List
import os
import boto3

from .chatbot import Chatbot


class ChatbotManager:
    def __init__(self, chatbot_table, index_table, model_table):
        self.chatbot_table = chatbot_table
        self.index_table = index_table
        self.model_table = model_table

    @classmethod
    def from_environ(cls):
        chatbot_table_name = os.environ.get("CHATBOT_TABLE_NAME", "")
        model_table_name = os.environ.get("MODEL_TABLE_NAME", "")
        index_table_name = os.environ.get("INDEX_TABLE_NAME", "")
        dynamodb = boto3.resource("dynamodb")
        chatbot_table = dynamodb.Table(chatbot_table_name)
        model_table = dynamodb.Table(model_table_name)
        index_table = dynamodb.Table(index_table_name)
        chatbot_manager = cls(chatbot_table, index_table, model_table)
        return chatbot_manager 

    def get_chatbot(self, group_name: str, chatbot_id: str):
        """Get chatbot from chatbot id and add index, model, etc. data

        Args:
            group_name (str): group name
            chatbot_id (str): chatbot id

        Returns:
            Chatbot instance
        """
        chatbot_response = self.chatbot_table.get_item(
            Key={"groupName": group_name, "chatbotId": chatbot_id}
        )
        chatbot_content = chatbot_response.get("Item")
        if not chatbot_content:
            return Chatbot.from_dynamodb_item({})
        for index_type, index_item in chatbot_content.get("indexIds").items():
            for tag, index_id in index_item.get("value").items():
                index_content = self.index_table.get_item(
                    Key={"groupName": group_name, "indexId": index_id}
                ).get("Item")
                embedding_model_id = index_content.get("modelIds").get("embedding")
                if embedding_model_id:
                    model_content = self.model_table.get_item(
                        Key={"groupName": group_name, "modelId": embedding_model_id}
                    ).get("Item")
                    index_content["modelIds"]["embedding"] = model_content
                chatbot_content["indexIds"][index_type]["value"][tag] = index_content

        chatbot = Chatbot.from_dynamodb_item(chatbot_content)

        return chatbot

