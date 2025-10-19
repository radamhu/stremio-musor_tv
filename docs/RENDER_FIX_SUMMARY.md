# Render Deployment Fix - Summary

## Problem Identified

Your Stremio addon was deployed to Render but returning "Internal Server Error" when accessing the catalog endpoint:

```bash
$ curl https://stremio-musor-tv.onrender.com/catalog/movie/hu-live.json
Internal Server Error
```

### Root Cause

Checking the `/healthz` endpoint revealed the issue:

```json
{
  "last_error": "Executable doesn't exist at /opt/render/.cache/ms-playwright/chromium-1134/chrome-linux/chrome
  Looks like Playwright was just installed or updated.
  Please run the following command to download new browsers: playwright install"
}
```

**The scraper is failing because Playwright browsers (Chromium) are not installed in the Render environment.**

This happens when:
- Render is using **Python runtime** instead of **Docker runtime**
- In Python runtime, `playwright install` and `playwright install-deps` don't have the necessary system permissions
- The Dockerfile properly installs Chromium, but only works when using Docker deployment

## Solution Implemented

### 1. Added Error Handling (Prevents 500 errors)

**File: `src/main.py`**
- Wrapped catalog endpoint in try-catch
- Returns empty catalog `{"metas": []}` with 200 status on scraper failure
- Logs errors for debugging

**File: `src/catalog_handler.py`**
- Added try-catch around scraper fetch
- Returns empty list if scraping fails
- Prevents crash on Playwright errors

### 2. Created Render Configuration

**File: `render.yaml`** (NEW)
- Configures Render to use **Docker runtime** (critical!)
- Sets proper Dockerfile path
- Defines environment variables
- This ensures Playwright browsers are installed via Docker build

### 3. Created Deployment Guide

**File: `docs/RENDER_DEPLOYMENT.md`** (NEW)
- Complete step-by-step deployment instructions
- Troubleshooting guide for common issues
- Performance tips and monitoring advice

### 4. Updated README

**File: `README.md`**
- Added "Cloud Deployment (Render)" section
- Links to detailed deployment guide
- Emphasizes using Docker runtime

## Next Steps - Action Required

### To Fix Your Deployed Addon:

1. **Commit and Push Changes**
   ```bash
   cd /home/ferko/Documents/stremio-musor_tv
   git add .
   git commit -m "Add Render deployment config with Docker runtime and error handling"
   git push
   ```

2. **Update Render Service Configuration**
   
   **Option A: Use render.yaml (Recommended)**
   - Go to Render Dashboard
   - Delete current service
   - Create new "Blueprint" service
   - Connect your repository
   - Render will auto-detect `render.yaml` and use Docker
   
   **Option B: Update Existing Service Manually**
   - Go to your service in Render Dashboard
   - Click "Settings"
   - Under "Build & Deploy":
     - Change **Runtime** to `Docker`
     - Set **Dockerfile Path** to `./Dockerfile`
     - Set **Docker Context** to `.`
   - Click "Save Changes"
   - Trigger manual deploy

3. **Wait for Build**
   - Initial Docker build will take 5-10 minutes
   - Watch the build logs for "playwright install chromium"
   - Should see "Browser initialized successfully" in runtime logs

4. **Test the Fixed Deployment**
   ```bash
   # Test manifest
   curl https://stremio-musor-tv.onrender.com/manifest.json
   
   # Test catalog (should now work)
   curl https://stremio-musor-tv.onrender.com/catalog/movie/hu-live.json
   
   # Check health (should show healthy scraper)
   curl https://stremio-musor-tv.onrender.com/healthz
   ```

5. **Install in Stremio**
   - Open Stremio
   - Go to Addons → "Install from URL"
   - Enter: `https://stremio-musor-tv.onrender.com/manifest.json`
   - Navigate to Movies → Find "Live on TV (HU)" catalog

## Why This Fixes the Issue

| Before | After |
|--------|-------|
| Python runtime | **Docker runtime** |
| Playwright browsers not installed | ✅ Browsers installed via Dockerfile |
| Crashes on scraper error | ✅ Graceful error handling |
| No deployment docs | ✅ Complete deployment guide |
| 500 Internal Server Error | ✅ Returns empty catalog with helpful logs |

## Files Changed

- ✅ `src/main.py` - Added error handling
- ✅ `src/catalog_handler.py` - Added scraper error handling  
- ✅ `render.yaml` - NEW: Render Docker configuration
- ✅ `docs/RENDER_DEPLOYMENT.md` - NEW: Deployment guide
- ✅ `README.md` - Added Render deployment section

## Verification Checklist

After redeploying, verify:

- [ ] Manifest endpoint works: `/manifest.json` returns JSON
- [ ] Catalog endpoint works: `/catalog/movie/hu-live.json` returns movies
- [ ] Health check shows healthy scraper: `/healthz` shows `"healthy": true`
- [ ] Stremio can install the addon
- [ ] "Live on TV (HU)" catalog appears in Stremio Movies section
- [ ] Movies are listed with correct times and channels

## Troubleshooting

If still having issues after redeploy:

1. **Check Render Logs**
   - Go to service → "Logs" tab
   - Look for "Browser initialized successfully"
   - Check for Playwright errors

2. **Verify Docker Runtime**
   - Service settings should show "Runtime: Docker"
   - Build logs should show Docker layer caching

3. **Memory Issues**
   - Free tier has 512MB RAM
   - If OOM errors, increase `SCRAPE_RATE_MS` to reduce load

4. **Cold Start Delays**
   - First request after 15min inactivity will be slow
   - Consider paid tier to avoid spin-down

## References

- [Render Deployment Guide](docs/RENDER_DEPLOYMENT.md)
- [Dockerfile](/Dockerfile)
- [render.yaml](/render.yaml)
