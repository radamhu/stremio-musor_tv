"""Catalog handler for Stremio addon."""
import os
import logging
from datetime import datetime
from typing import Any, Optional, Dict, List
from cache import create_cache
from time_window import compute_window, within_window
from scraper import fetch_live_movies
from utils import is_probably_film, slugify, strip_diacritics
from models import CatalogExtra, StremioMetaPreview


logger = logging.getLogger(__name__)

CACHE_TTL_MIN = int(os.getenv("CACHE_TTL_MIN", "10")) * 60_000

# Cache for meta previews derived from scraper
_cache = create_cache(CACHE_TTL_MIN)


async def catalog_handler(type_: str, id_: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, list]:
    """Handle catalog requests."""
    if type_ != "movie" or id_ != "hu-live":
        return {"metas": []}
    
    q: Dict[str, Any] = extra or {}
    time_window = compute_window(q.get("time"))
    cache_key = f"catalog:{q.get('time', 'now')}"
    
    logger.info(f"Fetching catalog for time window: {q.get('time', 'now')}")
    
    metas = _cache.get(cache_key)
    
    if not metas:
        logger.info("Cache miss, fetching live movies...")
        try:
            raw = await fetch_live_movies(False)
            logger.info(f"Fetched {len(raw)} raw items from scraper")
            
            filtered = [
                r for r in raw
                if is_probably_film(r.category) and within_window(r.start_iso, time_window)
            ]
            logger.info(f"Filtered to {len(filtered)} movies in time window")
            
            metas = []
            for r in filtered:
                start_time = datetime.fromisoformat(r.start_iso.replace("Z", "+00:00"))
                timestamp = int(start_time.timestamp())
                meta_id = f"musortv:{slugify(r.channel)}:{timestamp}:{slugify(r.title)}"
                genres = _parse_genres(r.category)
                
                metas.append(StremioMetaPreview(
                    id=meta_id,
                    type="movie",
                    name=r.title,
                    release_info=f"{_fmt_time(r.start_iso)} • {r.channel}",
                    poster=r.poster,
                    genres=genres
                ))
            
            logger.info(f"Created {len(metas)} meta previews")
            _cache.set(cache_key, metas)
        except Exception as e:
            logger.error(f"Failed to fetch and process movies: {e}", exc_info=True)
            # Return empty list on scraper failure
            metas = []
    else:
        logger.info(f"Cache hit, returning {len(metas)} metas")
    
    # Search filter (accent-insensitive)
    search = q.get("search", "").strip()
    if search:
        needle = strip_diacritics(search).lower()
        metas = [m for m in metas if needle in strip_diacritics(m.name).lower()]
    
    # Convert Pydantic models to dicts
    return {"metas": [m.model_dump() for m in metas]}


def _parse_genres(category: Optional[str]) -> Optional[List[str]]:
    """Parse and map Hungarian genre names."""
    if not category:
        return None
    
    base = category.split(",")[0] if "," in category else category
    lc = base.lower()
    
    if "akció" in lc:
        return ["Akció"]
    if "vígjáték" in lc:
        return ["Vígjáték"]
    if "dráma" in lc:
        return ["Dráma"]
    if "thriller" in lc:
        return ["Thriller"]
    if "horror" in lc:
        return ["Horror"]
    
    return [base.strip()]


def _fmt_time(iso: str) -> str:
    """Format ISO datetime to HH:MM format."""
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return d.strftime("%H:%M")
