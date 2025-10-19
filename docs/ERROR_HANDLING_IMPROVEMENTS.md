# Error Handling Improvements

**Date**: October 18, 2025  
**Status**: ✅ **IMPLEMENTED**  
**Issue**: Error messages disappear in production, making debugging difficult

---

## Problem Summary

When scraping failed in production (Docker), error messages were either:
1. Logged at DEBUG level (invisible with default LOG_LEVEL=info)
2. Silently swallowed by bare `except:` clauses
3. Not surfaced in API responses (empty catalogs look the same as errors)

This made it extremely difficult to debug "why is my catalog empty?" issues in production.

---

## Implemented Solutions

### 1. ✅ Upgraded Parse Failure Logging

**File**: `src/scraper.py` (line ~171)

**Before**:
```python
except Exception as e:
    logger.debug(f"Failed to parse show event {i}: {e}")
    continue
```

**After**:
```python
except Exception as e:
    logger.warning(f"Failed to parse show event {i} on {url}: {e}")
    continue
```

**Impact**: Parse failures are now visible in production logs with default `LOG_LEVEL=info`

---

### 2. ✅ Fixed Bare Except Clause

**File**: `src/scraper.py` (line ~237)

**Before**:
```python
except:
    pass
```

**After**:
```python
except Exception as e:
    logger.debug(f"Could not click element '{selector}': {e}")
    pass
```

**Impact**: Cookie dialog failures are now logged (at DEBUG level since these are non-critical)

---

### 3. ✅ Added Scraper Status Tracking

**File**: `src/scraper.py`

**Added Instance Variables**:
```python
# Status tracking for health monitoring
self._last_success_at: Optional[float] = None
self._last_error_at: Optional[float] = None
self._last_error: Optional[str] = None
self._total_error_count: int = 0
self._consecutive_error_count: int = 0
```

**Updated `fetch_live_movies()` Method**:
- Tracks successful fetches with timestamp
- Tracks errors with timestamp and message
- Maintains error counters (total + consecutive)
- Resets consecutive errors on success

**Impact**: Scraper now maintains state about its health and error history

---

### 4. ✅ Added Status Getter Methods

**File**: `src/scraper.py`

**Added Method to MusorTvScraper Class**:
```python
def get_status(self) -> Dict[str, Any]:
    """Get current scraper status for health monitoring."""
    return {
        "healthy": self._consecutive_error_count < 3,  # Unhealthy after 3 consecutive failures
        "last_success_at": self._last_success_at,
        "last_error_at": self._last_error_at,
        "last_error": self._last_error,
        "total_errors": self._total_error_count,
        "consecutive_errors": self._consecutive_error_count,
    }
```

**Added Module-Level Function**:
```python
async def get_scraper_status() -> Dict[str, Any]:
    """Get the current status of the scraper instance."""
    # Returns status or "not initialized" message
```

**Impact**: Status can now be queried programmatically for health checks

---

### 5. ✅ Enhanced Health Endpoint

**File**: `src/main.py`

**Before**:
```python
@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    import time
    return {"ok": True, "ts": int(time.time() * 1000)}
```

**After**:
```python
@app.get("/healthz")
async def health_check():
    """Health check endpoint with scraper status."""
    import time
    from scraper import get_scraper_status
    
    scraper_status = await get_scraper_status()
    
    return {
        "ok": scraper_status.get("healthy", False),
        "ts": int(time.time() * 1000),
        "scraper": scraper_status
    }
```

**Impact**: Health endpoint now returns detailed scraper status

---

## Usage Examples

### Checking Health in Production

```bash
# Quick health check
curl http://localhost:7000/healthz

# Example response when healthy:
{
  "ok": true,
  "ts": 1729274400000,
  "scraper": {
    "healthy": true,
    "initialized": true,
    "last_success_at": 1729274395.5,
    "last_error_at": null,
    "last_error": null,
    "total_errors": 0,
    "consecutive_errors": 0
  }
}

# Example response when unhealthy (3+ consecutive errors):
{
  "ok": false,
  "ts": 1729274400000,
  "scraper": {
    "healthy": false,
    "initialized": true,
    "last_success_at": 1729274000.0,
    "last_error_at": 1729274395.5,
    "last_error": "Failed to scrape https://musor.tv/most/tvben: ...",
    "total_errors": 5,
    "consecutive_errors": 3
  }
}
```

### Monitoring Logs

```bash
# View logs in Docker
docker logs addon-python

# You'll now see:
# - WARNING level parse failures (visible with LOG_LEVEL=info)
# - Detailed error information with stack traces
# - Success/failure timestamps in health endpoint
```

### Setting Up Alerts

You can now monitor the `/healthz` endpoint and alert on:
- `"ok": false` - Scraper is unhealthy (3+ consecutive errors)
- `"initialized": false` - Scraper never started
- High `total_errors` count
- Recent `last_error_at` timestamp

---

## Benefits

### For Debugging
✅ **Parse failures visible in production** - No need to change LOG_LEVEL to debug  
✅ **Error context preserved** - Includes URL and event index in warnings  
✅ **Historical error tracking** - See total errors and patterns  

### For Monitoring
✅ **Health endpoint reflects reality** - Returns `false` when scraper is failing  
✅ **Programmatic status checks** - Can integrate with monitoring systems  
✅ **Error message visibility** - Last error message included in health response  

### For Operations
✅ **No code changes needed to debug** - Just check `/healthz` or logs  
✅ **Clear failure signals** - Consecutive errors indicate persistent issues  
✅ **Better Docker logging** - All errors visible in `docker logs`  

---

## Testing Checklist

- [ ] Start server: `python src/main.py`
- [ ] Check health when scraper hasn't run: `curl http://localhost:7000/healthz`
- [ ] Trigger a scrape by accessing catalog: `curl http://localhost:7000/catalog/movie/hu-live.json`
- [ ] Check health after successful scrape: `curl http://localhost:7000/healthz`
- [ ] Verify logs show INFO and WARNING level messages
- [ ] (Optional) Simulate failure by breaking musor.tv URL and verify health returns `"ok": false`

---

## Docker Deployment

No changes needed to existing Docker setup. The improvements work automatically with:
- Default `LOG_LEVEL=info` (parse warnings now visible)
- Docker log collection (all errors captured)
- Existing health check configurations

---

## Future Enhancements

Possible additional improvements:
1. **Prometheus metrics** - Export error counts and health status
2. **Structured logging** - JSON logs for better parsing
3. **Error aggregation** - Group similar errors together
4. **Auto-recovery** - Attempt browser restart after consecutive failures
5. **Catalog error metadata** - Return error hints in empty catalog responses

---

## Related Files

- `src/scraper.py` - Main scraper with error tracking
- `src/main.py` - Health endpoint
- `docker-compose.yml` - LOG_LEVEL configuration
- `Dockerfile` - Container setup with logging

---

## Rollback Plan

If issues arise, revert to previous behavior by:
1. Restoring `src/scraper.py` and `src/main.py` from git
2. No database or state changes required
3. No breaking API changes (health endpoint is backward compatible)
