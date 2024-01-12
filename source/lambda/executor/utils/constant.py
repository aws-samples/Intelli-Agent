from enum import Enum

class Type(Enum):
    COMMON = "common"
    DGR = "dgr"
    MARKET = "market"
    MARKET_CHAIN = "market_chain"
    QQ_RETRIEVER = "qq_retriever"
    QD_RETRIEVER = "qd_retriever"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

class IntentType(Enum):
    KNOWLEDGE_QA = "knowledge_qa"
    CHAT = "chat"
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 