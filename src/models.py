"""Type definitions for Stremio HU Live Movies addon."""
from typing import Literal, TypedDict, Optional, List
from pydantic import BaseModel


TimePreset = Literal["now", "next2h", "tonight"]


class CatalogExtra(TypedDict, total=False):
    """Extra parameters for catalog requests."""
    search: str
    time: TimePreset


class LiveMovieRaw(BaseModel):
    """Raw movie data from scraper."""
    title: str
    start_iso: str  # ISO format datetime string
    channel: str
    category: Optional[str] = None
    poster: Optional[str] = None
    # Note: stream_url removed - catalog addons don't provide streams


class StremioMetaPreview(BaseModel):
    """Stremio metadata preview format."""
    id: str
    type: Literal["movie"]
    name: str
    release_info: Optional[str] = None  # "21:00 • RTL"
    poster: Optional[str] = None
    background: Optional[str] = None
    genres: Optional[List[str]] = None
    description: Optional[str] = None  # Enhanced: Include channel and time info
    
    # Note: stream_url removed - this is a catalog addon
    # Stream provider addons will provide the actual streams
