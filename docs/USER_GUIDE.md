# How to Watch Hungarian TV in Stremio

This addon shows you **what's on Hungarian TV**, but you need a **stream provider addon** to actually watch the content.

## Quick Setup (2 Steps)

### Step 1: Install This Catalog Addon

Add to Stremio:
```
http://your-server-url.com/manifest.json
```

**What you get:**
- ✅ Browse Hungarian TV movies
- ✅ See what's on now, next 2 hours, or tonight
- ✅ Search for specific titles
- ✅ Filter by channel and time

### Step 2: Install a Stream Provider Addon

You need at least one of these to actually watch content:

#### Option A: Torrentio (Recommended for most users)
```
https://torrentio.strem.fun/manifest.json
```
- ✅ Free
- ✅ No configuration
- ✅ Works for most content
- ⚠️ Requires torrent client

#### Option B: Hungarian IPTV Addon (Best for live TV)
Look for:
- "Hungarian TV" or "Magyar TV" addons in Stremio community
- IPTV addons that include Hungarian channels
- Regional addon providers

#### Option C: Other Stream Addons
- **YouTube** - For content available on YouTube
- **Cinemeta** - Basic streams
- **Local addons** - If you have access

## How It Works Together

```
1. You browse Hungarian TV movies in THIS addon
   ↓
2. You click a movie you want to watch
   ↓  
3. Stremio asks YOUR stream addons: "Do you have this?"
   ↓
4. Stream addons provide playback options
   ↓
5. You watch! 🎉
```

## Example Workflow

1. **Open Stremio** → Go to "Discover"
2. **Select "Live on TV (HU)"** catalog
3. **Browse movies** currently on Hungarian TV
4. **Click a movie** you want to watch
5. **Stremio shows streams** from your installed stream addons
6. **Pick a stream** and watch!

## FAQ

### Q: Why don't I see streams when I click a movie?

**A:** You need to install stream provider addons (see Step 2 above).

This addon only shows what's on TV - it doesn't provide the actual streams. That's by design!

### Q: Which stream addon should I use?

**For Hungarian live TV:**
- Best: IPTV addon with Hungarian channels
- Alternative: Record/save content and watch later via Torrentio

**For Hungarian movies:**
- Torrentio usually has good coverage
- YouTube addon for some content

### Q: Can this addon provide streams directly?

**A:** Technically yes, but we chose not to because:
- ✅ You already have stream addons installed
- ✅ They work better than we could build
- ✅ Keeps legal responsibility clear
- ✅ Follows Stremio's design principles

### Q: I have streams installed but still nothing shows

**Possible causes:**
1. Stream addon doesn't have that specific content
2. Title mismatch (different names in different databases)
3. Stream addon needs configuration

**Try:**
- Install another stream addon for more options
- Check if the movie title is correct
- Search manually in your stream addon

### Q: Do I need to pay for anything?

**This addon:** Free, open source

**Stream addons:** Depends which you choose
- Torrentio: Free
- IPTV addons: Usually require subscription
- YouTube: Free

## Recommended Setup

For best Hungarian TV experience:

```
1. This addon (catalog)
   + Torrentio (general content)
   + Hungarian IPTV addon (live TV)
   = Complete solution!
```

## Troubleshooting

### No streams available

1. Check you have stream addons installed
2. Go to Stremio Settings → Addons
3. You should see addons with "stream" capability
4. If not, install Torrentio at minimum

### Wrong content shows up

Sometimes stream addons match by title and might get it wrong. Try:
- Different stream addon
- Manual search
- Check movie details before playing

### Poor quality streams

- Install more stream addons for more options
- Premium IPTV usually has better quality
- Torrentio: higher seeds = better quality

## Best Practices

1. **Install multiple stream addons** - More options = better coverage
2. **Keep addons updated** - Stream sources change
3. **Use IPTV for live TV** - Better than VOD for current programming
4. **Browse, don't search** - Catalog browsing works best for "what's on now"

## Support

**For catalog issues** (addon not showing movies, wrong times, etc.):
- Check addon logs
- Report on GitHub

**For streaming issues** (no streams, won't play, etc.):
- Check your stream addon's documentation
- Not this addon's responsibility

## Summary

✅ **This addon** = Shows what's on Hungarian TV  
✅ **Stream addons** = Let you watch it

Together = Complete Stremio experience! 🎬

---

**Pro tip:** Once set up, you never have to think about it again. Just browse and watch! 