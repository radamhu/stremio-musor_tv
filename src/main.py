"""Main FastAPI application for Stremio HU Live Movies addon."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from urllib.parse import unquote
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from manifest import MANIFEST
from catalog_handler import catalog_handler
from meta_handler import meta_handler
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback


# Configuration
PORT = int(os.getenv("PORT", "7000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()

# Setup Rich console and traceback
console = Console()
install_rich_traceback(show_locals=True, suppress=[])

# Setup Rich logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
            show_time=True,
            show_path=True,
        )
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting Stremio HU Live Movies addon")
    yield
    # Shutdown
    logger.info("Shutting down addon, cleaning up resources...")
    from scraper import cleanup_scraper
    await cleanup_scraper()
    logger.info("Cleanup complete")


# Create FastAPI app with lifecycle management
app = FastAPI(title="Stremio HU Live Movies", lifespan=lifespan)

# Add CORS middleware to allow requests from Stremio clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Stremio compatibility
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def root():
    """Root endpoint - redirect to manifest."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/manifest.json")


@app.get("/healthz")
async def health_check():
    """Health check endpoint with scraper and IMDb lookup status."""
    import time
    from scraper import get_scraper_status
    from imdb_lookup import get_api_status
    
    scraper_status = await get_scraper_status()
    imdb_status = get_api_status()
    
    return {
        "ok": scraper_status.get("healthy", False),
        "ts": int(time.time() * 1000),
        "scraper": scraper_status,
        "imdb_lookup": imdb_status
    }


@app.get("/manifest.json")
async def get_manifest():
    """Return Stremio addon manifest."""
    return JSONResponse(content=MANIFEST)


@app.get("/catalog/{type}/{id}.json")
async def get_catalog(
    type: str,
    id: str,
    search: str = Query(None),
    time: str = Query(None)
):
    """Handle catalog requests."""
    try:
        extra = {}
        if search:
            extra["search"] = search
        if time:
            extra["time"] = time
        
        result = await catalog_handler(type, id, extra)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in catalog handler: {e}", exc_info=True)
        # Return empty catalog instead of 500 error
        return JSONResponse(
            content={"metas": []},
            status_code=200  # Return 200 with empty results for better UX
        )


@app.get("/meta/{type}/{id}.json")
async def get_meta(type: str, id: str):
    """Handle meta requests - provide detailed movie information.
    
    This endpoint returns rich metadata about a specific movie,
    including description, genres, broadcast time, and channel info.
    """
    # Decode the ID (in case of URL encoding)
    raw_id = id
    id = unquote(id)
    if id != raw_id:
        logger.debug(f"Decoded meta id from '{raw_id}' to '{id}'")
    
    logger.info(f"Meta request for {type}/{id}")
    
    try:
        result = await meta_handler(type, id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in meta handler: {e}", exc_info=True)
        # Return empty meta instead of 500 error
        return JSONResponse(
            content={"meta": None},
            status_code=200  # Return 200 with null meta for better UX
        )


@app.get("/stream/{type}/{id}.json")
async def get_stream(type: str, id: str):
    """Handle stream requests - catalog addon design.
    
    This is a CATALOG/DISCOVERY addon that shows what's on Hungarian TV.
    It does NOT provide streams - that's the job of stream provider addons
    (like Torrentio, Cinemeta, etc.) that users install separately.
    
    Benefits of this design:
    - Separation of concerns (discovery vs. streaming)
    - Users choose their preferred stream sources
    - No legal liability for stream URLs
    - Works with any stream provider addon
    - Follows Stremio's modular architecture
    
    This endpoint returns empty streams to indicate:
    "Content exists in catalog, but use your stream addons to watch it"
    """
    # Starlette/FastAPI decodes path params, but some clients may double-encode.
    # Apply a defensive unquote to ensure we operate on a clean ID.
    raw_id = id
    id = unquote(id)
    if id != raw_id:
        logger.debug(f"Decoded stream id from '{raw_id}' to '{id}'")
    
    # Log with decoded ID for clarity
    logger.info(f"Stream request for {type}/{id} (catalog-only addon)")
    
    # Validate musortv ID format
    if id.startswith("musortv:"):
        # This is our catalog item - let stream addons handle it
        return JSONResponse(content={
            "streams": []
        })
    
    # Not our ID - ignore
    return JSONResponse(content={"streams": []})


@app.get("/favicon.ico")
async def get_favicon():
    """Return a simple favicon to prevent 404 errors."""
    from fastapi.responses import Response
    # Return a minimal 1x1 transparent ICO file
    # This is a base64 decoded minimal ICO format
    ico_data = (
        b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00'
        b'(\x00\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x01\x00\x00\x00'
        b'\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00\x00\x00'
    )
    return Response(content=ico_data, media_type="image/x-icon")


if __name__ == "__main__":
    import uvicorn
    from rich.panel import Panel
    
    # Display startup banner with Rich
    console.print(Panel.fit(
        f"[bold cyan]Stremio HU Live Movies Addon[/bold cyan]\n"
        f"[green]Port:[/green] {PORT}\n"
        f"[green]Log Level:[/green] {LOG_LEVEL}\n"
        f"[green]Cache TTL:[/green] {os.getenv('CACHE_TTL_MIN', '10')} min\n"
        f"[green]Scrape Rate:[/green] {os.getenv('SCRAPE_RATE_MS', '30000')} ms",
        title="🎬 Starting Server",
        border_style="cyan"
    ))
    
    logger.info(f"Starting addon on port {PORT}")
    uvicorn.run(
        "main:app",  # Import string for auto-reload
        host="0.0.0.0",
        port=PORT,
        log_level=LOG_LEVEL.lower(),
        reload=True  # Auto-reload on code changes
    )
