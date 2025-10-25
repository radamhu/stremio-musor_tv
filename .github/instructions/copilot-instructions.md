# Copilot Instructions

## Project Overview

This is a **Stremio addon** that scrapes Hungarian TV listings from musor.tv and exposes a catalog of currently airing movies via HTTP/JSON endpoints. The addon is built with Python and FastAPI, uses Playwright for web scraping, and provides time-filtered movie catalogs (now/next2h/tonight) with search capabilities.

**Key Features:**
- Real-time scraping of Hungarian TV listings
- Time-based filtering (now playing, next 2 hours, tonight)
- Accent-insensitive search for Hungarian titles
- In-memory TTL-based caching
- Docker deployment ready

## Repository Structure

```
stremio-musor_tv/
├── src/                     # Main application code (Python)
│   ├── main.py             # FastAPI server entry point
│   ├── manifest.py         # Stremio addon manifest configuration
│   ├── catalog_handler.py  # Catalog request handler (business logic)
│   ├── meta_handler.py     # Meta endpoint handler
│   ├── scraper.py          # Playwright web scraper for musor.tv
│   ├── time_window.py      # Time filtering logic
│   ├── cache.py            # TTL cache wrapper (cachetools)
│   ├── imdb_cache.py       # IMDb metadata caching
│   ├── imdb_lookup.py      # IMDb search and metadata lookup
│   ├── utils.py            # Utility functions (slugify, diacritics)
│   ├── models.py           # Pydantic models and type definitions
│   └── __init__.py         # Package marker with version
├── tests/                   # Test suite
│   ├── test_imdb_lookup.py
│   ├── test_midnight_boundary.py
│   ├── test_scraper_refactor.py
│   ├── test_stream_endpoint.py
│   └── test_stream_support.py
├── debug/                   # Debug scripts
│   ├── debug_selectors_v2.py
│   ├── debug_selectors.py
│   ├── demo_midnight_fix.py
│   ├── dump_html.py
│   └── validate_stream_endpoint.py
├── docs/                    # Project documentation
│   ├── CATALOG_ONLY_DESIGN.md
│   ├── ERROR_HANDLING_IMPROVEMENTS.md
│   ├── IMDB_LOOKUP_SPEC.md
│   ├── META_ENDPOINT_IMPLEMENTATION.md
│   └── ...
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Docker Compose configuration
├── render.yaml             # Render.com deployment config
└── README.md               # Main documentation
```

## Coding Standards

### Naming Conventions
- **snake_case**: functions, variables, module names (`fetch_live_movies`, `time_window`)
- **PascalCase**: classes, Pydantic models (`LiveMovieRaw`, `StremioMetaPreview`)
- **UPPER_SNAKE_CASE**: constants and environment variables (`CACHE_TTL_MIN`, `PORT`)

### Type Hints
- All function signatures must include type hints
- Use Pydantic models for data validation and serialization
- Use `Optional[T]` or `T | None` for nullable types
- Use `Literal` for string enums (e.g., `Literal["now", "next2h", "tonight"]`)

### Code Style
- Use f-strings for string formatting
- Async/await for all I/O operations (HTTP, scraping, file access)
- Use Python logging module (never `print()` statements)
- Prefer explicit over implicit (clear variable names, no magic values)

### Import Order
1. Standard library imports (`import os`, `from datetime import datetime`)
2. Third-party imports (`from fastapi import FastAPI`, `from playwright.async_api import async_playwright`)
3. Local module imports (`from models import LiveMovieRaw`, `from utils import slugify`)

### Error Handling
- Use try-except blocks in async scraper logic
- Never crash the server on scraper failures (return empty list)
- Log errors with appropriate levels (DEBUG, INFO, WARNING, ERROR)
- FastAPI handles HTTP errors automatically

## Technology Stack

**Core Framework:**
- Python 3.11+
- FastAPI 0.115.0 (web framework)
- Uvicorn 0.30.6 (ASGI server)
- Pydantic 2.9.2 (data validation)

**Dependencies:**
- playwright 1.47.0 (browser automation, Chromium)
- cachetools 5.5.0 (TTL-based in-memory cache)
- python-dotenv 1.0.1 (environment variables)

**Deployment:**
- Docker (Dockerfile)
- Docker Compose (docker-compose.yml)
- Render.com (render.yaml)

## Environment Variables

```bash
PORT=7000               # Server port (default: 7000)
CACHE_TTL_MIN=10        # Cache TTL in minutes (default: 10)
SCRAPE_RATE_MS=30000    # Rate limit between scrapes in ms (default: 30000)
LOG_LEVEL=info          # Logging level: debug|info|warning|error (default: info)
TZ=Europe/Budapest      # Timezone - MUST be Europe/Budapest for correct time calculations
```

## Critical Project-Specific Rules

### Timezone
- **ALWAYS** use `Europe/Budapest` timezone
- Set in Dockerfile via `TZ` environment variable
- All time calculations assume this timezone
- Never change this value

### CSS Selectors (scraper.py)
- Selectors are fragile and may break when musor.tv updates their HTML
- Use fallback patterns: `.class1, .class2, .class3`
- Test selectors thoroughly after any musor.tv changes
- Located around line 50 in `scraper.py`

### Caching Strategy
- Cache key format: `catalog:{time_preset}` (e.g., `catalog:now`)
- Default TTL: 10 minutes (configurable via `CACHE_TTL_MIN`)
- Maximum 64 cache entries (LRU eviction)
- Cache invalidation happens automatically on time preset change

### Hungarian Text Handling
- Use `strip_diacritics()` from `utils.py` for text comparison
- Enables accent-insensitive search (e.g., "Matriz" matches "Mátrix")
- Apply to both search queries and movie titles

## Common Development Tasks

### Adding New Time Presets
1. Update `TimePreset` type in `time_window.py`
2. Add new case in `compute_window()` function
3. Update manifest extra options in `manifest.py`

### Modifying Genre Mapping
Edit `_parse_genres()` in `catalog_handler.py`:
```python
if "új_kulcsszó" in lc:
    return ["Új Műfaj"]
```

### Updating Scraper Selectors
Edit `scraper.py` around line 50:
```python
cards = page.locator(".card, .program, .új-selector")
title = await el.locator("h3, .title, .új-title-class").first.text_content()
```

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the server
cd src && python main.py

# Or use Docker
docker-compose up
```

## API Endpoints

- `GET /manifest.json` - Stremio addon manifest
- `GET /catalog/movie/hu-live.json` - Movie catalog (supports `?search=` and `?time=` params)
- `GET /meta/movie/{imdb_id}.json` - Movie metadata with IMDb lookup
- `GET /stream/movie/{imdb_id}.json` - Stream links (not supported, returns empty)
- `GET /healthz` - Health check endpoint

## Known Limitations

1. **CSS selectors are fragile** - Will break when musor.tv changes their HTML structure
2. **No browser restart** - Chromium crash will bring down the addon (requires manual restart)
3. **Rate limiting** - Minimum 30 seconds between scrape requests to avoid overloading musor.tv
4. **Stream endpoint not supported** - Only catalog and meta endpoints are implemented
5. **IMDb lookup may be slow** - First lookup for a movie requires web search

## Version

Current: 1.0.0 (see `src/__init__.py`)