"""Simple cache implementation using cachetools TTLCache."""
import time
from typing import TypeVar, Generic, Optional
from cachetools import TTLCache


T = TypeVar("T")


class Cache(Generic[T]):
    """Generic TTL-based cache wrapper."""
    
    def __init__(self, ttl_ms: int):
        """Initialize cache with TTL in milliseconds."""
        self._cache: TTLCache = TTLCache(maxsize=64, ttl=ttl_ms / 1000.0)
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        return self._cache.get(key)
    
    def set(self, key: str, value: T) -> None:
        """Set value in cache."""
        self._cache[key] = value
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache


def create_cache(ttl_ms: int) -> Cache:
    """Factory function to create a cache instance."""
    return Cache(ttl_ms)
