# Stremio HU Live Movies Addon

A **catalog-only Stremio addon** that discovers movies currently airing or scheduled on Hungarian TV channels. This addon scrapes real-time TV listings from [musor.tv](https://musor.tv) and provides IMDb-matched metadata, enabling seamless integration with your favorite stream provider addons (Torrentio, MediaFusion, etc.).

## 🎯 Purpose

This addon integrates with the Stremio media center to allow users to:
- **Discover** movies currently playing on Hungarian TV
- Filter by time windows (now playing, next 2 hours, tonight)
- Search for specific titles (with accent-insensitive Hungarian text support)
- View movie metadata including start times, channels, genres, and posters
- **Get IMDb IDs** for automatic stream matching with other addons

**Architecture Philosophy: Catalog-Only Design**

This is a **discovery addon**, not a streaming addon. It answers "What's on TV?" and provides IMDb IDs so your stream provider addons (like Torrentio, Comet, MediaFusion) can automatically provide torrents or direct streams.

**Benefits:**
- ✅ **Separation of concerns** - We discover, others stream
- ✅ **User choice** - Pick your preferred stream sources
- ✅ **Legal clarity** - Just TV schedule info, no streaming URLs
- ✅ **Better quality** - Stream addons provide HD torrents vs. live TV quality
- ✅ **Flexibility** - Works with any stream provider addon in the ecosystem

The addon exposes HTTP/JSON endpoints that comply with the Stremio addon protocol, making Hungarian live TV content discoverable within the Stremio interface.

## 📢 Recent Updates

![Build and Push](https://github.com/radamhu/stremio-musor_tv/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)

### 🎬 IMDb Integration (Oct 25, 2025)
**Major Feature**: Added automatic IMDb ID lookup for Hungarian TV movies using TMDB API.

**What's New:**
- Movies now get matched to their IMDb IDs automatically
- Works seamlessly with stream provider addons (Torrentio, etc.)
- **Success rate: ~75%** for popular international movies
- Intelligent caching (7-day TTL) to minimize API calls
- Falls back gracefully to custom IDs when IMDb match not found
- Supports both TMDB API keys and Bearer tokens (JWT)

**How It Works:**
```
Hungarian TV listing → TMDB API lookup → IMDb ID → Your stream addons recognize it!
Example: "Mátrix" on RTL → tt0133093 → Torrentio provides torrents ✅
```

**Setup (Optional but Recommended):**
1. Get free TMDB API key: https://www.themoviedb.org/settings/api
2. Add to `.env`: `TMDB_API_KEY=your_key_here`
3. Restart addon
4. Enjoy better stream matching!

📖 **Documentation:** [IMDb Lookup Spec](docs/IMDB_LOOKUP_SPEC.md)

### 📺 Meta Endpoint Support (Oct 21, 2025)
**Enhancement**: Added `/meta/{type}/{id}.json` endpoint for detailed movie information.

**Benefits:**
- Users see rich movie details when clicking catalog entries
- No more "no information found about this" errors
- Shows channel, broadcast time, genre, and poster images
- Works with both IMDb IDs and custom musortv IDs

📖 **Documentation:** [Meta Endpoint Implementation](docs/META_ENDPOINT_IMPLEMENTATION.md)

### ✅ Midnight Boundary Fix (Oct 18, 2025)
Fixed a bug where late-night programs (00:00-06:00) were incorrectly dated when scraped in the evening. The time parser now uses a 12-hour threshold to detect midnight boundary crossings, ensuring programs after midnight appear in the correct time windows.

**Impact:** Users browsing at 23:00 will now correctly see movies scheduled for 01:00 as "upcoming" rather than "22 hours ago".

📖 **Documentation:** [MIDNIGHT_BOUNDARY_FIX.md](docs/MIDNIGHT_BOUNDARY_FIX.md) | [IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)

## 🏗️ Architecture Overview

### System Design: Catalog-Only Addon

```
┌─────────────────────────────────────────────────────────────────┐
│                      STREMIO CLIENT                              │
│                  (User's media center)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ User searches "matrix"
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               THIS ADDON (Catalog/Meta Only)                     │
│                                                                  │
│  GET /catalog/movie/hu-live.json?search=matrix                  │
│  Returns: [{id: "tt0133093", name: "Mátrix", ...}]              │
│                                                                  │
│  GET /meta/movie/tt0133093.json                                 │
│  Returns: {poster, description, genres, "RTL 20:00", ...}       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ IMDb ID: tt0133093
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│            STREAM PROVIDER ADDONS (User's choice)                │
│                                                                  │
│  Torrentio:   GET /stream/movie/tt0133093.json                  │
│               Returns: [1080p torrent, 720p torrent, ...]       │
│                                                                  │
│  MediaFusion: GET /stream/movie/tt0133093.json                  │
│               Returns: [Debrid links, ...]                      │
│                                                                  │
│  Comet:       GET /stream/movie/tt0133093.json                  │
│               Returns: [RD cached torrents, ...]                │
└─────────────────────────────────────────────────────────────────┘

User Experience:
1. User searches "matrix" → Finds "Mátrix on RTL at 20:00"
2. Clicks on movie → Sees full details (poster, description, channel)
3. Clicks "Watch" → Torrentio/other addons provide HD streams ✅
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER                              │
│                        (main.py)                                 │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ /manifest  │  │  /catalog    │  │    /meta     │           │
│  │   .json    │  │  /{type}/{id}│  │  /{type}/{id}│           │
│  └────────────┘  └──────┬───────┘  └──────┬───────┘           │
│                          │                  │                   │
│  ┌──────────────┐       │                  │                   │
│  │   /healthz   │       │                  │                   │
│  │  (status)    │       │                  │                   │
│  └──────────────┘       │                  │                   │
└─────────────────────────┼──────────────────┼────────────────────┘
                          │                  │
                          ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              CATALOG HANDLER          META HANDLER               │
│           (catalog_handler.py)     (meta_handler.py)             │
│                                                                  │
│  1. Parse params (time, search)    1. Parse movie ID            │
│  2. Check cache                    2. Fetch movie details       │
│  3. Filter by time window          3. Build rich metadata       │
│  4. IMDb lookup (TMDB API) ────┐   4. Return meta object        │
│  5. Transform to Stremio format│                                │
│  6. Apply search filter        │                                │
│                                 │                                │
│  ┌──────────────────┐           └───►┌──────────────────┐      │
│  │  CACHE LAYER     │                │  IMDb LOOKUP     │      │
│  │  (cache.py)      │                │  (imdb_lookup.py)│      │
│  │  TTL: 10 min     │                │  + TMDB API      │      │
│  └──────────────────┘                │  + Cache (7 days)│      │
│                                       └──────────────────┘      │
└──────────┬───────────────────────────────────────────────────────┘
           │ Cache miss
           │ fetch_live_movies()
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WEB SCRAPER                                 │
│                     (scraper.py)                                 │
│                                                                  │
│  Rate Limiting: 30s between scrapes                              │
│  Deduplication: One scrape at a time                             │
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │  PLAYWRIGHT BROWSER  │                                       │
│  │  (Headless Chromium) │                                       │
│  └──────────┬───────────┘                                       │
│             │ Navigate + Extract via CSS selectors              │
└─────────────┼───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MUSOR.TV WEBSITE                            │
│              (External Hungarian TV guide)                       │
│                                                                  │
│  Pages: /most/tvben, /filmek                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. **FastAPI Web Server** (`main.py`)
   - **Role:** HTTP/JSON endpoint provider
   - **Endpoints:**
     - `/manifest.json` - Addon identity and capabilities
     - `/catalog/{type}/{id}.json` - Movie catalog with time/search filters
     - `/meta/{type}/{id}.json` - Detailed movie metadata
     - `/healthz` - System health (scraper + IMDb status)
   - **Note:** NO `/stream` endpoint (catalog-only design)

#### 2. **Catalog Handler** (`catalog_handler.py`)
   - **Role:** Business logic orchestrator
   - **Responsibilities:**
     - Manage caching strategy (10-min TTL)
     - Filter by category (movies only, exclude series)
     - **IMDb lookup integration** (TMDB API)
     - Transform musor.tv data → Stremio format
     - Accent-insensitive search (Hungarian)
     - Success rate tracking (~75% IMDb match rate)

#### 3. **Meta Handler** (`meta_handler.py`)
   - **Role:** Detailed metadata provider
   - **Features:**
     - Rich Hungarian descriptions
     - Channel + broadcast time display
     - Poster images from musor.tv
     - Genre parsing and display
     - Works with IMDb IDs AND custom IDs

#### 4. **IMDb Lookup Service** (`imdb_lookup.py`)
   - **Role:** TMDB API integration
   - **Features:**
     - Title → IMDb ID matching
     - Rate limiting (40 req/s, configurable)
     - Hungarian → English fallback
     - Batch lookup optimization
     - Supports API keys + Bearer tokens (JWT)
     - Graceful degradation on API errors

#### 5. **IMDb Cache Layer** (`imdb_cache.py`)
   - **Role:** Reduce API calls
   - **Features:**
     - 7-day TTL for lookups
     - Caches successes AND failures
     - Normalized keys (handles accents)
     - ~80%+ cache hit rate
     - Statistics tracking

#### 6. **Web Scraper** (`scraper.py`)
   - **Role:** musor.tv data extraction
   - **Technology:** Playwright (headless Chromium)
   - **Features:**
     - Concurrent page scraping
     - Rate limiting (30s default)
     - In-flight deduplication
     - Cookie consent handling
     - Robust error recovery

#### 7. **Time Window Filter** (`time_window.py`)
   - **Role:** Time-based filtering
   - **Presets:**
     - `now`: Next 90 minutes
     - `next2h`: Next 2 hours
     - `tonight`: 18:00-23:59 today
   - **Smart Features:**
     - Midnight boundary detection
     - Timezone-aware (Europe/Budapest)

8. **Caching Layer** (`cache.py`)
   - TTL-based in-memory cache (default: 10 minutes)
   - Reduces scraping frequency and improves response times
   - Uses `cachetools.TTLCache` with max 64 entries

9. **Utilities & Models**
   - `models.py`: Pydantic data models (`LiveMovieRaw`, `StremioMetaPreview`, `StremioMeta`)
   - `utils.py`: Text processing (slugify, diacritics removal, film detection)
   - `manifest.py`: Stremio addon manifest configuration

### Data Flow (Catalog-Only Design)

1. **HTTP Request** arrives at FastAPI server with optional `search` and `time` parameters
2. **Catalog Handler** checks cache for the requested time preset
3. **Cache Miss** → Scraper fetches live data from musor.tv using Playwright
4. **Raw Data** is filtered by:
   - Category (must be a film, not a series)
   - Time window (must fall within selected time range)
5. **IMDb Lookup**:
   - Extract year from category when available
   - Query TMDB API with title and year
   - Cache result (success or failure) for 7 days
   - Use IMDb ID if found, fall back to custom ID
6. **Transformation** to Stremio format with metadata:
   - **Unique ID:** IMDb ID (e.g., `tt0133093`) ← **Stream addons recognize this!**
   - Fallback ID: `musortv:{channel}:{timestamp}:{title-slug}` (for unmatched movies)
   - Release info formatting: `"21:00 • RTL"`
   - Genre mapping (Hungarian → standardized)
   - Enhanced descriptions with channel and time info
7. **Caching** of transformed results with TTL (10 minutes)
8. **Search Filter** applied if provided (accent-insensitive)
9. **JSON Response** returned to Stremio client
10. **Stream Addons Take Over** - Torrentio/MediaFusion see IMDb IDs and provide streams ✅

## 📁 Project Structure

```
stremio-musor_tv/
├── src/                     # Main application code
│   ├── main.py              # FastAPI server entry point
│   ├── manifest.py          # Stremio addon manifest (catalog + meta only)
│   ├── catalog_handler.py   # Catalog business logic & orchestration
│   ├── meta_handler.py      # Meta endpoint handler
│   ├── scraper.py           # Playwright web scraper
│   ├── imdb_lookup.py       # TMDB API integration
│   ├── imdb_cache.py        # IMDb lookup caching
│   ├── time_window.py       # Time filtering logic
│   ├── cache.py             # TTL cache wrapper
│   ├── utils.py             # Text utilities (slugify, diacritics)
│   ├── models.py            # Pydantic data models
│   └── __init__.py          # Package marker
├── tests/                   # Unit tests
│   ├── test_imdb_lookup.py  # IMDb lookup tests
│   ├── test_scraper_refactor.py
│   ├── test_stream_support.py
│   └── test_midnight_boundary.py
├── docs/                    # Documentation
│   ├── IMDB_LOOKUP_SPEC.md  # IMDb feature specification
│   ├── META_ENDPOINT_IMPLEMENTATION.md  # Meta endpoint docs
│   ├── CATALOG_ONLY_DESIGN.md
│   ├── Midnight_Boundary_Fix_SUMMARY.md
│   └── ...
├── debug/                   # Debug scripts
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Docker Compose configuration
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

**IMDb Integration:** (**NEW**)
- aiohttp 3.9.5 (async HTTP client for TMDB API)
- TMDB API (for IMDb ID lookups)

**Testing:** (**NEW**)
- pytest 7.4.3 (unit testing framework)
- pytest-asyncio 0.21.1 (async test support)
- pytest-cov 4.1.0 (code coverage)

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
docker-compose logs -f | ccze -m ansi

# Stop
docker-compose down
```

The containerized addon will be available at `http://localhost:7000`

### Cloud Deployment

#### Render

For production deployment on Render.com:

Quick steps:
1. Push repository to GitHub/GitLab
2. Connect to Render Blueprint
3. Render auto-detects `render.yaml` and builds Docker image
4. Your addon will be at: `https://your-app.onrender.com`

**Note:** Make sure Render is configured to use **Docker runtime** (not Python) so Playwright browsers are properly installed.

**Configuration:**
- Render uses the `render.yaml` blueprint in the repository
- Automatically provisions a Docker-based web service
- Environment variables can be set in the Render dashboard
- Free tier available with 750 hours/month

#### Railway

For deployment on Railway.app:

Quick steps:
1. Push repository to GitHub
2. Create new project on [Railway](https://railway.app)
3. Connect your GitHub repository
4. Railway auto-detects `Dockerfile` and builds the image
5. Set environment variables in Railway dashboard:
   - `TZ=Europe/Budapest`
   - `PORT=7000` (or use Railway's auto-assigned port)
   - `CACHE_TTL_MIN=10`
   - `SCRAPE_RATE_MS=30000`
6. Your addon will be at: `https://your-app.railway.app`

**Configuration:**
- Railway automatically detects and builds Docker projects
- Uses `Dockerfile` in the repository root
- Free tier includes $5 of usage per month
- Easy environment variable management through dashboard
- Automatic HTTPS with custom domains supported

**Tips for Railway:**
- Let Railway assign the PORT (use `$PORT` environment variable)
- Monitor resource usage as Playwright requires ~2GB RAM
- Consider upgrading to paid plan for production use

## ⚙️ Configuration

### Environment Variables

All configuration is done via environment variables:

#### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | HTTP server port | `7000` | No |
| `LOG_LEVEL` | Logging verbosity (`debug`/`info`/`warning`/`error`) | `info` | No |
| `CACHE_TTL_MIN` | Cache TTL in minutes | `10` | No |
| `SCRAPE_RATE_MS` | Minimum milliseconds between scrapes | `30000` | No |
| `TZ` | Timezone (MUST be `Europe/Budapest` for correct times) | - | **Yes** |

#### IMDb Lookup Settings (**NEW**)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TMDB_API_KEY` | TMDB API key or Bearer token (JWT) for IMDb lookups | - | No* |
| `IMDB_LOOKUP_ENABLED` | Enable/disable IMDb ID lookup | `true` | No |
| `IMDB_CACHE_TTL_DAYS` | IMDb lookup cache TTL in days | `7` | No |
| `IMDB_RATE_LIMIT_PER_SEC` | Max TMDB API requests per second | `40` | No |

**\*Optional but highly recommended** for better stream provider integration.

**Getting a TMDB API Key (Free):**
1. Sign up at https://www.themoviedb.org/signup
2. Go to https://www.themoviedb.org/settings/api
3. Request an API key (instant approval for free tier)
4. Copy either:
   - **API Key (v3 auth)** - 32-character hex string (simpler)
   - **Bearer Token (JWT)** - Long `eyJ...` string (also supported)
5. Add to `.env` file: `TMDB_API_KEY=your_key_here`

**Benefits of IMDb Lookup:**
- Stream providers (Torrentio, etc.) can match movies by IMDb ID
- ~75% success rate for international movies
- Falls back to custom IDs when no match found
- Addon works perfectly fine without it

### Configuration in Docker

Edit `docker-compose.yml`:

```yaml
environment:
  - TZ=Europe/Budapest
  - PORT=7000
  - CACHE_TTL_MIN=15
  - SCRAPE_RATE_MS=45000
  - LOG_LEVEL=debug
  # IMDb lookup (optional)
  - TMDB_API_KEY=your_api_key_here
  - IMDB_LOOKUP_ENABLED=true
```

Or use a `.env` file (recommended for secrets):

```bash
# Copy example
cp .env.example .env

# Edit .env and add your TMDB_API_KEY
# Then docker-compose will automatically load it
```

### Configuration for Local Development

Create a `.env` file in the project root:

```bash
PORT=7000
LOG_LEVEL=info
CACHE_TTL_MIN=10
SCRAPE_RATE_MS=30000
TZ=Europe/Budapest

# IMDb lookup (optional but recommended)
TMDB_API_KEY=your_api_key_or_bearer_token_here
IMDB_LOOKUP_ENABLED=true
IMDB_CACHE_TTL_DAYS=7
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
  "description": "Discover movies on Hungarian TV • Works with your stream addons",
  "resources": ["catalog", "meta", "stream"],
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

# Search for specific movie
curl http://localhost:7000/catalog/movie/hu-live.json?search=matrix

# Tonight's movies
curl http://localhost:7000/catalog/movie/hu-live.json?time=tonight
```

**Response Format:**
```json
{
  "metas": [
    {
      "id": "tt0133093",
      "type": "movie",
      "name": "Mátrix",
      "release_info": "21:00 • RTL",
      "poster": "https://musor.tv/img/small/...",
      "genres": ["Sci-Fi", "Akció"],
      "description": "📺 RTL • 21:00 • amerikai sci-fi akciófilm,1999"
    }
  ]
}
```

**Note:** Movies with IMDb matches use IMDb IDs (e.g., `tt0133093`), others use custom format: `musortv:channel:timestamp:title-slug`

#### `GET /meta/movie/{id}.json` (**NEW**)
Returns detailed metadata for a specific movie.

**Parameters:**
- `{id}`: Movie ID (IMDb ID like `tt0133093` or custom `musortv:...` ID)

**Example:**
```bash
# Get details for The Matrix
curl http://localhost:7000/meta/movie/tt0133093.json

# Get details with custom ID
curl http://localhost:7000/meta/movie/musortv:rtl:1697654400:matrix.json
```

**Response:**
```json
{
  "meta": {
    "id": "tt0133093",
    "type": "movie",
    "name": "Mátrix",
    "poster": "https://musor.tv/img/small/...",
    "background": "https://musor.tv/img/small/...",
    "genres": ["Sci-Fi"],
    "description": "📺 **Csatorna:** RTL\n🕐 **Kezdés:** 2025.10.25 21:00\n🎬 **Műfaj:** amerikai sci-fi akciófilm,1999\n\n📡 **Élő adás a magyar TV-ből**\n\n💡 *Tipp: Használj stream kiegészítőt (pl. Torrentio) a megtekintéshez*",
    "releaseInfo": "📅 2025.10.25 • 21:00"
  }
}
```

#### `GET /stream/movie/{id}.json`
Returns empty streams array (catalog-only addon).

**Response:**
```json
{
  "streams": []
}
```

**Note:** This addon discovers content but doesn't provide streams. Install separate stream provider addons (Torrentio, etc.) for playback.

#### `GET /healthz`
Health check endpoint with system status.

**Response:**
```json
{
  "ok": true,
  "ts": 1761423802441,
  "scraper": {
    "healthy": true,
    "last_success_at": 22525.902,
    "total_errors": 0,
    "initialized": true
  },
  "imdb_lookup": {
    "enabled": true,
    "api_key_configured": true,
    "rate_limit": 40,
    "cache": {
      "size": 17,
      "maxsize": 1000,
      "ttl_days": 7
    }
  }
}
```

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
- Filter by time: "Now", "Next 2 Hours", "Tonight"
- Click on a movie to see detailed information
- **With IMDb integration:** Stream providers (Torrentio, etc.) will automatically offer torrents/streams

### How It Works with Stream Providers

**Without IMDb Lookup:**
```
1. You browse catalog → See "Mátrix on RTL at 21:00"
2. You click movie → ID: musortv:rtl:1697654400:matrix
3. Torrentio searches → ❌ Can't match (unknown ID format)
4. No streams available
```

**With IMDb Lookup (Recommended):**
```
1. You browse catalog → See "Mátrix on RTL at 21:00"
2. Behind the scenes → IMDb ID lookup: tt0133093
3. You click movie → ID: tt0133093
4. Torrentio recognizes → ✅ Provides torrents for The Matrix
5. You can watch! 🎬
```

**Success Rate:** ~75% of international movies get IMDb matches. Hungarian/regional films fall back to custom IDs (still visible, just no automatic stream matching).

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_imdb_lookup.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Coverage

- ✅ IMDb lookup functionality (`test_imdb_lookup.py`)
- ✅ Caching behavior (both catalog and IMDb)
- ✅ API error handling and fallbacks
- ✅ Hungarian title normalization
- ✅ Midnight boundary calculations
- ✅ Stream endpoint validation

## 🔗 Related Documentation

### Core Documentation
- [IMDb Lookup Specification](docs/IMDB_LOOKUP_SPEC.md) - Complete IMDb integration design
- [Meta Endpoint Implementation](docs/META_ENDPOINT_IMPLEMENTATION.md) - Detailed movie info endpoint
- [Catalog-Only Design](docs/CATALOG_ONLY_DESIGN.md) - Architecture philosophy
- [Midnight Boundary Fix](docs/Midnight_Boundary_Fix_SUMMARY.md) - Time calculation improvements

### Development Guides
- [Copilot Instructions](.github/instructions/copilot-instructions.md) - Development guidelines
- [Code Analysis Prompt](docs/CODE_ANALYSIS_PROMPT.md) - Analysis methodology
- [Scraper Refactor Summary](docs/SCRAPER_REFACTOR_SUMMARY.md) - Scraper architecture
- [Error Handling Improvements](docs/ERROR_HANDLING_IMPROVEMENTS.md) - Error handling patterns

## 🎯 Roadmap

### Completed ✅
- [x] Basic catalog functionality
- [x] Time window filtering (now/next2h/tonight)
- [x] Accent-insensitive search
- [x] Midnight boundary fix
- [x] Meta endpoint for detailed movie info
- [x] IMDb ID lookup integration
- [x] TMDB API Bearer token support
- [x] Comprehensive test coverage
- [x] Catalog-only architecture (stream addons handle playback)

### Planned Features
- [ ] Additional TMDB metadata (ratings, cast, plot)
- [ ] Year extraction from more category formats
- [ ] Manual IMDb ID overrides/corrections
- [ ] Performance optimization for batch lookups
- [ ] Series/TV show support
- [ ] Alternative time presets (weekend, week ahead)
- [ ] Multi-language support (English interface option)

## �📄 License

MIT License - Same as the original TypeScript version.
