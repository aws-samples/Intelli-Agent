from enum import Enum, unique


DEFAULT_MAX_ITEMS = 50
DEFAULT_SIZE = 50
HTTPS_PORT_NUMBER = "443"
DEFAULT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ROOT_RESOURCE = "/intention"
PRESIGNED_URL_RESOURCE = f"{ROOT_RESOURCE}/execution-presigned-url"
EXECUTION_RESOURCE = f"{ROOT_RESOURCE}/executions"
INDEX_USED_SCAN_RESOURCE = f"{ROOT_RESOURCE}/index-used-scan"
DOWNLOAD_RESOURCE = f"{ROOT_RESOURCE}/download-template"
SECRET_NAME = "opensearch-master-user"
AOS_INDEX = "aics_intention_index"
BULK_SIZE = 100000000

@unique
class IndexType(Enum):
    QD = "qd"
    QQ = "qq"
    INTENTION = "intention"

@unique
class KBType(Enum):
    AOS = "aos"


@unique
class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

ModelDimensionMap = {
    "amazon.titan-embed-text-v1": 1536,
    "cohere.embed-english-v3": 1024,
    "amazon.titan-embed-text-v2:0": 1024
}

@unique
class ModelType(Enum):
    EMBEDDING = "embedding_and_rerank"
    LLM = "llm"