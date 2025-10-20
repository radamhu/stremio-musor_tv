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


class StremioMeta(BaseModel):
    """Full Stremio metadata format for detailed movie information."""
    id: str
    type: Literal["movie"]
    name: str
    poster: Optional[str] = None
    background: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    releaseInfo: Optional[str] = None  # Year or date
    runtime: Optional[str] = None  # "120 min"
    genres: Optional[List[str]] = None
    director: Optional[List[str]] = None
    cast: Optional[List[str]] = None
    imdbRating: Optional[str] = None
    released: Optional[str] = None  # ISO date
    links: Optional[List[dict]] = None  # External links
    trailerStreams: Optional[List[dict]] = None
    behaviorHints: Optional[dict] = None


class StremioStream(BaseModel):
    """Stremio stream format."""
    url: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    behaviorHints: Optional[dict] = None
