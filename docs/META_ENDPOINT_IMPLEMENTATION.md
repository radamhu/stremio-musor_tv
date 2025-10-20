# Meta Endpoint Implementation

## Problem

The addon was showing movies in the catalog successfully, but when users clicked on a movie in Stremio, they saw **"no information found about this"**. This happened because:

1. ✅ The addon had `/catalog/{type}/{id}.json` - showing the list of movies
2. ✅ The addon had `/stream/{type}/{id}.json` - (returns empty by design)
3. ❌ The addon was **missing** `/meta/{type}/{id}.json` - providing detailed movie information

When users click a movie in Stremio, it tries to fetch detailed metadata from the `/meta/` endpoint to show in the movie details page.

## Solution

Added a complete meta endpoint implementation that provides rich movie information:

### Files Added/Modified

1. **`src/meta_handler.py`** (NEW)
   - Parses movie IDs (format: `musortv:channel:timestamp:title-slug`)
   - Fetches live movies from scraper
   - Matches the requested movie by channel, timestamp, and title
   - Returns rich metadata with Hungarian descriptions

2. **`src/models.py`** (MODIFIED)
   - Added `StremioMeta` class for full metadata format
   - Includes fields: poster, background, description, genres, release info, etc.
   - Also added missing `StremioStream` class

3. **`src/manifest.py`** (MODIFIED)
   - Added `"meta"` to the resources array
   - Now declares: `["catalog", "meta", "stream"]`

4. **`src/main.py`** (MODIFIED)
   - Added `/meta/{type}/{id}.json` endpoint
   - Imports `meta_handler` and calls it for meta requests
   - Handles URL decoding and error cases gracefully

## What the Meta Endpoint Provides

```json
{
  "meta": {
    "id": "musortv:film-hd:1760961000:ut-a-szabadsagba",
    "type": "movie",
    "name": "Út a szabadságba",
    "poster": "https://musor.tv/img/small/84/8416/Ut_a_szabadsagba.jpg",
    "background": "https://musor.tv/img/small/84/8416/Ut_a_szabadsagba.jpg",
    "description": "📺 **Csatorna:** film+ (HD)\n🕐 **Kezdés:** 2025.10.20 13:50\n🎬 **Műfaj:** amerikai-kalandfilm\n\n📡 **Élő adás a magyar TV-ből**\n\n💡 *Tipp: Használj stream kiegészítőt (pl. Torrentio) a megtekintéshez*",
    "releaseInfo": "📅 2025.10.20 • 13:50",
    "genres": ["Kaland"]
  }
}
```

### Features

- **Rich Hungarian descriptions** with emojis for better UX
- **Channel information** prominently displayed
- **Broadcast time** in human-readable format (date + time)
- **Genre mapping** from Hungarian to standardized categories
- **User tips** suggesting to use stream addons
- **Poster and background** images from musor.tv
- **Error handling** - returns null meta gracefully if movie not found

## Testing

```bash
# 1. Get movie IDs from catalog
curl -s 'http://localhost:7000/catalog/movie/hu-live.json?time=now' | jq '.metas[0].id'

# 2. Fetch metadata for a specific movie
curl -s 'http://localhost:7000/meta/movie/musortv:film-hd:1760961000:ut-a-szabadsagba.json' | jq .

# 3. Verify manifest includes "meta"
curl -s 'http://localhost:7000/manifest.json' | jq '.resources'
```

## User Experience

**Before:**
- User browses catalog ✅
- User clicks movie ❌ "no information found about this"

**After:**
- User browses catalog ✅
- User clicks movie ✅ Sees rich details: title, poster, description, channel, time, genre
- User can then use their installed stream addons to watch ✅

## Architecture

The addon now follows the complete Stremio catalog addon pattern:

```
/manifest.json         → Declares catalog, meta, stream resources
/catalog/.../....json  → Lists movies (previews)
/meta/.../....json     → Shows detailed movie information (NEW!)
/stream/.../....json   → Returns empty (delegates to stream addons)
```

This is the standard **catalog/discovery addon** architecture where:
- **This addon** = Discovers content (what's on TV)
- **Stream addons** = Provides playback (Torrentio, etc.)

## Future Improvements

- [ ] Add caching for meta responses (similar to catalog)
- [ ] Fetch additional metadata from external APIs (TMDB, IMDB)
- [ ] Add movie duration if available from scraper
- [ ] Add cast/director information if available
- [ ] Consider adding "related" movies (same time slot, other channels)
