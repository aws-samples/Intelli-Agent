from typing import Dict, Any, List

class Chatbot:
    def __init__(self, group_name: str, chatbot_id: str, create_time: str, index_ids: Dict[str, Any], languages: List[str], status: str, update_time: str):
        self.group_name = group_name
        self.chatbot_id = chatbot_id
        self.create_time = create_time
        self.index_ids = index_ids
        self.languages = languages
        self.status = status
        self.update_time = update_time

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]):
        """Convert to a chatbot instance from DynamoDB item

        Args:
            item (Dict[str, Any]): DynamoDB item

        Returns:
            Chatbot instance
        """
        return cls(
            group_name=item.get("groupName"),
            chatbot_id=item.get("chatbotId"),
            create_time=item.get("createTime"),
            index_ids=item.get("indexIds",{}),
            languages=item.get("languages"),
            status=item.get("status"),
            update_time=item.get("updateTime")
        )

    def __repr__(self):
        return f"Chatbot(group_name={self.group_name}, chatbot_id={self.chatbot_id}, create_time={self.create_time}, index_ids={self.index_ids}, languages={self.languages}, status={self.status}, update_time={self.update_time})"

    def get_index_dict(self):
        """Get index dict in a chatbot

        Returns:
            index_dict: chatbot index dict including qd, qq, intention
        """
        index_dict = {}
        
        for index_type, item_dict in self.index_ids.items():
            for index_content in item_dict["value"].values():
                index_dict[index_content['indexId']] = index_type
        return index_dict

