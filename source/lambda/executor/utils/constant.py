from enum import Enum

class EntryType(Enum):
    COMMON = "common"
    DGR = "dgr"
    MARKET = "market"
    MARKET_CHAIN = "market_chain"
    MARKET_CHAIN_CORE = "market_chain_core"
    MARKET_CHAIN_KNOWLEDGE = "market_chain_knowledge"
    QQ_RETRIEVER = "qq_retriever"
    QD_RETRIEVER = "qd_retriever"
    MARKET_CONVERSATION_SUMMARY = "market_conversation_summary"
    LLM = "llm"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

Type = EntryType
class IntentType(Enum):
    KNOWLEDGE_QA = "knowledge_qa"
    CHAT = "chat"
    MARKET_EVENT = 'market_event'
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

class RerankerType(Enum):
    BGE_RERANKER = "bge_reranker"
    BGE_M3_RERANKER = "bge_m3_colbert"
    BYPASS = "no_reranker"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 


# LLM chain typs
QUERY_TRANSLATE_TYPE = "query_translate"  # for query translate purpose
INTENT_RECOGNITION_TYPE = "intent_recognition" # for intent recognition
AWS_TRANSLATE_SERVICE_MODEL_ID = "Amazon Translate"
QUERY_TRANSLATE_IDENTITY_TYPE = "identity"
QUERY_REWRITE_TYPE = "query_rewrite"
HYDE_TYPE = "hyde"
CONVERSATION_SUMMARY_TYPE = "conversation_summary"
MKT_CONVERSATION_SUMMARY_TYPE = "mkt_conversation_summary"
STEPBACK_PROMPTING_TYPE = "stepback_prompting"

HUMAN_MESSAGE_TYPE = 'human'
AI_MESSAGE_TYPE = 'ai'
SYSTEM_MESSAGE_TYPE = 'system'



class StreamMessageType:
    START = "START"
    END = "END"
    ERROR = "ERROR"
    CHUNK = "CHUNK"
    CONTEXT = "CONTEXT"