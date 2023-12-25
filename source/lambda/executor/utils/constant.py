from enum import Enum

class Type(Enum):
    COMMON = "common"
    DGR = "dgr"
    MARKET = "market"
    MARKET_CHAIN = "market_chain"

    def has_value(self,value):
        return value in self._value2member_map_ 

class IntentType(Enum):
    KNOWLEDGE_QA = "knowledge_qa"
    CHAT = "chat"
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"

    def has_value(self,value):
        return value in self._value2member_map_ 