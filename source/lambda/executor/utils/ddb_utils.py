from datetime import date
import json
import boto3
import logging
from typing import List
from decimal import Decimal
from datetime import datetime
from botocore.exceptions import ClientError
from logger_utils import logger
import time 
from decimal import Decimal
from langchain.schema import BaseChatMessageHistory
from langchain.schema.messages import (
    BaseMessage,
    _message_to_dict,
    messages_from_dict,
    messages_to_dict,
    _message_from_dict
)
from constant import HUMAN_MESSAGE_TYPE,AI_MESSAGE_TYPE,SYSTEM_MESSAGE_TYPE


client = boto3.resource("dynamodb")


class DynamoDBChatMessageHistory(BaseChatMessageHistory):
    def __init__(
        self,
        table_name: str,
        session_id: str,
        user_id: str,
    ):
        self.table = client.Table(table_name)
        self.session_id = session_id
        self.user_id = user_id

    @property
    def messages(self):
        """Retrieve the messages from DynamoDB"""
        response = None
        try:
            response = self.table.get_item(
                Key={"SessionId": self.session_id, "UserId": self.user_id}
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ResourceNotFoundException":
                print("No record found with session id: %s", self.session_id)
            else:
                print(error)

        if response and "Item" in response:
            items = response["Item"]["History"]
        else:
            items = []

        return items

    @property
    def message_as_langchain(self):
        response = self.table.get_item(
             Key={"SessionId": self.session_id, "UserId": self.user_id}
             )
        item = response.get('Item',[])
        if not item:
            return []
        history = response["Item"]["History"]
        ret = []
        for his in history:
            assert his['type'] in [AI_MESSAGE_TYPE,HUMAN_MESSAGE_TYPE]
            create_time = his['data']['additional_kwargs']['create_time']
            his['data']['additional_kwargs']['create_time'] = float(create_time)
            ret.append(_message_from_dict(his))
        return ret 

    def add_message(self, message) -> None:
        """Append the message to the record in DynamoDB"""
        messages = self.messages
        messages.append(message)
     
        try:
            response = self.table.put_item(
                Item={
                    "SessionId": self.session_id,
                    "UserId": self.user_id,
                    "StartTime": datetime.now().isoformat(),
                    "History": messages,
                }
            )
        except ClientError as err:
            print(f"Error adding message: {err}")

    def add_user_message(self, message_id, content) -> None:
        """Append the user message to the record in DynamoDB"""
        message = {
            'type': HUMAN_MESSAGE_TYPE,
            'data': {
                'type': HUMAN_MESSAGE_TYPE,
                'content': content,
                'additional_kwargs':{
                    "message_id": message_id,
                    "create_time": Decimal.from_float(time.time())
                }, 
                # 'example': False,
                }
            }
        self.add_message(message)
    
    def add_ai_message(self, message_id, content) -> None:
        """Append the ai message to the record in DynamoDB"""
        message = {
            'type': AI_MESSAGE_TYPE,
            'data': 
            {
                'type': AI_MESSAGE_TYPE, 
                'content': content, 
                'additional_kwargs': {
                    "message_id": message_id,
                    "create_time": Decimal.from_float(time.time())
                    }, 
                # 'example': False,
                }
            }
        self.add_message(message)

    def add_metadata(self, metadata) -> None:
        """Add additional metadata to the last message"""
        existing_messages = self.messages
        if not existing_messages:
            return

        metadata = json.loads(json.dumps(metadata), parse_float=Decimal)
        existing_messages[-1]["data"]["additional_kwargs"] = metadata

        try:
            self.table.put_item(
                Item={
                    "SessionId": self.session_id,
                    "UserId": self.user_id,
                    "StartTime": datetime.now().isoformat(),
                    "History": existing_messages,
                }
            )

        except Exception as err:
            print(err)

    def clear(self) -> None:
        """Clear session memory from DynamoDB"""
        try:
            self.table.delete_item(
                Key={"SessionId": self.session_id, "UserId": self.user_id}
            )
        except ClientError as err:
            print(err)
