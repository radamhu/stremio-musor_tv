# Deploying to Render

This guide explains how to deploy the Stremio HU Live Movies addon to Render.

## Prerequisites

- A [Render](https://render.com) account (free tier works)
- This repository pushed to GitHub/GitLab

## Deployment Methods

### Method 1: Automatic Deployment with render.yaml (Recommended)

1. **Connect Repository to Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub/GitLab repository
   - Render will automatically detect `render.yaml`

2. **Deploy**
   - Click "Apply" to create the service
   - Render will build the Docker image with Playwright/Chromium
   - Wait 5-10 minutes for initial build

3. **Get Your Addon URL**
   - Once deployed, you'll get a URL like: `https://stremio-musor-tv.onrender.com`
   - Your manifest will be at: `https://stremio-musor-tv.onrender.com/manifest.json`

### Method 2: Manual Web Service Setup

If you prefer manual setup:

1. **Create New Web Service**
   - Go to Render Dashboard → "New +" → "Web Service"
   - Connect your repository

2. **Configure Service**
   - **Name:** `stremio-musor-tv`
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Context:** `.`

3. **Environment Variables**
   Add these in the "Environment" section:
   ```
   PORT=7000
   TZ=Europe/Budapest
   LOG_LEVEL=info
   CACHE_TTL_MIN=10
   SCRAPE_RATE_MS=30000
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete

## Troubleshooting

### Issue: Internal Server Error on /catalog endpoint

**Symptom:** 
```bash
$ curl https://your-app.onrender.com/catalog/movie/hu-live.json
Internal Server Error
```

**Solution:** Check health endpoint for scraper status:
```bash
$ curl https://your-app.onrender.com/healthz
```

If you see `"last_error": "Executable doesn't exist"`, it means Playwright is not installed properly. Make sure you're using **Docker runtime** in render.yaml, not Python runtime.

### Issue: Build Times Out

**Symptom:** Build fails after 15 minutes

**Solution:** 
- Render free tier has a 15-minute build timeout
- Docker layer caching helps (already configured in Dockerfile)
- If still timing out, consider upgrading to paid tier or using a lighter scraping approach

### Issue: Out of Memory

**Symptom:** App crashes or fails to start

**Solution:**
- Chromium uses ~200-400MB RAM
- Free tier has 512MB RAM limit
- Reduce `CACHE_TTL_MIN` to lower memory usage
- Increase `SCRAPE_RATE_MS` to reduce scraping frequency

### Issue: Cold Start Takes Long Time

**Symptom:** First request after inactivity is very slow

**Solution:**
- Render free tier spins down after 15 minutes of inactivity
- Cold start includes browser initialization (~10-15 seconds)
- Consider upgrading to paid tier to avoid spin-down
- Or use a uptime monitoring service to ping your addon periodically

## Monitoring

### Check Service Health
```bash
curl https://your-app.onrender.com/healthz
```

Response:
```json
{
  "ok": true,
  "ts": 1697654400000,
  "scraper": {
    "healthy": true,
    "last_success_at": 1697654390.5,
    "last_error_at": null,
    "last_error": null,
    "total_errors": 0,
    "consecutive_errors": 0,
    "initialized": true
  }
}
```

### View Logs
- Go to Render Dashboard → Your Service → "Logs" tab
- Look for scraping activity and errors
- Rich formatted logs show colorized output

## Performance Tips

1. **Enable Caching**
   - Default cache TTL is 10 minutes
   - Increase `CACHE_TTL_MIN` for better performance but staler data

2. **Rate Limiting**
   - Default scrape rate is 30 seconds
   - Increase `SCRAPE_RATE_MS` to reduce server load

3. **Resource Limits**
   - Free tier: 512MB RAM, 0.1 CPU
   - Paid tier: More resources, no spin-down

## Updating the Addon

1. Push changes to your repository
2. Render auto-deploys on push (if auto-deploy enabled)
3. Or manually trigger deploy from Render Dashboard

## Cost

- **Free Tier:** 750 hours/month (enough for one service)
- **Paid Tier:** Starts at $7/month (no spin-down, more resources)

## Next Steps

After deployment:
1. Test manifest: `curl https://your-app.onrender.com/manifest.json`
2. Test catalog: `curl https://your-app.onrender.com/catalog/movie/hu-live.json`
3. Install in Stremio: Use `https://your-app.onrender.com/manifest.json`

## Support

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)
- [Playwright Documentation](https://playwright.dev/python/)
