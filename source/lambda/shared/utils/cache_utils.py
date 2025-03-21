from async_lru import alru_cache
import asyncio
from functools import wraps
from cachetools import LFUCache,cached,keys
from .logger_utils import get_logger



def lru_cache_with_logging(cache:LFUCache, key=keys.hashkey, lock=None):
    def decorator(func):
        cached_func = cached(cache,key=key,lock=lock,info=True)(func)
        @wraps(func)
        def wrapper(*args, **kwargs):
            before_hits = cached_func.cache_info().hits
            result = cached_func(*args, **kwargs)
            current_cache_info = cached_func.cache_info()
            
            if current_cache_info.hits > before_hits:
                print(f"Cache hit for {args} {kwargs}")
            else:
                print(f"Cache miss for {args} {kwargs}")
            return result
        return wrapper
    return decorator


def alru_cache_with_logging(maxsize=128):
    def decorator(func):
        cached_func = alru_cache(maxsize=maxsize)(func)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            before_hits = cached_func.cache_info().hits
            result = await cached_func(*args, **kwargs)
            # cache_info = cached_func.cache_info()
            current_cache_info = cached_func.cache_info()
            current_cache_hits = current_cache_info.hits
            current_cache_size = current_cache_info.currsize

            if current_cache_hits > before_hits:
                print(f"Cache hit for {args} {kwargs}, current_cache_size: {current_cache_size}")
            else:
                print(f"Cache miss for {args} {kwargs}, current_cache_size: {current_cache_size}")
            return result
        return wrapper
    return decorator



