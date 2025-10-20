# Quick Start: Adding Stream Support

## 🚀 5-Minute Setup

You've just upgraded to stream support! Here's how to get started:

### Step 1: Choose Your Stream Source

Pick one option:

**A. Use IPTV Service (Recommended)**
```bash
# Sign up for Hungarian IPTV provider
# Get M3U playlist or individual channel URLs
```

**B. Use Public IPTV Lists (Free, but less reliable)**
```bash
# Visit: https://github.com/iptv-org/iptv
# Search for Hungarian channels
# Copy .m3u8 URLs
```

**C. Use YouTube Live (If available)**
```bash
# Find channels streaming on YouTube
# Use YouTube video URLs
```

### Step 2: Configure Environment Variables

**Option A: Using .env file (Local)**
```bash
# Copy example file
cp .env.example .env

# Edit .env and add your stream URLs
nano .env
```

Add your streams:
```bash
STREAM_RTL=https://your-provider.com/rtl.m3u8
STREAM_TV2=https://your-provider.com/tv2.m3u8
STREAM_AMC_HD=https://your-provider.com/amc-hd.m3u8
```

**Option B: Docker Compose**

Edit `docker-compose.yml`:
```yaml
services:
  addon:
    environment:
      - STREAM_RTL=https://your-provider.com/rtl.m3u8
      - STREAM_TV2=https://your-provider.com/tv2.m3u8
```

**Option C: Render.com / Cloud Hosting**

1. Go to your service settings
2. Navigate to Environment Variables
3. Add variables:
   - Name: `STREAM_RTL`
   - Value: `https://your-provider.com/rtl.m3u8`
4. Repeat for each channel

### Step 3: Test Configuration

Run the test script:
```bash
python tests/test_stream_support.py
```

Expected output:
```
✅ PASS: musortv:amc-hd:1760943000:rendorsztori
✓ rtl: https://your-provider.com/rtl.m3u8...
✓ tv2: https://your-provider.com/tv2.m3u8...
✅ 2 channel(s) configured and ready to stream
```

### Step 4: Start the Addon

```bash
# Local development
python src/main.py

# Or Docker
docker-compose up

# Or Docker (detached)
docker-compose up -d
```

### Step 5: Test in Stremio

1. Open Stremio
2. Add your addon: `http://localhost:7000/manifest.json`
3. Browse catalog
4. Click a movie
5. You should see stream options with 🔴 icon!

## 📝 Important Notes

### What Gets Configured?

- ✅ **Channels you add** → Will have streams
- ❌ **Channels you skip** → Will appear in catalog but can't play

This is normal! You don't need to configure all channels.

### Minimum Setup

Just configure 2-3 popular channels to start:
```bash
STREAM_RTL=...
STREAM_TV2=...
STREAM_HBO=...
```

### Testing Stream URLs

Before adding to addon, test URLs work:
```bash
# Test with VLC
vlc "https://your-stream-url.m3u8"

# Or ffprobe
ffprobe "https://your-stream-url.m3u8"

# Or curl (check if accessible)
curl -I "https://your-stream-url.m3u8"
```

### Channel Name Matching

The addon converts channel names to slugs:

| Channel Name | Environment Variable | Slug |
|--------------|---------------------|------|
| RTL | `STREAM_RTL` | `rtl` |
| RTL Klub | `STREAM_RTL_KLUB` | `rtl-klub` |
| AMC HD | `STREAM_AMC_HD` | `amc-hd` |
| TV2 | `STREAM_TV2` | `tv2` |
| HBO | `STREAM_HBO` | `hbo` |

Check logs to see which channels are found during scraping.

## 🐛 Troubleshooting

### "No streams available"

**Cause:** Channel not configured or environment variable not set

**Fix:**
```bash
# Check if variable is set
echo $STREAM_RTL

# If empty, set it:
export STREAM_RTL="https://your-url.m3u8"

# Or add to .env file
```

### "Stream won't play"

**Possible causes:**
1. **Invalid URL** - Test in VLC first
2. **Geo-restricted** - Use VPN
3. **Format issue** - Stremio might not support the format
4. **CORS issue** - For web player

**Debug:**
```bash
# Check addon logs
docker logs stremio-addon

# Look for:
# "Found stream URL for channel..."
# or
# "No stream URL configured for channel..."
```

### "Only some channels work"

This is **expected behavior**! Only channels with `STREAM_*` variables will provide streams.

To fix: Add more `STREAM_*` environment variables.

## 📚 More Info

- **Full Setup Guide:** [docs/STREAM_CONFIGURATION.md](STREAM_CONFIGURATION.md)
- **Implementation Details:** [docs/STREAM_SUPPORT_SUMMARY.md](STREAM_SUPPORT_SUMMARY.md)
- **Main README:** [README.md](../README.md)

## 🔒 Security Reminder

- ✅ Use environment variables
- ✅ Add `.env` to `.gitignore` (already done)
- ❌ Never commit stream URLs to git
- ❌ Don't share stream URLs publicly

## 💡 Example Configuration

Here's a working example to get you started:

```bash
# .env file
PORT=7000
LOG_LEVEL=info
CACHE_TTL_MIN=10
SCRAPE_RATE_MS=30000

# Add your actual stream URLs here
STREAM_RTL=https://your-iptv-provider.com/rtl/index.m3u8
STREAM_TV2=https://your-iptv-provider.com/tv2/index.m3u8
STREAM_HBO=https://your-iptv-provider.com/hbo/index.m3u8
STREAM_AMC_HD=https://your-iptv-provider.com/amc-hd/index.m3u8
```

That's it! 🎉

Your addon now provides real streaming capabilities for Hungarian TV channels!
