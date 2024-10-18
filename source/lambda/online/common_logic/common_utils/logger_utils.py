
import logging
import threading
import os
from functools import wraps

opensearch_logger = logging.getLogger("opensearch")
opensearch_logger.setLevel(logging.ERROR)

logger_lock = threading.Lock()


def cloud_print_wrapper(fn):
    @wraps(fn)
    def _inner(msg, *args, **kwargs):
        from common_logic.common_utils.lambda_invoke_utils import is_running_local
        if not is_running_local:
            # enable multiline as one message in cloudwatch
            msg = msg.replace("\n", "\r")
        return fn(msg, *args, **kwargs)
    return _inner


class Logger:
    logger_map = {}

    @classmethod
    def _get_logger(
        cls,
        name,
        level=int(os.environ.get('DEBUG_LEVEL', logging.INFO)),
        format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S'
    ):
        if name in cls.logger_map:
            return cls.logger_map[name]
        logger = logging.getLogger(name)
        logger.propagate = 0
        # Create a handler
        c_handler = logging.StreamHandler()
        formatter = logging.Formatter(format, datefmt=datefmt)
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)
        logger.setLevel(level)
        logger.info = cloud_print_wrapper(logger.info)
        logger.error = cloud_print_wrapper(logger.error)
        logger.warning = cloud_print_wrapper(logger.warning)
        logger.critical = cloud_print_wrapper(logger.critical)
        logger.debug = cloud_print_wrapper(logger.debug)
        cls.logger_map[name] = logger
        return logger

    @classmethod
    def get_logger(
        cls,
        *args,
        **kwargs
    ):
        with logger_lock:
            return cls._get_logger(*args, **kwargs)


get_logger = Logger.get_logger

# modify default logger
logging.root = get_logger("main")
logger = logging.root


def print_llm_messages(msg, logger=logger):
    enable_print_messages = os.getenv(
        "ENABLE_PRINT_MESSAGES", 'True').lower() in ('true', '1', 't')
    if enable_print_messages:
        logger.info(msg)
