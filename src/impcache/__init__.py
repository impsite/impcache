"""Simple async cache with high performance. Easy to use & ready for production."""

__version__ = "1.0.0"

from .exceptions import CacheError, JsonEncodeError, JsonDecodeError
from .repository import RedisCacheRepository
from .service import ICache, Cache

__all__ = [
    "ICache",
    "Cache",
    "RedisCacheRepository",
    "CacheError",
    "JsonEncodeError",
    "JsonDecodeError",
]
