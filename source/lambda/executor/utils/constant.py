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
    TEXT2SQL = "text2sql"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

Type = EntryType
class IntentType(Enum):
    # common intention
    CHAT = "chat"
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"
    QUICK_REPLY_TOO_SHORT = "quick_reply_too_short_query"
    COMMON_CHAT = "common_chat"
    COMMON_QUICK_REPLY_TOO_SHORT = "common_quick_reply_too_short_query"
    # domain intention
    KNOWLEDGE_QA = "knowledge_qa"
    MARKET_EVENT = 'market_event'
    # text2sql intention
    TEXT2SQL_SQL_QA = "text2sql_sql_qa"
    TEXT2SQL_SQL_QUICK_REPLY = "text2sql_sql_quick_reply"
    TEXT2SQL_SQL_GEN = "text2sql_sql_generate"
    TEXT2SQL_SQL_RE_GEN = "text2sql_sql_re_generate"
    TEXT2SQL_SQL_VALIDATED = "text2sql_sql_validated"
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

class MKTUserType:
    ASSISTANT = "assistant"
    AUTO_CHAT = "auto_chat"

class HistoryType:
    DDB = 'ddb'
    MESSAGE = "message"


# LLM chain typs
QUERY_TRANSLATE_TYPE = "query_translate"  # for query translate purpose
INTENT_RECOGNITION_TYPE = "intent_recognition" # for intent recognition
AWS_TRANSLATE_SERVICE_MODEL_ID = "Amazon Translate"
QUERY_TRANSLATE_IDENTITY_TYPE = "identity"
QUERY_REWRITE_TYPE = "query_rewrite"
HYDE_TYPE = "hyde"
CONVERSATION_SUMMARY_TYPE = "conversation_summary"
MKT_CONVERSATION_SUMMARY_TYPE = "mkt_conversation_summary"
MKT_QUERY_REWRITE_TYPE = "mkt_query_rewrite"
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