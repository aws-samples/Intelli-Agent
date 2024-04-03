import json
from langchain.schema.messages import BaseMessage


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseMessage):
            return {"role": obj.type, "content": obj.content}
        return json.JSONEncoder.default(self, obj)
