"""Caching layer for IMDb ID lookups.

This module provides a TTL-based cache for IMDb lookups to reduce
API calls to TMDB and improve performance.
"""
import os
import logging
import hashlib
from typing import Optional
from cachetools import TTLCache
from utils import strip_diacritics


logger = logging.getLogger(__name__)


# Configuration
IMDB_CACHE_TTL_DAYS = int(os.getenv("IMDB_CACHE_TTL_DAYS", "7"))
IMDB_CACHE_TTL_SECONDS = IMDB_CACHE_TTL_DAYS * 24 * 60 * 60
IMDB_CACHE_MAX_SIZE = 1000

# Global cache instance
# Key: normalized title + year hash
# Value: IMDb ID or None (to cache failed lookups)
_imdb_cache: TTLCache = TTLCache(maxsize=IMDB_CACHE_MAX_SIZE, ttl=IMDB_CACHE_TTL_SECONDS)


def _normalize_title(title: str) -> str:
    """Normalize title for consistent cache keys.
    
    Removes diacritics, converts to lowercase, strips whitespace.
    
    Args:
        title: Movie title
        
    Returns:
        Normalized title
    """
    return strip_diacritics(title.lower().strip())


def _cache_key(title: str, year: Optional[int] = None) -> str:
    """Generate cache key from title and year.
    
    Args:
        title: Movie title
        year: Release year (optional)
        
    Returns:
        MD5 hash as cache key
    """
    normalized = _normalize_title(title)
    year_str = str(year) if year else ""
    key_string = f"{normalized}:{year_str}"
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cached_imdb_id(title: str, year: Optional[int] = None) -> Optional[str]:
    """Get IMDb ID from cache.
    
    Args:
        title: Movie title
        year: Release year (optional)
        
    Returns:
        Cached IMDb ID, None (if cached as not found), or KeyError (if not in cache)
    """
    key = _cache_key(title, year)
    
    try:
        value = _imdb_cache[key]
        logger.debug(f"Cache HIT for '{title}' (year: {year}): {value}")
        return value
    except KeyError:
        logger.debug(f"Cache MISS for '{title}' (year: {year})")
        raise


def set_cached_imdb_id(title: str, year: Optional[int], imdb_id: Optional[str]) -> None:
    """Store IMDb ID in cache.
    
    Args:
        title: Movie title
        year: Release year (optional)
        imdb_id: IMDb ID to cache (or None to cache failed lookup)
    """
    key = _cache_key(title, year)
    _imdb_cache[key] = imdb_id
    logger.debug(f"Cached IMDb ID for '{title}' (year: {year}): {imdb_id}")


def clear_cache() -> None:
    """Clear all cached IMDb IDs."""
    _imdb_cache.clear()
    logger.info("Cleared IMDb cache")


def get_cache_stats() -> dict:
    """Get cache statistics.
    
    Returns:
        Dict with cache stats (size, maxsize, ttl)
    """
    return {
        "size": len(_imdb_cache),
        "maxsize": _imdb_cache.maxsize,
        "ttl_days": IMDB_CACHE_TTL_DAYS,
        "ttl_seconds": IMDB_CACHE_TTL_SECONDS,
    }
