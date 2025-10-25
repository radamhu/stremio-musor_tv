"""Meta handler for Stremio addon - provides detailed movie information."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from scraper import fetch_live_movies
from utils import is_probably_film, slugify
from models import StremioMeta


logger = logging.getLogger(__name__)


def parse_meta_id(meta_id: str) -> Optional[Dict[str, str]]:
    """Parse a musortv meta ID into its components.
    
    Expected format: musortv:channel-slug:timestamp:title-slug
    Example: musortv:mozi-hd:1760956800:fekete-kutya
    
    Args:
        meta_id: The meta ID to parse
        
    Returns:
        Dictionary with keys: channel_slug, timestamp, title_slug
        or None if parsing fails
    """
    if not meta_id.startswith("musortv:"):
        logger.warning(f"Invalid meta ID format (missing prefix): {meta_id}")
        return None
    
    parts = meta_id.split(":")
    if len(parts) != 4:
        logger.warning(f"Invalid meta ID format (wrong part count): {meta_id}")
        return None
    
    _, channel_slug, timestamp_str, title_slug = parts
    
    try:
        # Validate timestamp is numeric
        int(timestamp_str)
        
        return {
            "channel_slug": channel_slug,
            "timestamp": timestamp_str,
            "title_slug": title_slug
        }
    except ValueError:
        logger.warning(f"Invalid meta ID format (bad timestamp): {meta_id}")
        return None


async def meta_handler(type_: str, id_: str) -> Dict[str, Any]:
    """Handle meta requests - provide detailed movie information.
    
    Supports two ID formats:
    1. IMDb ID: tt1234567 (from catalog with IMDb lookup)
    2. Custom ID: musortv:channel:timestamp:title (fallback)
    
    Args:
        type_: Content type (should be "movie")
        id_: Meta ID (IMDb ID or musortv:channel:timestamp:title)
        
    Returns:
        Dictionary with "meta" key containing detailed movie information
    """
    logger.info(f"Meta request for {type_}/{id_}")
    
    # Validate type
    if type_ != "movie":
        logger.warning(f"Unsupported content type: {type_}")
        return {"meta": None}
    
    # Check if this is an IMDb ID or custom musortv ID
    if id_.startswith("tt") and id_[2:].isdigit():
        # IMDb ID format - need to match by title from catalog
        logger.info(f"IMDb ID detected: {id_}, fetching from catalog for title match")
        
        # Import here to avoid circular dependency
        from catalog_handler import catalog_handler
        
        # Get catalog to find the movie with this IMDb ID
        catalog_result = await catalog_handler(type_="movie", id_="hu-live", extra={})
        matching_meta = None
        
        for meta in catalog_result.get("metas", []):
            if meta.get("id") == id_:
                matching_meta = meta
                break
        
        if not matching_meta:
            logger.warning(f"No movie found in catalog with IMDb ID: {id_}")
            return {"meta": None}
        
        # Return the catalog meta (which already has all the info)
        # Convert StremioMetaPreview to full StremioMeta format
        return {"meta": matching_meta}
    
    # Custom musortv ID format
    parsed = parse_meta_id(id_)
    if not parsed:
        return {"meta": None}
    
    channel_slug = parsed["channel_slug"]
    timestamp_str = parsed["timestamp"]
    title_slug = parsed["title_slug"]
    
    # Fetch current live movies to find matching entry
    try:
        raw_movies = await fetch_live_movies(force=False)
        
        # Find the movie that matches our ID components
        matching_movie = None
        for movie in raw_movies:
            if not is_probably_film(movie.category):
                continue
            
            # Parse movie timestamp
            try:
                movie_start = datetime.fromisoformat(movie.start_iso.replace("Z", "+00:00"))
                movie_timestamp = int(movie_start.timestamp())
                
                # Check if this is the same movie
                if (slugify(movie.channel) == channel_slug and
                    str(movie_timestamp) == timestamp_str and
                    slugify(movie.title) == title_slug):
                    matching_movie = movie
                    break
            except (ValueError, AttributeError):
                continue
        
        if not matching_movie:
            logger.info(f"No matching movie found for ID: {id_}")
            return {"meta": None}
        
        # Build detailed metadata
        start_time = datetime.fromisoformat(matching_movie.start_iso.replace("Z", "+00:00"))
        time_str = start_time.strftime("%H:%M")
        date_str = start_time.strftime("%Y.%m.%d")
        
        # Parse genres
        genres = _parse_genres(matching_movie.category)
        
        # Enhanced description with all available information
        description_parts = []
        description_parts.append(f"📺 **Csatorna:** {matching_movie.channel}")
        description_parts.append(f"🕐 **Kezdés:** {date_str} {time_str}")
        if matching_movie.category:
            description_parts.append(f"🎬 **Műfaj:** {matching_movie.category}")
        description_parts.append("\n📡 **Élő adás a magyar TV-ből**")
        description_parts.append("\n💡 *Tipp: Használj stream kiegészítőt (pl. Torrentio) a megtekintéshez*")
        
        description = "\n".join(description_parts)
        
        # Create rich metadata
        meta = StremioMeta(
            id=id_,
            type="movie",
            name=matching_movie.title,
            poster=matching_movie.poster,
            background=matching_movie.poster,
            genres=genres,
            description=description,
            releaseInfo=f"📅 {date_str} • {time_str}",
            runtime=None,  # Unknown for live TV
            director=None,
            cast=None,
            links=[],
            behaviorHints={
                "defaultVideoId": None
            }
        )
        
        logger.info(f"Returning metadata for: {matching_movie.title}")
        return {"meta": meta.model_dump(exclude_none=True)}
        
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}", exc_info=True)
        return {"meta": None}


def _parse_genres(category: Optional[str]) -> Optional[list[str]]:
    """Parse and map Hungarian genre names."""
    if not category:
        return None
    
    base = category.split(",")[0] if "," in category else category
    lc = base.lower()
    
    genre_map = {
        "akció": "Akció",
        "vígjáték": "Vígjáték",
        "dráma": "Dráma",
        "thriller": "Thriller",
        "horror": "Horror",
        "sci-fi": "Sci-Fi",
        "fantasy": "Fantasy",
        "kaland": "Kaland",
        "romantikus": "Romantikus",
        "bűnügyi": "Bűnügyi",
        "western": "Western",
        "háborús": "Háborús",
        "dokumentum": "Dokumentumfilm",
        "animáció": "Animáció",
        "családi": "Családi"
    }
    
    for key, value in genre_map.items():
        if key in lc:
            return [value]
    
    # Default: return cleaned category
    return [base.strip().title()]
