
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

opensearch_logger = logging.getLogger("opensearch")
opensearch_logger.setLevel(logging.ERROR)
boto3_logger = logging.getLogger("botocore")
boto3_logger.setLevel(logging.ERROR)


