import logging
import threading
import os
from functools import wraps

opensearch_logger = logging.getLogger("opensearch")
opensearch_logger.setLevel(logging.ERROR)

logger_lock = threading.Lock()


class CloudStreamHandler(logging.StreamHandler):
    def emit(self, record):
        from common_logic.common_utils.lambda_invoke_utils import is_running_local
        if not is_running_local:
            # enable multiline as one message in cloudwatch
            record.msg = record.msg.replace("\n", "\r")
        return super().emit(record)


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
        c_handler = CloudStreamHandler()
        formatter = logging.Formatter(format, datefmt=datefmt)
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)
        logger.setLevel(level)
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


def llm_messages_print_decorator(fn):
    @wraps(fn)
    def _inner(*args, **kwargs):
        if args:
            print_llm_messages(args)
        if kwargs:
            print_llm_messages(kwargs)
        return fn(*args, **kwargs)
    return _inner
