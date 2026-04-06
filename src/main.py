"""Main FastAPI application for Stremio HU Live Movies addon."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
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


@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    """Root endpoint - HTML landing page."""
    from fastapi.responses import HTMLResponse
    
    # Get the base URL dynamically from the request or environment variable
    base_url = os.getenv("BASE_URL")
    if not base_url:
        netloc = request.url.netloc
        # Honour X-Forwarded-Proto set by reverse proxies (e.g. Render, nginx)
        # so the install link uses https:// even when the internal hop is http.
        forwarded_proto = request.headers.get("x-forwarded-proto")
        scheme = forwarded_proto or request.url.scheme
        base_url = f"{scheme}://{netloc}"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HU Live Movies (musor.tv) - Stremio Addon</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }}
        
        .logo {{
            width: 120px;
            height: auto;
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        
        h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            color: #2d3748;
        }}
        
        .version {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        
        .description {{
            font-size: 1.1em;
            color: #4a5568;
            line-height: 1.6;
            margin-bottom: 30px;
        }}
        
        .features {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: left;
        }}
        
        .features h3 {{
            color: #2d3748;
            font-size: 1.1em;
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .features ul {{
            list-style: none;
            padding: 0;
        }}
        
        .features li {{
            padding: 8px 0;
            color: #4a5568;
            display: flex;
            align-items: center;
        }}
        
        .features li:before {{
            content: "•";
            color: #667eea;
            font-weight: bold;
            font-size: 1.5em;
            margin-right: 10px;
        }}
        
        .install-btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            padding: 16px 40px;
            border-radius: 30px;
            font-weight: 600;
            font-size: 1.1em;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            margin-bottom: 20px;
        }}
        
        .install-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}
        
        .support {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
        }}
        
        .support-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }}
        
        .support-link:hover {{
            color: #764ba2;
        }}
        
        .info {{
            margin-top: 20px;
            padding: 15px;
            background: #fff5f5;
            border-left: 4px solid #fc8181;
            border-radius: 4px;
            text-align: left;
            font-size: 0.9em;
            color: #742a2a;
        }}
        
        .info strong {{
            color: #c53030;
        }}
        
        code {{
            background: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="https://musor.tv/images/etc/logo_small.png" alt="musor.tv logo" class="logo">
        
        <h1>🇭🇺 HU Live Movies</h1>
        <span class="version">v{MANIFEST['version']}</span>
        
        <p class="description">
            {MANIFEST['description']}
        </p>
        
        <div class="features">
            <h3>✨ This addon provides:</h3>
            <ul>
                <li>Movies currently airing on Hungarian TV</li>
                <li>Time filters (Now, Next 2h, Tonight)</li>
                <li>IMDb ID matching for stream providers</li>
                <li>Accent-insensitive search</li>
                <li>Real-time TV schedule from musor.tv</li>
            </ul>
        </div>
        
        <a href="stremio://{base_url.removeprefix('https://').removeprefix('http://')}/manifest.json" class="install-btn">
            📺 INSTALL IN STREMIO
        </a>
        
        <div class="info">
            <strong>Note:</strong> This is a <strong>catalog-only addon</strong>. 
            It discovers content on Hungarian TV. Install stream provider addons 
            (like <code>Torrentio</code>, <code>MediaFusion</code>) to watch the movies.
        </div>
        
        <div class="support">
            <p style="color: #718096; margin-bottom: 10px;">☕ Enjoying this addon?</p>
            <a href="https://ko-fi.com/radamhu" class="support-link" target="_blank" rel="noopener">
                <span>Support on Ko-fi</span>
                <span>→</span>
            </a>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


@app.api_route("/healthz", methods=["GET", "HEAD"])
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
    """Handle catalog requests with query parameters."""
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


@app.get("/catalog/{type}/{id}/{extra}.json")
async def get_catalog_with_extra(
    type: str,
    id: str,
    extra: str
):
    """Handle catalog requests with extra parameters in path (Stremio format).
    
    Stremio often encodes extra parameters in the path like:
    /catalog/movie/hu-live/search=matrix.json
    /catalog/movie/hu-live/time=tonight.json
    /catalog/movie/hu-live/search=matrix&time=tonight.json
    """
    try:
        # Parse extra parameters from path
        extra_params = {}
        
        # Decode URL-encoded characters
        extra_decoded = unquote(extra)
        
        # Split by & for multiple parameters
        pairs = extra_decoded.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                extra_params[key] = value
        
        logger.info(f"Catalog request with path extras: {extra_params}")
        
        result = await catalog_handler(type, id, extra_params)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in catalog handler with extras: {e}", exc_info=True)
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
