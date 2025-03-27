# warmup
import time 
from shared.utils.logger_utils import get_logger
from shared.utils.boto3_utils import get_boto3_client

logger = get_logger(__name__)

try:
    t0 = time.time()
    from opensearchpy import OpenSearch
    logger.info(f'opensearch warmup time: {time.time()-t0}')
except ModuleNotFoundError:
    logger.warning('opensearch module not found')

get_boto3_client("bedrock-runtime")
get_boto3_client("sagemaker-runtime")

