# Stream Configuration Guide

## Overview

As of version 1.0.0, this addon now provides **actual stream URLs** for Hungarian TV channels in addition to the catalog/discovery features. This means users can watch content directly through Stremio.

## How It Works

1. **Catalog Discovery**: The addon scrapes musor.tv to find movies currently airing on Hungarian TV
2. **Channel Mapping**: Each catalog item is matched to a configured stream URL based on the channel
3. **Stream Delivery**: When users click a movie, the addon returns the live stream URL for that channel

## Configuration

Stream URLs are configured via **environment variables**. This allows you to:
- Keep stream URLs private and secure
- Update URLs without code changes
- Use different URLs for different deployments

### Environment Variables

Set environment variables for each channel you want to support:

```bash
# Public channels
STREAM_M1="https://example.com/m1.m3u8"
STREAM_M2="https://example.com/m2.m3u8"
STREAM_M4_SPORT="https://example.com/m4-sport.m3u8"
STREAM_M5="https://example.com/m5.m3u8"
STREAM_DUNA="https://example.com/duna.m3u8"
STREAM_DUNA_WORLD="https://example.com/duna-world.m3u8"

# Commercial channels
STREAM_RTL="https://example.com/rtl.m3u8"
STREAM_RTL2="https://example.com/rtl2.m3u8"
STREAM_RTL_KLUB="https://example.com/rtl-klub.m3u8"
STREAM_TV2="https://example.com/tv2.m3u8"
STREAM_SUPER_TV2="https://example.com/super-tv2.m3u8"
STREAM_COOL="https://example.com/cool.m3u8"

# Movie channels
STREAM_FILM="https://example.com/film.m3u8"
STREAM_FILMPLUS="https://example.com/filmplus.m3u8"
STREAM_FILM4="https://example.com/film4.m3u8"
STREAM_HBO="https://example.com/hbo.m3u8"
STREAM_HBO2="https://example.com/hbo2.m3u8"
STREAM_HBO3="https://example.com/hbo3.m3u8"
STREAM_CINEMAX="https://example.com/cinemax.m3u8"
STREAM_CINEMAX2="https://example.com/cinemax2.m3u8"
STREAM_AMC="https://example.com/amc.m3u8"
STREAM_AMC_HD="https://example.com/amc-hd.m3u8"
STREAM_PARAMOUNT="https://example.com/paramount.m3u8"
STREAM_COMEDY_CENTRAL="https://example.com/comedy-central.m3u8"
STREAM_PARAMOUNT_CHANNEL="https://example.com/paramount-channel.m3u8"

# International channels
STREAM_AXN="https://example.com/axn.m3u8"
STREAM_SONY="https://example.com/sony.m3u8"
STREAM_UNIVERSAL="https://example.com/universal.m3u8"
STREAM_PRIMA_PLUS="https://example.com/prima-plus.m3u8"
STREAM_PRIME="https://example.com/prime.m3u8"

# Other
STREAM_VIASAT3="https://example.com/viasat3.m3u8"
STREAM_VIASAT6="https://example.com/viasat6.m3u8"
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  stremio-addon:
    environment:
      - STREAM_RTL=https://your-stream-url.m3u8
      - STREAM_TV2=https://your-stream-url.m3u8
      # Add more as needed
```

### Render.com / Hosting Platforms

Add environment variables in your hosting platform's settings:
- **Render.com**: Settings → Environment → Add Environment Variable
- **Heroku**: Settings → Config Vars
- **Railway**: Variables tab

## Stream URL Sources

### Option 1: IPTV M3U Playlists

The most common solution for live TV streaming. You can:

1. **Use Public IPTV Lists**:
   - Search for "Hungarian IPTV m3u" playlists
   - Find on GitHub repositories like `iptv-org/iptv`
   - Note: Public streams may be unreliable or geo-restricted

2. **Subscribe to IPTV Services**:
   - Many providers offer Hungarian channel packages
   - Usually provide M3U playlist URLs
   - More reliable than free sources

3. **Extract from Your Own Subscription**:
   - If you have a legal TV subscription with online access
   - Some providers allow extracting stream URLs for personal use
   - Check terms of service

