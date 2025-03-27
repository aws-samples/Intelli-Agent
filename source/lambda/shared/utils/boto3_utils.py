import boto3 
from .cache_utils import lru_cache_with_logging
from cachetools import LRUCache

@lru_cache_with_logging(cache=LRUCache(128))
def get_boto3_client(
        service_name:str,
        profile_name=None,
        **kwargs
    ):
    session = boto3.Session(profile_name=profile_name)
    return session.client(service_name, **kwargs)
