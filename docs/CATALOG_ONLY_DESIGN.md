# Catalog-Only Addon Design

**Date:** October 20, 2025  
**Design Pattern:** Catalog/Discovery Addon  
**Status:** ✅ Implemented

## Philosophy

This addon follows Stremio's **separation of concerns** architecture:

| Addon Type | Responsibility | Example |
|------------|---------------|---------|
| **Catalog** | Discovery (what to watch) | This addon, Cinemeta |
| **Stream Provider** | Delivery (where to watch) | Torrentio, YouTube addon |

## Why Catalog-Only?

### ✅ Advantages

1. **Modularity**
   - Users mix and match their preferred stream sources
   - One catalog works with many stream providers
   - Easy to swap stream providers without losing catalog

2. **Simplicity**
   - No stream URL configuration needed
   - No IPTV provider dependencies
   - Simpler codebase, easier maintenance

3. **Legal Safety**
   - Addon doesn't host or link to streams
   - No copyright liability
   - Just provides TV schedule information (public data)

4. **Better UX**
   - Users already have stream addons installed
   - Consistent streaming experience across all content
   - No need to configure each catalog addon

5. **Stremio Best Practice**
   - Follows official Stremio addon architecture
   - Works seamlessly with Stremio's addon system
   - Future-proof design

### ❌ Alternatives Considered

**Option 1: Stream Provider Addon**
- ❌ Requires IPTV subscriptions or stream URLs
- ❌ Legal gray area (linking to streams)
- ❌ Configuration complexity
- ❌ Stream URLs break often
- ❌ Limited to one stream source

**Option 2: Hybrid (Catalog + Streams)**
- ❌ Violates separation of concerns
- ❌ Added complexity
- ❌ Users forced to use our stream source
- ❌ Harder to maintain

## How It Works

### User Flow

```
1. User installs catalog addon (this one)
   ↓
2. User browses Hungarian TV movies
   ↓
3. User clicks a movie
   ↓
4. Stremio queries installed stream addons
   ↓
5. Stream addons provide playback options
   ↓
6. User watches via their preferred stream source
```

### Stream Addon Integration

The catalog provides rich metadata that stream addons can use:

```json
{
  "id": "musortv:rtl:1760943000:matrix",
  "type": "movie",
  "name": "The Matrix",
  "release_info": "21:00 • RTL",
  "description": "📺 RTL • 21:00 • Akciófil m",
  "genres": ["Akció"],
  "poster": "https://..."
}
```

Stream addons can:
- Match by title (fuzzy search)
- Use genre/category information
- Check release year if available
- Provide multiple quality options

### Compatible Stream Addons

This catalog works with **any** stream provider addon:

**Popular Options:**
- **Torrentio** - Torrent streams
- **YouTube** - YouTube content
- **Cinemeta** - Metadata + some streams
- **IPTV addons** - Live TV streams
- **Custom Hungarian addon** - Local stream providers

Users can install multiple stream addons for best coverage!

## Technical Implementation

### `/stream` Endpoint

```python
@app.get("/stream/{type}/{id}.json")
async def get_stream(type: str, id: str):
    """Catalog addon - returns empty streams.
    
    This tells Stremio: "I don't provide streams, 
    ask other installed stream addons"
    """
    return JSONResponse(content={"streams": []})
```

### Manifest

```python
MANIFEST = {
    "resources": ["catalog", "stream"],  # Must declare both
    "catalogs": [{...}]  # Our catalog definition
}
```

**Why include "stream" if we don't provide streams?**
- Stremio protocol requirement
- Tells Stremio: "Query me for streams (I'll return empty)"
- Without it, Stremio won't show our catalog items in details view

### Empty Streams Response

```json
{
  "streams": []
}
```

**Meaning:** "This content exists, but I don't have streams. Ask other addons."

**NOT an error** - this is the correct behavior for catalog addons!

## User Setup

### Step 1: Install Catalog Addon

```
http://your-server.com/manifest.json
```

### Step 2: Install Stream Provider Addons

Users should install stream addons like:
- Torrentio (most popular)
- IPTV addon for Hungarian TV
- YouTube addon
- Any other stream sources

### Step 3: Use

1. Browse catalog from this addon
2. Click movie
3. Stremio automatically queries stream addons
4. Watch via available streams

**No configuration needed!**

## FAQ

### Q: Why don't I see streams?

**A:** You need to install stream provider addons separately. This is a catalog-only addon.

**Solution:**
1. Install Torrentio: `https://torrentio.strem.fun/manifest.json`
2. Or install IPTV addon for Hungarian live TV
3. Streams will appear automatically

### Q: Can this addon provide streams?

**A:** Technically yes, but it goes against Stremio's design principles and best practices. Better to keep catalog and streaming separate.

### Q: How do users watch content then?

**A:** Through their installed stream provider addons. Most Stremio users already have Torrentio or similar addons installed.

### Q: What if users want live Hungarian TV?

**A:** They should install a dedicated IPTV addon that provides Hungarian channels. This catalog will show what's on, the IPTV addon provides streams.

### Q: Won't this confuse users?

**A:** No - this is how Stremio is designed to work. Users are familiar with:
- Installing catalog addons for discovery
- Installing stream addons for playback
- They work together automatically

## Comparison

### Before (Stream Provider Approach)

```
❌ User must configure stream URLs
❌ Legal concerns
❌ Breaks when URLs change
❌ Single stream source
❌ Complex setup
```

### After (Catalog-Only Approach)

```
✅ Zero configuration
✅ No legal issues
✅ Works with any stream addon
✅ Multiple stream sources
✅ Simple, maintainable
```

## Future Enhancements

While keeping catalog-only design, we can improve metadata:

1. **Add IMDb IDs** - Better matching with stream addons
2. **Include year** - More accurate matches
3. **Better genre mapping** - Richer categorization
4. **Enhanced descriptions** - More context for users
5. **Links to official sources** - For manual viewing

All without providing streams!

## Related Documentation

- [Stremio Addon SDK](https://github.com/Stremio/stremio-addon-sdk)
- [Addon Examples](https://github.com/Stremio/addon-helloworld)
- [Manifest Specification](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/responses/manifest.md)

## Conclusion

**The catalog-only design is:**
- ✅ Simpler
- ✅ More maintainable  
- ✅ Legally safer
- ✅ Better UX (works with user's preferred streams)
- ✅ Follows Stremio best practices
- ✅ Future-proof

**It's the right architectural choice for this addon.**
