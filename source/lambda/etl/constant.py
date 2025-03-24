"""
Constant used in ETL lambda
"""

from enum import Enum, unique


@unique
class KBType(Enum):
    AOS = "aos"


@unique
class UiStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@unique
class ExecutionStatus(Enum):
    IN_PROGRESS = "IN-PROGRESS"
    COMPLETED = "COMPLETED"
    DELETING = "DELETING"
    DELETED = "DELETED"
    UPDATING = "UPDATING"


class EmbeddingModelType(Enum):
    BEDROCK_TITAN_V1 = "amazon.titan-embed-text-v1"


@unique
class IndexType(Enum):
    QD = "qd"
    QQ = "qq"
    INTENTION = "intention"


@unique
class ModelType(Enum):
    EMBEDDING = "embedding"
    LLM = "llm"
    VLM = "vlm"
    RERANK = "rerank"


@unique
class IndexTag(Enum):
    COMMON = "common"


@unique
class OperationType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXTRACT_ONLY = "extract_only"


@unique
class ModelProvider(Enum):
    EMD = "emd"
    BEDROCK = "Bedrock"
    BRCONNECTOR_BEDROCK = "Bedrock API"
    OPENAI = "OpenAI API"
