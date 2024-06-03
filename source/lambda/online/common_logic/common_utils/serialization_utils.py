import json

from langchain.schema.messages import BaseMessage
from common_utils.ddb_utils import DynamoDBChatMessageHistory


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseMessage):
            return {"role": obj.type, "content": obj.content}
        if isinstance(obj, DynamoDBChatMessageHistory):
            return DynamoDBChatMessageHistory.__name__
        try:
            return json.JSONEncoder.default(self, obj)
        except:
            return str(obj)