### Option 2: Official Channel Websites

Some Hungarian channels offer free online streaming:

- **M1, M2, M4, M5, Duna**: Public channels may have official streams
- **RTL Most**: RTL's streaming service
- **TV2 Play**: TV2's streaming platform

Check each channel's website for available streams. You may need to:
- Extract the stream URL from the web player
- Use browser developer tools (Network tab)
- Look for `.m3u8` or `.mpd` manifest files

### Option 3: YouTube Live Streams

Some channels stream live on YouTube:
- More stable and legal
- Usually free
- Can use YouTube stream URLs directly

## Stream URL Formats

The addon supports various stream formats:

- **HLS (M3U8)**: `https://example.com/stream.m3u8` - Most common for live TV
- **MPEG-DASH**: `https://example.com/stream.mpd` - Modern adaptive streaming
- **Direct MP4**: `https://example.com/video.mp4` - Less common for live content
- **YouTube**: `https://www.youtube.com/watch?v=VIDEO_ID` - If Stremio supports it

## Testing Streams

After configuration, test your streams:

1. **Check Configuration**:
   ```bash
   curl http://localhost:7000/healthz
   ```

2. **Test a Specific Stream**:
   ```bash
   curl http://localhost:7000/stream/movie/musortv:rtl:1234567890:test.json
   ```

3. **Validate Stream URL**:
   ```bash
   # Test if stream URL is accessible
   curl -I "YOUR_STREAM_URL"
   
   # Or use ffprobe
   ffprobe "YOUR_STREAM_URL"
   ```

## Security Considerations

⚠️ **Important**: 

1. **Never commit stream URLs to version control**
2. **Use environment variables** for all stream URLs
3. **Check licensing**: Ensure you have rights to use/redistribute streams
4. **Geo-restrictions**: Many streams are region-locked
5. **Rate limiting**: Some providers may limit concurrent connections

## Troubleshooting

### No Streams Appearing

1. Check if environment variables are set:
   ```bash
   echo $STREAM_RTL
   ```

2. Check logs for channel matching:
   ```bash
   docker logs stremio-addon 2>&1 | grep "channel"
   ```

3. Verify channel slug matches:
   - Addon converts channel names to slugs (lowercase, dashes)
   - "RTL Klub" → "rtl-klub"
   - "AMC HD" → "amc-hd"

### Streams Not Playing

1. **Test stream URL directly** in VLC or another player
2. **Check for geo-restrictions** - may need VPN
3. **Verify stream format** is supported by Stremio
4. **Check CORS headers** if playing in web browser

### Only Some Channels Work

This is normal - only channels with configured `STREAM_*` environment variables will provide streams. Movies on unsupported channels will still appear in the catalog but won't have playable streams.

## Adding New Channels

To add support for a new channel:

1. Find the channel slug used by the addon:
   - Check logs when catalog loads
   - Look at catalog IDs in API responses
   - Use `slugify(channel_name)` format

2. Add environment variable:
   ```bash
   STREAM_<CHANNEL_SLUG_UPPER>="stream_url"
   ```

3. Update `src/channel_streams.py` if needed (optional - env vars are loaded automatically)

## Example Configuration

Here's a complete working example:

```bash
# .env file (for local development)
PORT=7000
LOG_LEVEL=info
CACHE_TTL_MIN=10
SCRAPE_RATE_MS=30000

# Stream URLs (replace with actual URLs)
STREAM_RTL="https://example.com/rtl/index.m3u8"
STREAM_TV2="https://example.com/tv2/index.m3u8"
STREAM_AMC_HD="https://example.com/amc-hd/index.m3u8"
STREAM_HBO="https://example.com/hbo/index.m3u8"
```

Then run:
```bash
docker-compose up
```

## Legal Notice

This addon is a tool for aggregating and displaying TV schedule information. **You are responsible** for:

1. Ensuring you have legal rights to access and use any stream URLs
2. Complying with copyright laws in your jurisdiction
3. Respecting terms of service of streaming providers
4. Not redistributing copyrighted content without permission

The addon developers do not provide, host, or endorse any specific stream URLs.
