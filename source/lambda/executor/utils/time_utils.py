from functools import wraps
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        # first item in the args, ie `args[0]` is `self`
        logger.info(f'Function {func.__name__} Took {total_time:.4f} seconds\n')
        return result
    return timeit_wrapper