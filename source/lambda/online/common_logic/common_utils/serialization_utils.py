import json

from langchain.schema.messages import BaseMessage


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseMessage):
            return {"role": obj.type, "content": obj.content}
        try:
            return json.JSONEncoder.default(self, obj)
        except:
            return str(obj)
