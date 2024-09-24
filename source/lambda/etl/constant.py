"""
Constant used in ETL lambda
"""

from enum import Enum, unique


@unique
class KBType(Enum):
    AOS = "aos"


@unique
class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class EmbeddingModelType(Enum):
    BEDROCK_TITAN_V1 = "amazon.titan-embed-text-v1"

@unique
class IndexType(Enum):
    QD = "qd"
    QQ = "qq"
    INTENTION = "intention"


@unique
class ModelType(Enum):
    EMBEDDING = "embedding_and_rerank"
    LLM = "llm"


@unique
class IndexTag(Enum):
    COMMON = "common"
