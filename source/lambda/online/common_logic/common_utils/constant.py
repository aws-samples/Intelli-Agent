class ConstantBase:
    @classmethod
    def has_value(cls, value):
        return value in list(cls.__dict__.values())

class EntryType(ConstantBase):
    COMMON = "common"
    RETAIL = "retail"
    DGR = "aws-knowledge"

class SceneType(ConstantBase):
    COMMON = "common"
    RETAIL = "retail"
    AWS_QA = "aws-qa"


    
Type = EntryType
class IntentType(ConstantBase):
    # common intention
    # CHAT = "chat"
    STRICT_QQ = "strict_q_q"
    AUTO = "auto"
    QUICK_REPLY_TOO_SHORT = "quick_reply_too_short_query"
    COMMON_CHAT = "common_chat"
    COMMON_QUICK_REPLY_TOO_SHORT = "common_quick_reply_too_short_query"
    # domain intention
    # KNOWLEDGE_QA = "knowledge_qa"
    MARKET_EVENT = 'market_event'
    # text2sql intention
    TEXT2SQL_SQL_QA = "text2sql_sql_qa"
    TEXT2SQL_SQL_QUICK_REPLY = "text2sql_sql_quick_reply"
    TEXT2SQL_SQL_GEN = "text2sql_sql_generate"
    TEXT2SQL_SQL_RE_GEN = "text2sql_sql_re_generate"
    TEXT2SQL_SQL_VALIDATED = "text2sql_sql_validated"

class RerankerType(ConstantBase):
    BGE_RERANKER = "bge_reranker"
    BGE_M3_RERANKER = "bge_m3_colbert"
    BYPASS = "no_reranker"


class MKTUserType(ConstantBase):
    ASSISTANT = "assistant"
    AUTO_CHAT = "auto_chat"

class HistoryType(ConstantBase):
    DDB = 'ddb'
    MESSAGE = "message"


class LLMTaskType(ConstantBase):
    # LLM chain typs
    QUERY_TRANSLATE_TYPE = "query_translate"  # for query translate purpose
    INTENT_RECOGNITION_TYPE = "intent_recognition" # for intent recognition
    AWS_TRANSLATE_SERVICE_MODEL_ID = "Amazon Translate"
    QUERY_TRANSLATE_IDENTITY_TYPE = "identity"
    QUERY_REWRITE_TYPE = "query_rewrite"
    HYDE_TYPE = "hyde"
    CONVERSATION_SUMMARY_TYPE = "conversation_summary"
    RETAIL_CONVERSATION_SUMMARY_TYPE = "retail_conversation_summary"

    MKT_CONVERSATION_SUMMARY_TYPE = "mkt_conversation_summary"
    MKT_QUERY_REWRITE_TYPE = "mkt_query_rewrite"
    STEPBACK_PROMPTING_TYPE = "stepback_prompting"
    TOOL_CALLING = "tool_calling"
    RETAIL_TOOL_CALLING = "retail_tool_calling"
    RAG = "rag"
    CHAT = 'chat'
    AUTO_EVALUATION = "auto_evaluation"
    

class MessageType(ConstantBase):
    HUMAN_MESSAGE_TYPE = 'human'
    AI_MESSAGE_TYPE = 'ai'
    SYSTEM_MESSAGE_TYPE = 'system'
    OBSERVATION = "observation"
    TOOL_MESSAGE_TYPE = "tool"


class StreamMessageType(ConstantBase):
    START = "START"
    END = "END"
    ERROR = "ERROR"
    CHUNK = "CHUNK"
    CONTEXT = "CONTEXT"
    MONITOR = "MONITOR"


class ChatbotMode(ConstantBase):
    chat = "chat" # chi-chat
    rag_mode = "rag"  # rag
    agent = "agent" # rag + tool use


class ToolRuningMode(ConstantBase):
    LOOP = "loop"
    ONCE = "once"


class LLMModelType(ConstantBase):
    CLAUDE_INSTANCE = "anthropic.claude-instant-v1"
    CLAUDE_2 = "anthropic.claude-v2"
    CLAUDE_21 = "anthropic.claude-v2:1"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    MIXTRAL_8X7B_INSTRUCT = "mistral.mixtral-8x7b-instruct-v0:1"
    BAICHUAN2_13B_CHAT = "Baichuan2-13B-Chat-4bits"
    INTERNLM2_CHAT_7B = "internlm2-chat-7b"
    INTERNLM2_CHAT_20B = "internlm2-chat-20b"
    GLM_4_9B_CHAT = "glm-4-9b-chat"
    CHATGPT_35_TURBO = "gpt-3.5-turbo-0125"
    CHATGPT_4_TURBO = "gpt-4-turbo"
    CHATGPT_4O = "gpt-4o"
    QWEN2INSTRUCT7B = "qwen2-7B-instruct"
    QWEN2INSTRUCT72B = "qwen2-72B-instruct"
    QWEN15INSTRUCT32B = "qwen1_5-32B-instruct"
    
    


