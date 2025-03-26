# warmup
import time 
from shared.utils.logger_utils import get_logger

logger = get_logger(__name__)

try:
    t0 = time.time()
    from opensearchpy import OpenSearch
    logger.info(f'opensearch warmup time: {time.time()-t0}')
except ModuleNotFoundError:
    logger.warning('opensearch module not found')


