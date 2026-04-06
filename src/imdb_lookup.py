"""IMDb ID lookup service using TMDB (The Movie Database) API.

This module provides functionality to look up IMDb IDs for movie titles,
enabling better integration with stream provider addons like Torrentio.
"""
import os
import logging
import asyncio
from typing import Optional, Dict, List, Tuple, Any
try:
    import aiohttp
except ImportError:
    aiohttp = None  # Will be handled gracefully
from utils import strip_diacritics
from imdb_cache import get_cached_imdb_id, set_cached_imdb_id, get_cache_stats


logger = logging.getLogger(__name__)


TMDB_BASE_URL = "https://api.themoviedb.org/3"
_last_request_time = 0.0
_rate_limit_semaphore: Optional[asyncio.Semaphore] = None
_rate_limit_capacity: Optional[int] = None


def _get_tmdb_api_key() -> str:
    """Read the current TMDB credential from the environment."""
    return os.getenv("TMDB_API_KEY", "")


def _is_lookup_enabled_flag() -> bool:
    """Read the current IMDb lookup feature flag from the environment."""
    return os.getenv("IMDB_LOOKUP_ENABLED", "true").lower() == "true"


def _get_rate_limit_per_sec() -> int:
    """Read the current TMDB rate limit from the environment."""
    return int(os.getenv("IMDB_RATE_LIMIT_PER_SEC", "40"))


def _is_bearer_token(api_key: str) -> bool:
    """Detect whether the configured TMDB credential is a bearer token."""
    return api_key.startswith("eyJ") if api_key else False


def _get_rate_limit_semaphore() -> asyncio.Semaphore:
    """Lazily create a semaphore bound to the active event loop."""
    global _rate_limit_semaphore, _rate_limit_capacity

    current_loop = asyncio.get_running_loop()
    rate_limit = _get_rate_limit_per_sec()
    semaphore_loop = getattr(_rate_limit_semaphore, "_loop", None) if _rate_limit_semaphore else None
    if (
        _rate_limit_semaphore is None or
        _rate_limit_capacity != rate_limit or
        (semaphore_loop is not None and semaphore_loop is not current_loop)
    ):
        _rate_limit_semaphore = asyncio.Semaphore(rate_limit)
        _rate_limit_capacity = rate_limit
    return _rate_limit_semaphore


