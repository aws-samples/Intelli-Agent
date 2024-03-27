
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

opensearch_logger = logging.getLogger("opensearch")
opensearch_logger.setLevel(logging.ERROR)
boto3_logger = logging.getLogger("botocore")
boto3_logger.setLevel(logging.ERROR)

def get_logger(
        name,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S'
        ):
    logger = logging.getLogger(name)
    logger.propagate = 0
    # Create a handler
    c_handler = logging.StreamHandler()
    formatter = logging.Formatter(format, datefmt=datefmt)
    c_handler.setFormatter(formatter)
    logger.addHandler(c_handler)
    logger.setLevel(level) 
    return logger





