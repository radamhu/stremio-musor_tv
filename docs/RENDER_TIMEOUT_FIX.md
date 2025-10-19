# Render Free Tier Timeout Fix

## Problem
When deploying to Render's free tier, the Playwright scraper was timing out with:
```
ERROR Failed to scrape https://musor.tv/most/tvben: 
Page.goto: Timeout 30000ms exceeded.
```

## Root Cause
Render's free tier has limited resources (512MB RAM, shared CPU). The default Playwright configuration and 30-second timeout were insufficient for:
1. Browser initialization in resource-constrained environment
2. Page loading with default Chrome flags
3. Network latency on free tier infrastructure

## Solution

### 1. Browser Launch Optimizations (`src/scraper.py`)

Added comprehensive Chromium flags to reduce resource usage:
- `--disable-dev-shm-usage`: Overcome limited /dev/shm space (critical for Docker)
- `--disable-gpu`: No GPU acceleration needed for headless mode
- `--disable-software-rasterizer`: Reduce CPU usage
- `--disable-background-networking`: Prevent unnecessary network requests
- Memory and rendering optimizations
- Increased browser launch timeout to 60 seconds

### 2. Page Navigation Improvements (`src/scraper.py`)

Implemented robust retry mechanism:
- **Increased timeout**: 30s → 90s for `page.goto()`
- **Exponential backoff retry**: 3 attempts with 2s, 4s, 8s delays
- **Per-page timeout**: Set default timeout to 90s for all operations
- **Faster wait strategy**: Use `domcontentloaded` instead of full `load` event

```python
# Before
await page.goto(url, wait_until="domcontentloaded", timeout=30000)

# After
page.set_default_timeout(90000)
for attempt in range(max_retries):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        break
    except Exception as e:
        # Exponential backoff retry logic
```

### 3. Environment Configuration

**Dockerfile:**
```dockerfile
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV NODE_OPTIONS="--max-old-space-size=512"
```

**render.yaml:**
```yaml
- key: PLAYWRIGHT_BROWSERS_PATH
  value: /ms-playwright
- key: NODE_OPTIONS
  value: --max-old-space-size=512
```

## Expected Results

1. **Browser launches successfully** even on slow startup
2. **Page navigation completes** within 90 seconds with retries
3. **Reduced memory footprint** from optimized Chrome flags
4. **Graceful degradation** with retry logic and detailed logging

## Monitoring

Check logs for:
- `Initializing Playwright browser...` → Should complete without timeout
- `Loading {url} (attempt X/3)` → Track retry attempts
- `Successfully loaded {url}` → Confirms successful navigation

## Performance Expectations on Render Free Tier

- **First scrape**: 30-60 seconds (cold start + browser init)
- **Subsequent scrapes**: 20-40 seconds (browser warm)
- **Timeout failures**: Should be rare with 3 retries × 90s

## Fallback Strategy

If timeouts persist, consider:
1. Increasing `SCRAPE_RATE_MS` to reduce scrape frequency
2. Implementing stale cache tolerance (return old data on failure)
3. Upgrading to Render paid tier (more CPU/RAM)

## Testing

Test locally with resource limits:
```bash
docker run --memory=512m --cpus=0.5 -p 7000:7000 stremio-musor-tv
```

## References

- Playwright on Render: https://render.com/docs/playwright
- Chrome flags for Docker: https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-puppeteer-in-docker
- Render free tier limits: https://render.com/docs/free
