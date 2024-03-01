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


# LLM chain typs
QUERY_TRANSLATE_TYPE = "query_translate"  # for query translate purpose
INTENT_RECOGNITION_TYPE = "intent_recognition" # for intent recognition
AWS_TRANSLATE_SERVICE_MODEL_ID = "Amazon Translate"
QUERY_TRANSLATE_IDENTITY_TYPE = "identity"
QUERY_REWRITE_TYPE = "query_rewrite"
CONVERSATION_SUMMARY_TYPE = "conversation_summary"
MKT_CONVERSATION_SUMMARY_TYPE = "mkt_conversation_summary"
STEPBACK_PROMPTING_TYPE = "stepback_prompting"

HUMAN_MESSAGE_TYPE = 'human'
AI_MESSAGE_TYPE = 'ai'
SYSTEM_MESSAGE_TYPE = 'system'