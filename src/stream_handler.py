"""Stream handler for Stremio addon."""
import logging
from typing import Optional, Dict, List
from datetime import datetime
from models import StremioStream
from channel_streams import get_stream_url
from utils import slugify


logger = logging.getLogger(__name__)


def parse_stream_id(stream_id: str) -> Optional[Dict[str, str]]:
    """Parse a musortv stream ID into its components.
    
    Expected format: musortv:channel-slug:timestamp:title-slug
    Example: musortv:amc-hd:1760943000:rendorsztori
    
    Args:
        stream_id: The stream ID to parse
        
    Returns:
        Dictionary with keys: channel_slug, timestamp, title_slug
        or None if parsing fails
    """
    if not stream_id.startswith("musortv:"):
        logger.warning(f"Invalid stream ID format (missing prefix): {stream_id}")
        return None
    
    parts = stream_id.split(":")
    if len(parts) != 4:
        logger.warning(f"Invalid stream ID format (wrong part count): {stream_id}")
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
        logger.warning(f"Invalid stream ID format (bad timestamp): {stream_id}")
        return None


async def stream_handler(type_: str, id_: str) -> Dict[str, list]:
    """Handle stream requests.
    
    Args:
        type_: Content type (should be "movie")
        id_: Stream ID (format: musortv:channel:timestamp:title)
        
    Returns:
        Dictionary with "streams" key containing list of stream objects (as dicts)
    """
    logger.info(f"Stream request for {type_}/{id_}")
    
    # Validate type
    if type_ != "movie":
        logger.warning(f"Unsupported content type: {type_}")
        return {"streams": []}
    
    # Parse the ID
    parsed = parse_stream_id(id_)
    if not parsed:
        return {"streams": []}
    
    channel_slug = parsed["channel_slug"]
    timestamp = parsed["timestamp"]
    title_slug = parsed["title_slug"]
    
    # Get stream URL for the channel
    stream_url = get_stream_url(channel_slug)
    
    if not stream_url:
        logger.info(f"No stream URL configured for channel: {channel_slug}")
        return {"streams": []}
    
    # Format the timestamp for display
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        time_str = dt.strftime("%H:%M")
    except (ValueError, OSError):
        time_str = "Live"
    
    # Create stream object
    # Format channel name for display (convert slug back to readable name)
    channel_display = channel_slug.replace("-", " ").upper()
    
    stream = StremioStream(
        url=stream_url,
        name=f"🔴 {channel_display}",
        title=f"Live Stream - {channel_display}",
        description=f"Live stream from {channel_display} • Started at {time_str}",
        behaviorHints={
            "notWebReady": False,  # Can be played in web player
            "bingeGroup": f"channel-{channel_slug}"  # Group streams by channel
        }
    )
    
    logger.info(f"Returning stream for {channel_display}: {stream_url[:50]}...")
    
    return {"streams": [stream.model_dump()]}


async def get_streams_for_meta(channel_name: str, start_time: str, title: str) -> List[StremioStream]:
    """Get stream objects for a specific movie/show.
    
    This is a helper function for use in catalog handlers if needed.
    
    Args:
        channel_name: Name of the channel
        start_time: ISO format start time
        title: Title of the show
        
    Returns:
        List of StremioStream objects
    """
    stream_url = get_stream_url(channel_name)
    
    if not stream_url:
        return []
    
    # Parse start time
    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M")
    except (ValueError, OSError):
        time_str = "Live"
    
    channel_display = channel_name.upper()
    
    stream = StremioStream(
        url=stream_url,
        name=f"🔴 {channel_display}",
        title=f"{title} - {channel_display}",
        description=f"Live from {channel_display} • {time_str}",
        behaviorHints={
            "notWebReady": False,
            "bingeGroup": f"channel-{slugify(channel_name)}"
        }
    )
    
    return [stream]
