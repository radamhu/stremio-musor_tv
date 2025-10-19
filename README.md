# Stremio HU Live Movies Addon

A **Stremio addon** that provides real-time catalogs of movies currently airing or scheduled to air on Hungarian TV channels by scraping TV listings from [musor.tv](https://musor.tv).

## 📢 Recent Updates

### ✅ Midnight Boundary Fix (Oct 18, 2025)
Fixed a bug where late-night programs (00:00-06:00) were incorrectly dated when scraped in the evening. The time parser now uses a 12-hour threshold to detect midnight boundary crossings, ensuring programs after midnight appear in the correct time windows.

**Impact:** Users browsing at 23:00 will now correctly see movies scheduled for 01:00 as "upcoming" rather than "22 hours ago".

📖 **Documentation:** [MIDNIGHT_BOUNDARY_FIX.md](docs/MIDNIGHT_BOUNDARY_FIX.md) | [IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)

## 🎯 Purpose

This addon integrates with the Stremio media center to allow users to:
- Browse movies currently playing on Hungarian TV
- Search for specific titles (with accent-insensitive Hungarian text support)
- Filter by time windows (now playing, next 2 hours, tonight)
- View movie metadata including start times, channels, genres, and posters

The addon exposes HTTP/JSON endpoints that comply with the Stremio addon protocol, making Hungarian live TV content discoverable within the Stremio interface.

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREMIO CLIENT                            │
│                    (User's media center)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/JSON
                            │ GET /catalog/movie/hu-live.json
                            │     ?time=now&search=matrix
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER                              │
│                        (main.py)                                 │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ /manifest  │  │  /catalog    │  │   /healthz   │           │
│  │   .json    │  │  /{type}/{id}│  │              │           │
│  └────────────┘  └──────┬───────┘  └──────────────┘           │
└─────────────────────────┼────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CATALOG HANDLER                                │
│                 (catalog_handler.py)                             │
│                                                                  │
│  1. Parse query params (time, search)                           │
│  2. Check cache                         ┌──────────────────┐   │
│  3. Filter by category & time    ◄─────►│  CACHE LAYER     │   │
│  4. Transform to Stremio format         │  (cache.py)      │   │
│  5. Apply search filter                 │  TTL: 10 min     │   │
│                                          └──────────────────┘   │
└──────────┬───────────────────────────────────────────────────────┘
           │ Cache miss
           │ fetch_live_movies()
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WEB SCRAPER                                 │
│                     (scraper.py)                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐        │
│  │  Rate Limiting: 30s between scrapes                │        │
│  │  In-flight dedup: one scrape at a time             │        │
│  └────────────────────────────────────────────────────┘        │
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │  PLAYWRIGHT BROWSER  │                                       │
│  │  (Headless Chromium) │                                       │
│  └──────────┬───────────┘                                       │
│             │ Navigate to pages                                 │
│             │ Extract data via CSS selectors                    │
└─────────────┼───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MUSOR.TV WEBSITE                            │
│              (External Hungarian TV guide)                       │
│                                                                  │
│  Pages scraped:                                                  │
│  • https://musor.tv/most/tvben                                  │
│  • https://musor.tv/filmek                                      │
└─────────────────────────────────────────────────────────────────┘

```

### Key Services

1. **FastAPI Web Server** (`main.py`)
   - Entry point exposing HTTP/JSON endpoints
   - Routes: `/manifest.json`, `/catalog/{type}/{id}.json`, `/healthz`
   - Handles query parameters for search and time filtering

2. **Catalog Handler** (`catalog_handler.py`)
   - Business logic layer that orchestrates data retrieval and transformation
   - Manages caching strategy (cache key based on time preset)
   - Filters content by category (films vs. series)
   - Transforms raw scraper data into Stremio-compatible metadata
   - Implements accent-insensitive search for Hungarian titles

3. **Web Scraper** (`scraper.py`)
   - Playwright-based headless browser automation
   - Scrapes multiple musor.tv pages concurrently
   - Implements rate limiting (30s default) and deduplication
   - Manages browser instance lifecycle with module-level state
   - Handles cookie consent popups automatically

4. **Time Window Filter** (`time_window.py`)
   - Computes time ranges based on presets:
     - `now`: next 90 minutes
     - `next2h`: next 2 hours
     - `tonight`: 18:00-23:59 today
   - Filters program start times within computed windows

5. **Caching Layer** (`cache.py`)
   - TTL-based in-memory cache (default: 10 minutes)
   - Reduces scraping frequency and improves response times
   - Uses `cachetools.TTLCache` with max 64 entries

6. **Utilities & Models**
   - `models.py`: Pydantic data models (`LiveMovieRaw`, `StremioMetaPreview`)
   - `utils.py`: Text processing (slugify, diacritics removal, film detection)
   - `manifest.py`: Stremio addon manifest configuration

### Data Flow

1. **HTTP Request** arrives at FastAPI server with optional `search` and `time` parameters
2. **Catalog Handler** checks cache for the requested time preset
3. **Cache Miss** → Scraper fetches live data from musor.tv using Playwright
4. **Raw Data** is filtered by:
   - Category (must be a film, not a series)
   - Time window (must fall within selected time range)
5. **Transformation** to Stremio format with metadata:
   - Unique ID generation: `musortv:{channel}:{timestamp}:{title-slug}`
   - Release info formatting: `"21:00 • RTL"`
   - Genre mapping (Hungarian → standardized)
6. **Caching** of transformed results with TTL
7. **Search Filter** applied if provided (accent-insensitive)
8. **JSON Response** returned to Stremio client

## 📁 Project Structure

```
stremio-musor_tv/
├── src/                     # Main application code
│   ├── main.py              # FastAPI server entry point
│   ├── manifest.py          # Stremio addon manifest
│   ├── catalog_handler.py   # Business logic & orchestration
│   ├── scraper.py           # Playwright web scraper
│   ├── time_window.py       # Time filtering logic
│   ├── cache.py             # TTL cache wrapper
│   ├── utils.py             # Text utilities (slugify, diacritics)
│   ├── models.py            # Pydantic data models
│   └── __init__.py          # Package marker
├── docs/                    # Documentation
│   └── CODE_ANALYSIS_PROMPT.md
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Docker Compose configuration
├── run_python.sh            # Quick start script
└── README.md                # This file
```

## 🚀 Quick Start

### Dependencies

**Core Stack:**
- Python 3.11+
- FastAPI 0.115.0 (async web framework)
- Uvicorn 0.30.6 (ASGI server)
- Pydantic 2.9.2 (data validation & serialization)

**Scraping & Caching:**
- Playwright 1.47.0 (headless Chromium browser automation)
- cachetools 5.5.0 (TTL cache implementation)
- python-dotenv 1.0.1 (environment configuration)

**Deployment:**
- Docker + Docker Compose
- Chromium browser installed in container

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- 2GB+ RAM (for Chromium browser)

### Local Development

```bash
# Python environment setup
pyenv virtualenv 3.9.18 stremio-musor-tv
pyenv local stremio-musor-tv
pyenv activate stremio-musor-tv

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium

# Run the application
cd src
python main.py
```

The addon will be available at `http://localhost:7000`

### Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The containerized addon will be available at `http://localhost:7000`

### Cloud Deployment (Render)

For production deployment on Render.com:

```bash
# See detailed deployment guide
📖 docs/RENDER_DEPLOYMENT.md
```

Quick steps:
1. Push repository to GitHub/GitLab
2. Connect to Render Blueprint
3. Render auto-detects `render.yaml` and builds Docker image
4. Your addon will be at: `https://your-app.onrender.com`

**Note:** Make sure Render is configured to use **Docker runtime** (not Python) so Playwright browsers are properly installed.

## ⚙️ Configuration

### Environment Variables

All configuration is done via environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | HTTP server port | `7000` | No |
| `LOG_LEVEL` | Logging verbosity (`debug`/`info`/`warning`/`error`) | `info` | No |
| `CACHE_TTL_MIN` | Cache TTL in minutes | `10` | No |
| `SCRAPE_RATE_MS` | Minimum milliseconds between scrapes | `30000` | No |
| `TZ` | Timezone (MUST be `Europe/Budapest` for correct times) | - | **Yes** |

### Configuration in Docker

Edit `docker-compose.yml`:

```yaml
environment:
  - TZ=Europe/Budapest
  - PORT=7000
  - CACHE_TTL_MIN=15
  - SCRAPE_RATE_MS=45000
  - LOG_LEVEL=debug
```

### Configuration for Local Development

Create a `.env` file in the project root:

```bash
PORT=7000
LOG_LEVEL=info
CACHE_TTL_MIN=10
SCRAPE_RATE_MS=30000
TZ=Europe/Budapest
```

## 🔍 API Endpoints

### Stremio Protocol Endpoints

#### `GET /manifest.json`
Returns the Stremio addon manifest.

**Response:**
```json
{
  "id": "hu.live.movies",
  "version": "1.0.0",
  "name": "HU Live Movies (musor.tv)",
  "resources": ["catalog"],
  "types": ["movie"],
  "catalogs": [...]
}
```

#### `GET /catalog/movie/hu-live.json`
Returns the catalog of live movies.

**Query Parameters:**
- `search` (optional): Filter by title (accent-insensitive)
  - Example: `?search=matrix` matches "Mátrix"
- `time` (optional): Time filter preset
  - `now` (default): Movies in next 90 minutes
  - `next2h`: Movies in next 2 hours
  - `tonight`: Movies from 18:00 to 23:59 today

**Examples:**
```bash
# All movies airing now
curl http://localhost:7000/catalog/movie/hu-live.json

# Movies in next 2 hours
curl http://localhost:7000/catalog/movie/hu-live.json?time=next2h

# Search for specific title
curl http://localhost:7000/catalog/movie/hu-live.json?search=james+bond

# Combined search and time filter
curl http://localhost:7000/catalog/movie/hu-live.json?time=tonight&search=horror
```

**Response:**
```json
{
  "metas": [
    {
      "id": "musortv:rtl:1697654400:matrix",
      "type": "movie",
      "name": "Mátrix",
      "release_info": "21:00 • RTL",
      "poster": "https://musor.tv/...",
      "genres": ["Akció"]
    }
  ]
}
```


## 🤝 Stremio Integration

### Installing the Addon

1. Run the addon server (locally or via Docker)
2. Open Stremio
3. Go to Addons → Community Addons
4. Click "Install from URL"
5. Enter: `http://localhost:7000/manifest.json`
6. The addon will appear in your Discover catalog

### Usage in Stremio

- Navigate to **Movies** in Stremio
- Find the **"Live on TV (HU)"** catalog
- Browse current and upcoming Hungarian TV movies
- Use search to find specific titles
- Click on a movie to see details (start time, channel)

**Note:** This addon only provides **metadata** (what's on TV), not streaming links.

## 🔗 Related Documentation

- [Copilot Instructions](/.github/instructions/copilot-instructions.md) - Development guidelines
- [Code Analysis Prompt](/docs/CODE_ANALYSIS_PROMPT.md) - Analysis methodology


![Build and Push](https://github.com/radamhu/stremio-musor_tv/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![CI](https://github.com/radamhu/stremio-musor_tv/workflows/CI%20-%20Tests%20and%20Linting/badge.svg)

## 📄 License

Same as the original TypeScript version.
