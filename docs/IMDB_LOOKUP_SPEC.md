# IMDb Lookup Implementation Specification

## 📋 Overview

This document specifies the implementation of IMDb ID lookup functionality to enable better integration between this catalog addon and stream provider addons (Torrentio, etc.) in the Stremio ecosystem.

## 🎯 Objective

**Goal:** Enable users to find torrents/files for movies shown on Hungarian TV by bridging the gap between Hungarian TV listings and international movie databases.

**Current Problem:**
- Catalog entries use custom IDs: `musortv:rtl:1697654400:matrix`
- Stream addons expect IMDb IDs: `tt0133093`
- Title variations: "Mátrix" (Hungarian) vs "The Matrix" (English)
- **Result:** Stream addons can't match movies → users see "No streams available"

**Proposed Solution:**
- Look up IMDb IDs for Hungarian TV movie titles
- Use IMDb ID as the catalog entry ID when found
- Fall back to custom ID when IMDb lookup fails
- Stream addons can now match and provide torrents/files

## 🏗️ Architecture Changes

### Current Flow
```
musor.tv scraping → LiveMovieRaw → StremioMetaPreview
                                    id: musortv:rtl:...
                                    ↓
                                    Stremio Client
                                    ↓
                                    Stream Addons → ❌ No match
```

### Proposed Flow
```
musor.tv scraping → LiveMovieRaw → IMDb Lookup → StremioMetaPreview
                                    (TMDB API)     id: tt0133093 or
                                                   id: musortv:rtl:...
                                    ↓
                                    Stremio Client
                                    ↓
                                    Stream Addons → ✅ Match found
```

## 🔌 External API Integration

### TMDB (The Movie Database) API

**Why TMDB?**
- ✅ Free API key (no credit card required)
- ✅ Good Hungarian title coverage
- ✅ Returns IMDb IDs directly
- ✅ 50 requests/second rate limit (generous)
- ✅ Well-documented Python client libraries
- ❌ Requires API key management

**Alternative: OMDB**
- ✅ Simpler API
- ❌ Limited free tier (1,000 requests/day)
- ❌ Less Hungarian title coverage
- ✅ No rate limiting

**Decision:** Use TMDB as primary option with OMDB as fallback.

### API Endpoint
```
GET https://api.themoviedb.org/3/search/movie
Parameters:
  - api_key: {YOUR_KEY}
  - query: {movie_title}
  - year: {release_year} (optional but recommended)
  - language: hu-HU (try Hungarian first, fall back to en-US)
```

**Response Example:**
```json
{
  "results": [
    {
      "id": 603,
      "title": "The Matrix",
      "original_title": "The Matrix",
      "release_date": "1999-03-30",
      "imdb_id": "tt0133093"  // Note: Need to fetch from movie details endpoint
    }
  ]
}
```

**Note:** IMDb ID requires second API call:
```
GET https://api.themoviedb.org/3/movie/{movie_id}/external_ids
Returns: { "imdb_id": "tt0133093" }
```

## 📦 New Components

### 1. IMDb Lookup Service (`src/imdb_lookup.py`)

