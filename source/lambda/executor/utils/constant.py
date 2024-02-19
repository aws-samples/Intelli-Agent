from enum import Enum

class EntryType(Enum):
    COMMON = "common"
    DGR = "dgr"
    MARKET = "market"
    MARKET_CHAIN = "market_chain"
    QQ_RETRIEVER = "qq_retriever"
    QD_RETRIEVER = "qd_retriever"
    MARKET_CONVERSATION_SUMMARY = "market_conversation_summary"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

Type = EntryType
class IntentType(Enum):
    KNOWLEDGE_QA = "knowledge_qa"
    CHAT = "chat"
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

QUERY_TRANSLATE_TYPE = "query_translate"  # for query translate purpose

HUMAN_MESSAGE_TYPE = 'human'
AI_MESSAGE_TYPE = 'ai'
SYSTEM_MESSAGE_TYPE = 'system'