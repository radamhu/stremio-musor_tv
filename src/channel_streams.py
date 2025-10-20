"""Channel stream URL mappings for Hungarian TV channels.

This module provides mappings from Hungarian TV channel names to their
streaming URLs. These can be IPTV M3U8 streams, direct video URLs, or
channel-specific streaming endpoints.

Note: Stream URLs may require updates as channels change their streaming infrastructure.
You should replace these with actual working stream URLs for Hungarian channels.
"""
import os
import logging
from typing import Optional, Dict
from utils import slugify


logger = logging.getLogger(__name__)


# Hungarian TV Channel Stream URLs
# TODO: Replace these placeholder URLs with actual working stream URLs
# These can be:
# - IPTV M3U8 streams (recommended for live TV)
# - Direct video URLs
# - Channel-specific streaming endpoints
# - YouTube live streams (if available)

CHANNEL_STREAM_MAP: Dict[str, str] = {
    # Public channels
    "m1": os.getenv("STREAM_M1", ""),
    "m2": os.getenv("STREAM_M2", ""),
    "m4-sport": os.getenv("STREAM_M4_SPORT", ""),
    "m5": os.getenv("STREAM_M5", ""),
    "duna-tv": os.getenv("STREAM_DUNA", ""),
    "duna-world": os.getenv("STREAM_DUNA_WORLD", ""),
    
    # Commercial channels
    "rtl": os.getenv("STREAM_RTL", ""),
    "rtl-ii": os.getenv("STREAM_RTL2", ""),
    "rtl-klub": os.getenv("STREAM_RTL_KLUB", ""),
    "tv2": os.getenv("STREAM_TV2", ""),
    "super-tv2": os.getenv("STREAM_SUPER_TV2", ""),
    "cool-tv": os.getenv("STREAM_COOL", ""),
    
    # Cable/satellite channels
    "film": os.getenv("STREAM_FILM", ""),
    "filmplus": os.getenv("STREAM_FILMPLUS", ""),
    "film4": os.getenv("STREAM_FILM4", ""),
    "hbo": os.getenv("STREAM_HBO", ""),
    "hbo-2": os.getenv("STREAM_HBO2", ""),
    "hbo-3": os.getenv("STREAM_HBO3", ""),
    "cinemax": os.getenv("STREAM_CINEMAX", ""),
    "cinemax-2": os.getenv("STREAM_CINEMAX2", ""),
    "amc": os.getenv("STREAM_AMC", ""),
    "amc-hd": os.getenv("STREAM_AMC_HD", ""),
    "paramount-network": os.getenv("STREAM_PARAMOUNT", ""),
    "comedy-central": os.getenv("STREAM_COMEDY_CENTRAL", ""),
    "paramount-channel": os.getenv("STREAM_PARAMOUNT_CHANNEL", ""),
    
    # International channels (Hungarian subtitles/dubs)
    "axn": os.getenv("STREAM_AXN", ""),
    "sony-channel": os.getenv("STREAM_SONY", ""),
    "universal-channel": os.getenv("STREAM_UNIVERSAL", ""),
    "prima-plus": os.getenv("STREAM_PRIMA_PLUS", ""),
    "prime": os.getenv("STREAM_PRIME", ""),
    
    # Other
    "viasat3": os.getenv("STREAM_VIASAT3", ""),
    "viasat6": os.getenv("STREAM_VIASAT6", ""),
}


def get_stream_url(channel_name: str) -> Optional[str]:
    """Get stream URL for a given channel name.
    
    Args:
        channel_name: The channel name as scraped from musor.tv
        
    Returns:
        Stream URL if available, None otherwise
    """
    if not channel_name:
        return None
    
    # Normalize channel name to slug format
    channel_slug = slugify(channel_name)
    
    # Look up in the mapping
    stream_url = CHANNEL_STREAM_MAP.get(channel_slug)
    
    if stream_url:
        logger.debug(f"Found stream URL for channel '{channel_name}' (slug: {channel_slug})")
        return stream_url
    else:
        logger.debug(f"No stream URL configured for channel '{channel_name}' (slug: {channel_slug})")
        return None


def get_available_channels() -> list[str]:
    """Get list of channels that have configured stream URLs.
    
    Returns:
        List of channel slugs that have stream URLs
    """
    return [k for k, v in CHANNEL_STREAM_MAP.items() if v]


def is_channel_supported(channel_name: str) -> bool:
    """Check if a channel has a configured stream URL.
    
    Args:
        channel_name: The channel name to check
        
    Returns:
        True if channel has a stream URL, False otherwise
    """
    return get_stream_url(channel_name) is not None