async def _rate_limited_request(url: str, params: Dict) -> Optional[Dict]:
    """Make rate-limited HTTP request to TMDB API.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        
    Returns:
        JSON response dict or None on error
    """
    global _last_request_time
    
    api_key = _get_tmdb_api_key()
    rate_limit = _get_rate_limit_per_sec()

    async with _get_rate_limit_semaphore():
        # Ensure we don't exceed rate limit
        now = asyncio.get_event_loop().time()
        time_since_last = now - _last_request_time
        if time_since_last < (1.0 / rate_limit):
            await asyncio.sleep((1.0 / rate_limit) - time_since_last)
        
        try:
            # Prepare headers (Bearer token or API key in params)
            headers = {}
            request_params = params.copy()
            
            if _is_bearer_token(api_key):
                # Use Bearer token in Authorization header
                headers["Authorization"] = f"Bearer {api_key}"
                # Remove api_key from params if present
                request_params.pop("api_key", None)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    params=request_params, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    _last_request_time = asyncio.get_event_loop().time()
                    
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        logger.warning("TMDB rate limit exceeded")
                        return None
                    elif resp.status == 401:
                        logger.error("TMDB API authentication failed - check API key")
                        return None
                    else:
                        logger.warning(f"TMDB API returned status {resp.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("TMDB API request timed out")
            return None
        except Exception as e:
            logger.error(f"TMDB API request failed: {e}")
            return None


async def _search_movie_tmdb(title: str, year: Optional[int] = None, language: str = "hu-HU") -> Optional[int]:
    """Search for a movie on TMDB and return its TMDB ID.
    
    Args:
        title: Movie title (can be Hungarian or English)
        year: Release year for better matching accuracy
        language: TMDB language code (default: hu-HU)
        
    Returns:
        TMDB movie ID or None if not found
    """
    url = f"{TMDB_BASE_URL}/search/movie"
    api_key = _get_tmdb_api_key()
    params = {
        "api_key": api_key,
        "query": title,
        "language": language,
    }
    
    if year:
        params["year"] = str(year)
    
    data = await _rate_limited_request(url, params)
    
    if not data or not data.get("results"):
        # Try again with English if Hungarian didn't work
        if language == "hu-HU":
            logger.debug(f"No results for '{title}' in Hungarian, trying English")
            return await _search_movie_tmdb(title, year, "en-US")
        return None
    
    # Return first result's TMDB ID
    return data["results"][0].get("id")


async def _get_imdb_id_from_tmdb(tmdb_id: int) -> Optional[str]:
    """Get IMDb ID from TMDB movie ID.
    
    Args:
        tmdb_id: TMDB movie ID
        
    Returns:
        IMDb ID (e.g., "tt0133093") or None
    """
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/external_ids"
    params = {"api_key": _get_tmdb_api_key()}
    
    data = await _rate_limited_request(url, params)
    
    if not data:
        return None
    
    imdb_id = data.get("imdb_id")
    if imdb_id and imdb_id.startswith("tt"):
        return imdb_id
    
    return None


async def _get_movie_details_from_tmdb(tmdb_id: int) -> Optional[Dict[str, Any]]:
    """Get full movie details from TMDB including poster.
    
    Args:
        tmdb_id: TMDB movie ID
        
    Returns:
        Dict with movie details including poster_path, or None
    """
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {"api_key": _get_tmdb_api_key()}
    
    data = await _rate_limited_request(url, params)
    return data


async def lookup_imdb_id(
    title: str,
    year: Optional[int] = None,
    language: str = "hu-HU"
) -> Optional[str]:
    """Look up IMDb ID for a movie title.
    
    This is the main entry point for IMDb lookups. It queries TMDB API
    and returns the IMDb ID if found. Results are cached automatically
    by the imdb_cache module.
    
    Args:
        title: Movie title (can be Hungarian or English)
        year: Release year for better matching accuracy
        language: TMDB language code (default: hu-HU)
    
    Returns:
        IMDb ID (e.g., "tt0133093") or None if not found
        
    Example:
        >>> imdb_id = await lookup_imdb_id("Mátrix", 1999)
        >>> print(imdb_id)
        "tt0133093"
    """
    result = await _lookup_imdb_core(title, year, language)
    if result:
        return result[1]
    return None


async def _lookup_imdb_core(
    title: str,
    year: Optional[int] = None,
    language: str = "hu-HU",
) -> Optional[Tuple[str, int]]:
    """Perform the minimal TMDB lookup flow needed to resolve an IMDb ID."""
    # Check if lookup is enabled
    if not _is_lookup_enabled_flag():
        logger.debug("IMDb lookup disabled via IMDB_LOOKUP_ENABLED")
        return None

    # Check if API key is configured
    if not _get_tmdb_api_key():
        logger.debug("IMDb lookup skipped - no TMDB_API_KEY configured")
        return None

    normalized_title = title.strip()

    try:
        cached_result = get_cached_imdb_id(normalized_title, year)
        if cached_result:
            return normalized_title, cached_result
        if cached_result is None:
            return None
    except KeyError:
        pass

    logger.debug(f"Looking up IMDb ID for '{normalized_title}' (year: {year})")

    try:
        tmdb_id = await _search_movie_tmdb(normalized_title, year, language)
        if not tmdb_id:
            logger.debug(f"No TMDB results for '{normalized_title}'")
            set_cached_imdb_id(normalized_title, year, None)
            return None

        imdb_id = await _get_imdb_id_from_tmdb(tmdb_id)
        set_cached_imdb_id(normalized_title, year, imdb_id)

        if not imdb_id:
            logger.debug(f"No IMDb ID found for TMDB movie {tmdb_id}")
            return None

        logger.info(f"Found IMDb ID {imdb_id} for '{normalized_title}'")
        return normalized_title, imdb_id
    except Exception as e:
        logger.error(f"Unexpected error during IMDb lookup for '{normalized_title}': {e}")
        return None


async def lookup_imdb_data(
    title: str,
    year: Optional[int] = None,
    language: str = "hu-HU"
) -> Optional[Dict[str, Any]]:
    """Look up IMDb data including ID and poster for a movie title.
    
    This function queries TMDB API and returns both IMDb ID and poster URL.
    Results are cached automatically by the imdb_cache module.
    
    Args:
        title: Movie title (can be Hungarian or English)
        year: Release year for better matching accuracy
        language: TMDB language code (default: hu-HU)
    
    Returns:
        Dict with {"imdb_id": str, "poster_url": str} or None if not found
        
    Example:
        >>> data = await lookup_imdb_data("Mátrix", 1999)
        >>> print(data)
        {"imdb_id": "tt0133093", "poster_url": "https://image.tmdb.org/..."}
    """
    core_result = await _lookup_imdb_core(title, year, language)
    if not core_result:
        return None

    normalized_title, imdb_id = core_result
    poster_url = None

    try:
        tmdb_id = await _search_movie_tmdb(normalized_title, year, language)
        if tmdb_id:
            details = await _get_movie_details_from_tmdb(tmdb_id)
            if details and details.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w500{details['poster_path']}"
    except Exception as e:
        logger.warning(f"Poster lookup failed for '{normalized_title}': {e}")

    return {
        "imdb_id": imdb_id,
        "poster_url": poster_url,
    }


async def batch_lookup_imdb_ids(
    movies: List[Tuple[str, Optional[int]]]
) -> Dict[str, Optional[str]]:
    """Batch lookup multiple movies (for optimization).
    
    This function performs concurrent lookups for multiple movies,
    respecting rate limits and caching.
    
    Args:
        movies: List of (title, year) tuples
    
    Returns:
        Dict mapping title to IMDb ID (or None if not found)
        
    Example:
        >>> movies = [("Matrix", 1999), ("Inception", 2010)]
        >>> results = await batch_lookup_imdb_ids(movies)
        >>> print(results)
        {"Matrix": "tt0133093", "Inception": "tt1375666"}
    """
    if not _is_lookup_enabled_flag() or not _get_tmdb_api_key():
        return {title: None for title, _ in movies}
    
    logger.info(f"Batch lookup for {len(movies)} movies")
    
    # Create lookup tasks
    tasks = [lookup_imdb_id(title, year) for title, year in movies]
    
    # Execute concurrently (respecting rate limits via semaphore)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map results back to titles
    result_dict = {}
    for (title, _), result in zip(movies, results):
        if isinstance(result, Exception):
            logger.error(f"Batch lookup failed for '{title}': {result}")
            result_dict[title] = None
        else:
            result_dict[title] = result
    
    successful = sum(1 for v in result_dict.values() if v is not None)
    logger.info(f"Batch lookup complete: {successful}/{len(movies)} successful")
    
    return result_dict


def is_lookup_enabled() -> bool:
    """Check if IMDb lookup is enabled and configured.
    
    Returns:
        True if TMDB API key is set and lookup is enabled
    """
    return _is_lookup_enabled_flag() and bool(_get_tmdb_api_key())


def get_api_status() -> Dict[str, Any]:
    """Get current API configuration and status.
    
    Returns:
        Dict with configuration details (safe for logging)
    """
    cache_stats = get_cache_stats()
    return {
        "enabled": _is_lookup_enabled_flag(),
        "api_key_configured": bool(_get_tmdb_api_key()),
        "rate_limit": _get_rate_limit_per_sec(),
        "base_url": TMDB_BASE_URL,
        "cache": cache_stats,
    }
