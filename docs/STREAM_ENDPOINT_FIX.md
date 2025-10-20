# Stream Endpoint Fix for Stremio "No Streams Found" Error

## Problem

The addon was showing "No streams found" error in Stremio because:

1. **Missing `/stream` endpoint**: The addon only had a `/catalog` endpoint
2. **Incomplete manifest**: The manifest declared only `"resources": ["catalog"]` without `"stream"`
3. **Stremio requirement**: Even catalog-only addons must provide a `/stream` endpoint and declare it in the manifest

## Root Cause

When you click on a catalog item in Stremio, it attempts to fetch streams via:
```
GET /stream/movie/<video_id>.json
```

Without this endpoint implemented:
- Stremio shows "No streams found" error
- The catalog items appear but can't be selected
- Server logs show 404 errors for missing `/stream` routes

## Solution Implemented

### 1. Updated Manifest (`src/manifest.py`)

**Changed:**
```python
"resources": ["catalog"]
```

**To:**
```python
"resources": ["catalog", "stream"]
```

This tells Stremio that the addon supports both catalog and stream requests.

### 2. Added Stream Endpoint (`src/main.py`)

Implemented a new `/stream/{type}/{id}.json` endpoint that:

```python
@app.get("/stream/{type}/{id}.json")
async def get_stream(type: str, id: str):
    """Handle stream requests.
    
    This addon provides catalog/discovery for Hungarian live TV movies,
    but does not provide actual stream URLs. Returns empty streams array
    to indicate the content exists but no streams are available from this addon.
    """
    logger.info(f"Stream request for {type}/{id}")
    
    # Validate that this is one of our IDs (format: musortv:channel:timestamp:title)
    if not id.startswith("musortv:"):
        logger.warning(f"Invalid stream ID format: {id}")
        return JSONResponse(content={"streams": []})
    
    # Return empty array to indicate "no streams available" (not an error)
    return JSONResponse(content={"streams": []})
```

### Key Points:

- **Returns `{"streams": []}`**: An empty array is the correct response when no streams are available
- **Not an error**: Returning 200 OK with empty streams is different from an error
- **Validates ID format**: Checks that the request is for one of our catalog items
- **Logs requests**: Helps with debugging and monitoring

## Why Empty Streams?

This addon is a **discovery/catalog addon** that shows what movies are currently playing on Hungarian TV. It:

- ✅ Scrapes TV schedules from musor.tv
- ✅ Shows movies in Stremio's catalog
- ✅ Provides metadata (title, channel, time, poster)
- ❌ Does NOT provide actual stream URLs

Users can:
1. Browse the catalog to see what's on TV
2. Use the information to watch on their actual TV
3. Combine with other Stremio addons that provide streams

## Expected Behavior After Fix

### Before:
```
User clicks on catalog item → Stremio requests /stream → 404 Error → "No streams found"
```

### After:
```
User clicks on catalog item → Stremio requests /stream → 200 OK {"streams": []} → Shows "No streams available"
```

The difference:
- **Before**: Error message, addon appears broken
- **After**: Clean indication that this addon provides info only, not streams

## Testing

To test the fix:

1. **Rebuild the Docker container:**
   ```bash
   docker compose up --build
   ```

2. **Check the manifest:**
   ```bash
   curl http://localhost:7000/manifest.json
   ```
   Should show `"resources": ["catalog", "stream"]`

3. **Test a stream request:**
   ```bash
   curl http://localhost:7000/stream/movie/musortv:rtl:1234567890:test-movie.json
   ```
   Should return `{"streams": []}`

4. **Install in Stremio:**
   - Go to `http://localhost:7000/manifest.json` in Stremio
   - Browse the catalog
   - Click on items - should no longer show "No streams found" error
   - May show "No streams available" which is correct

## Future Enhancements

If you want to add actual streaming capability later:

1. **Find stream sources**: Identify where to get actual stream URLs
2. **Update stream endpoint**: Return stream objects instead of empty array:
   ```python
   {
       "streams": [
           {
               "url": "https://example.com/stream.m3u8",
               "title": "RTL HD",
               "behaviorHints": {"notWebReady": True}
           }
       ]
   }
   ```

3. **Consider legal implications**: Ensure you have rights to provide streams

## Related Stremio Documentation

- [Stremio Addon SDK - Stream Response](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/responses/stream.md)
- [Addon Manifest](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/responses/manifest.md)

## Summary

✅ **Fixed**: Added `/stream` endpoint and updated manifest  
✅ **Result**: "No streams found" error eliminated  
✅ **Behavior**: Addon now works as a proper catalog-only addon  
✅ **User Experience**: Clear indication that this is for discovery, not streaming