**Responsibilities:**
- Query TMDB API with movie title and optional year
- Handle API key management via environment variables
- Implement request rate limiting (respect TMDB's 50 req/s limit)
- Cache lookup results (reduce API calls)
- Handle errors gracefully (network issues, API limits)
- Return `Optional[str]` (IMDb ID or None)

**Function Signatures:**
```python
async def lookup_imdb_id(
    title: str,
    year: Optional[int] = None,
    language: str = "hu-HU"
) -> Optional[str]:
    """
    Look up IMDb ID for a movie title.
    
    Args:
        title: Movie title (can be Hungarian or English)
        year: Release year for better matching accuracy
        language: TMDB language code (default: hu-HU)
    
    Returns:
        IMDb ID (e.g., "tt0133093") or None if not found
    """
    pass

async def batch_lookup_imdb_ids(
    movies: List[Tuple[str, Optional[int]]]
) -> Dict[str, Optional[str]]:
    """
    Batch lookup multiple movies (for optimization).
    
    Args:
        movies: List of (title, year) tuples
    
    Returns:
        Dict mapping title to IMDb ID (or None)
    """
    pass
```

### 2. IMDb Cache Layer (`src/imdb_cache.py`)

**Purpose:** Reduce API calls by caching IMDb lookup results

**Cache Strategy:**
- **Key:** Normalized title (lowercase, no diacritics) + year
- **Value:** IMDb ID or `None` (to cache failed lookups)
- **TTL:** 7 days (IMDb IDs don't change)
- **Size:** 1000 entries (estimated 100KB memory)

**Implementation:**
```python
from cachetools import TTLCache
import hashlib

# TTL: 7 days in seconds
IMDB_CACHE_TTL = 7 * 24 * 60 * 60

# Max 1000 entries
imdb_cache: TTLCache = TTLCache(maxsize=1000, ttl=IMDB_CACHE_TTL)

def _cache_key(title: str, year: Optional[int]) -> str:
    """Generate cache key from title and year."""
    normalized = remove_diacritics(title.lower().strip())
    year_str = str(year) if year else ""
    return hashlib.md5(f"{normalized}:{year_str}".encode()).hexdigest()
```

### 3. Enhanced Catalog Handler (`src/catalog_handler.py`)

**Changes:**
- Integrate IMDb lookup into catalog generation
- Use IMDb ID as meta ID when available
- Fall back to custom musortv ID when lookup fails
- Track lookup success rate for monitoring

**Modified Logic:**
```python
async def catalog_handler(type_: str, id_: str, extra: Optional[Dict[str, Any]] = None):
    # ...existing code to fetch and filter movies...
    
    metas = []
    successful_lookups = 0
    
    for r in filtered:
        # Try IMDb lookup
        imdb_id = None
        if TMDB_API_KEY:  # Only if configured
            imdb_id = await lookup_imdb_id(r.title, r.year)
            if imdb_id:
                successful_lookups += 1
        
        # Choose ID strategy
        if imdb_id:
            meta_id = imdb_id
            logger.debug(f"Using IMDb ID {imdb_id} for '{r.title}'")
        else:
            # Fall back to custom ID
            meta_id = f"musortv:{slugify(r.channel)}:{timestamp}:{slugify(r.title)}"
            logger.debug(f"No IMDb ID found for '{r.title}', using custom ID")
        
        metas.append(StremioMetaPreview(
            id=meta_id,
            type="movie",
            name=r.title,
            # ...rest of fields...
        ))
    
    logger.info(f"IMDb lookup success rate: {successful_lookups}/{len(filtered)}")
    return {"metas": metas}
```

## 📊 Expected Success Rate

### Optimistic Estimate
- **80-90%** for popular movies (Hollywood, major releases)
- **60-70%** for European movies
- **30-50%** for Hungarian/regional movies
- **10-20%** for very old or obscure titles

### Factors Affecting Success
- ✅ Title language (English > Hungarian)
- ✅ Release year provided (improves matching)
- ✅ Movie popularity (TMDB coverage)
- ❌ Title translation variations ("Die Hard" vs "Drágán add az életed")
- ❌ Regional/TV movies with limited international distribution

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `TMDB_API_KEY` | TMDB API key (get from themoviedb.org) | **Yes** | `a1b2c3d4e5f6...` |
| `IMDB_LOOKUP_ENABLED` | Enable/disable IMDb lookup | No | `true` (default) |
| `IMDB_CACHE_TTL_DAYS` | Cache TTL in days | No | `7` (default) |
| `IMDB_RATE_LIMIT_PER_SEC` | Max TMDB requests per second | No | `40` (default, under 50 limit) |

### docker-compose.yml
```yaml
environment:
  - TMDB_API_KEY=${TMDB_API_KEY}  # Set in .env file
  - IMDB_LOOKUP_ENABLED=true
  - IMDB_CACHE_TTL_DAYS=7
```

### .env.example
```bash
# TMDB API Configuration
# Get your free API key from: https://www.themoviedb.org/settings/api
TMDB_API_KEY=your_api_key_here

# Optional: IMDb Lookup Settings
IMDB_LOOKUP_ENABLED=true
IMDB_CACHE_TTL_DAYS=7
IMDB_RATE_LIMIT_PER_SEC=40
```

## 🧪 Testing Strategy

### Unit Tests (`tests/test_imdb_lookup.py`)

```python
@pytest.mark.asyncio
async def test_lookup_popular_movie():
    """Test IMDb lookup for well-known movie."""
    imdb_id = await lookup_imdb_id("The Matrix", 1999)
    assert imdb_id == "tt0133093"

@pytest.mark.asyncio
async def test_lookup_hungarian_title():
    """Test lookup with Hungarian title."""
    imdb_id = await lookup_imdb_id("Mátrix", 1999)
    assert imdb_id == "tt0133093"

@pytest.mark.asyncio
async def test_lookup_not_found():
    """Test handling of unknown movie."""
    imdb_id = await lookup_imdb_id("Nonexistent Movie XYZ 2025", 2025)
    assert imdb_id is None

@pytest.mark.asyncio
async def test_cache_hit():
    """Test that repeated lookups use cache."""
    # First call - API request
    imdb_id1 = await lookup_imdb_id("The Matrix", 1999)
    
    # Second call - should hit cache
    with patch('aiohttp.ClientSession.get') as mock_get:
        imdb_id2 = await lookup_imdb_id("The Matrix", 1999)
        assert imdb_id1 == imdb_id2
        mock_get.assert_not_called()  # No API call
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_catalog_with_imdb_lookup(test_client):
    """Test catalog returns IMDb IDs when available."""
    response = test_client.get("/catalog/movie/hu-live.json")
    data = response.json()
    
    # Check that some metas have IMDb IDs
    imdb_ids = [m["id"] for m in data["metas"] if m["id"].startswith("tt")]
    assert len(imdb_ids) > 0, "Expected some IMDb IDs in catalog"
```

## 📈 Monitoring & Metrics

### Logging

Add structured logging for IMDb lookups:

```python
logger.info(
    "IMDb lookup completed",
    extra={
        "title": title,
        "year": year,
        "imdb_id": imdb_id,
        "cache_hit": cache_hit,
        "api_call_ms": duration_ms,
    }
)
```

### Metrics to Track

1. **Lookup Success Rate**
   - % of movies with IMDb ID found
   - Track by time window (now vs tonight)
   - Track by channel (RTL vs HBO)

2. **API Performance**
   - Average API response time
   - Cache hit rate
   - API errors (rate limits, network issues)

3. **User Impact**
   - Catalog response time (before/after IMDb lookup)
   - Stream availability (with vs without IMDb IDs)

## ⚠️ Error Handling

### API Failures

```python
try:
    imdb_id = await lookup_imdb_id(title, year)
except TMDBRateLimitError:
    logger.warning("TMDB rate limit reached, falling back to custom IDs")
    imdb_id = None
except TMDBAPIError as e:
    logger.error(f"TMDB API error: {e}, falling back to custom IDs")
    imdb_id = None
except Exception as e:
    logger.exception(f"Unexpected error during IMDb lookup: {e}")
    imdb_id = None
```

**Graceful Degradation:**
- If IMDb lookup fails, use custom musortv IDs
- Addon still works without TMDB API key
- Cache failed lookups to avoid repeated API calls

## 🚀 Implementation Phases

### Phase 1: Core Functionality (Week 1)
- [ ] Create `imdb_lookup.py` with TMDB integration
- [ ] Implement basic caching in `imdb_cache.py`
- [ ] Add unit tests for lookup function
- [ ] Update `catalog_handler.py` to use IMDb IDs

### Phase 2: Optimization (Week 2)
- [ ] Implement batch lookup for catalog generation
- [ ] Add rate limiting to respect TMDB quotas
- [ ] Optimize cache key generation
- [ ] Add integration tests

### Phase 3: Monitoring (Week 3)
- [ ] Add structured logging
- [ ] Track success rate metrics
- [ ] Create performance benchmarks
- [ ] Update documentation

### Phase 4: Production (Week 4)
- [ ] Deploy to Railway/Render
- [ ] Monitor real-world success rates
- [ ] Tune cache TTL based on usage
- [ ] Gather user feedback

## 🎯 Success Criteria

1. **Functional:**
   - ✅ IMDb lookup works for 70%+ of movies
   - ✅ Addon works without API key (graceful degradation)
   - ✅ Catalog response time < 500ms (with caching)

2. **Technical:**
   - ✅ All unit tests pass
   - ✅ Cache hit rate > 80% for repeated requests
   - ✅ No API rate limit violations

3. **User Experience:**
   - ✅ Users report more stream options available
   - ✅ No increase in "No streams available" errors
   - ✅ Catalog still works if TMDB is down

## 📚 Documentation Updates

### README.md Changes

Add section:
```markdown
## 🎬 IMDb Integration

This addon now supports IMDb ID lookup to improve compatibility with stream provider addons like Torrentio.

**Setup:**
1. Get free TMDB API key from https://www.themoviedb.org/settings/api
2. Set environment variable: `TMDB_API_KEY=your_key_here`
3. Restart addon

**Benefits:**
- Better matching with Torrentio and other stream addons
- More stream options available when clicking movies
- Works even if lookup fails (falls back to custom IDs)
```

### New Documentation

Create:
- `docs/IMDB_LOOKUP_GUIDE.md` - User guide for setup
- `docs/TMDB_API_SETUP.md` - How to get TMDB API key
- `docs/TROUBLESHOOTING_IMDB.md` - Common issues and solutions

## 🔄 Alternative Approaches Considered

### 1. Local Movie Database (Rejected)
**Idea:** Download IMDb/TMDB database locally
- ❌ Large database size (>1GB)
- ❌ Requires frequent updates
- ❌ Complex deployment

### 2. Wikipedia Scraping (Rejected)
**Idea:** Scrape Hungarian Wikipedia for IMDb IDs
- ❌ Unreliable structure
- ❌ Limited coverage
- ❌ Legal gray area

### 3. User-Provided Mappings (Future Enhancement)
**Idea:** Let users submit title → IMDb ID mappings
- ✅ Community-driven improvements
- ✅ Better Hungarian title coverage
- ⚠️ Requires moderation
- 💡 Could be Phase 5

## 📝 Notes

- IMDb lookup is **optional** - addon works without it
- Focus on **graceful degradation** - never break catalog
- Monitor **API costs** if switching to paid TMDB tier
- Consider **regional movies** may have low success rates
- User feedback will guide **optimization priorities**

## 🔗 References

- [TMDB API Documentation](https://developers.themoviedb.org/3)
- [Stremio Addon SDK](https://github.com/Stremio/stremio-addon-sdk)
- [Original Catalog Design Doc](CATALOG_ONLY_DESIGN.md)

---

**Last Updated:** October 21, 2025
**Status:** Draft Specification
**Next Step:** Review and approve before implementation