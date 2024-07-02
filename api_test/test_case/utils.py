import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_function_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Function: {func.__name__}, Arguments: {args}, Keyword arguments: {kwargs}")
        return func(*args, **kwargs)
    return wrapper


def step(msg):
    logger.info(f"Test step: {msg}")


def check_point(msg):
    logger.info(f"Check point: {msg}")