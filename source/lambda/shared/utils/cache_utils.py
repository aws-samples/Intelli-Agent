from aiocache import cached as asyncached,SimpleMemoryCache
import asyncio
from functools import wraps
from cachetools import cached,keys,Cache
from .logger_utils import get_logger


def lru_cache_with_logging(cache:Cache = None, key=keys.hashkey, lock=None):
    def decorator(func):
        cache_obj = cache
        if cache_obj is None:
            cache_obj = Cache(128)
        cached_func = cached(cache_obj,key=key,lock=lock,info=True)(func)
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


def alru_cache_with_logging(cache=SimpleMemoryCache, key=keys.hashkey, lock=None):
    def decorator(func):
        def key_helper(func,*args,**kwargs):
            return key(*args, **kwargs)
        cached_func = asyncached(cache=cache,key_builder=key_helper)(func)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            before_cache_size = len(cached_func.cache._cache)
            result = await cached_func(*args, **kwargs)
            current_cache_size = len(cached_func.cache._cache)
            if current_cache_size > before_cache_size:
                print(f"Cache hit for {args} {kwargs}, current_cache_size: {current_cache_size}")
            else:
                print(f"Cache miss for {args} {kwargs}, current_cache_size: {current_cache_size}")
            return result
        return wrapper
    return decorator




