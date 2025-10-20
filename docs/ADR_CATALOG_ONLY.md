# Architecture Decision: Catalog-Only Design

**Date:** October 20, 2025  
**Decision:** Implement as catalog/discovery addon, not stream provider  
**Status:** ✅ Implemented

## Summary

After implementing stream provider functionality, we **reverted to a catalog-only design** following Stremio's architectural best practices.

## The Journey

### 1. Initial State: Catalog-Only (Basic)
- Addon showed Hungarian TV movies
- Returned empty streams
- Users wondered how to watch

### 2. Stream Provider Implementation (Attempted)
- Added `channel_streams.py` for URL mapping
- Created `stream_handler.py` for stream delivery
- Environment variable configuration
- Full streaming capability

### 3. Final Decision: Catalog-Only (Refined)
- **Reverted stream provider code**
- **Enhanced metadata** for better stream addon compatibility
- **Clarified purpose** in documentation
- Follows Stremio's separation of concerns

## Why Catalog-Only Won

### Technical Reasons

1. **Separation of Concerns**
   ```
   Catalog Addon → "What's on TV"
   Stream Addon → "How to watch it"
   ```

2. **Modularity**
   - One catalog works with many stream sources
   - Users choose their preferred stream providers
   - Easy to swap providers without losing catalog

3. **Maintainability**
   - Simpler codebase
   - No stream URL management
   - No IPTV provider dependencies

### User Experience

1. **Flexibility**
   - Users already have stream addons (Torrentio, etc.)
   - Works with ANY stream provider they install
   - Consistent streaming experience

2. **Zero Configuration**
   - No stream URLs to configure
   - No IPTV subscriptions needed
   - Install and use immediately

3. **Better Integration**
   - Leverages Stremio's addon ecosystem
   - Users get multiple stream options
   - Higher quality streams from dedicated providers

### Legal & Safety

1. **No Liability**
   - Doesn't host or link to streams
   - Only provides public TV schedule data
   - No copyright concerns

2. **Compliance**
   - Follows Stremio guidelines
   - No terms of service violations
   - Safe to distribute publicly

## Implementation Changes

### Files Modified (Reverted Stream Support)

1. **`src/main.py`** - Stream endpoint returns empty with clear comment
2. **`src/models.py`** - Removed stream URL fields, kept enhanced description
3. **`src/manifest.py`** - Updated description to clarify catalog-only
4. **`src/catalog_handler.py`** - Enhanced metadata with channel/time info
5. **`README.md`** - Updated architecture and purpose sections

### Files Retained (For Reference)

The stream provider implementation files are kept for historical reference but not used:
- `src/channel_streams.py` - Channel→URL mapping (unused)
- `src/stream_handler.py` - Stream delivery logic (unused)
- `docs/STREAM_CONFIGURATION.md` - Configuration guide (reference only)
- `docs/STREAM_SUPPORT_SUMMARY.md` - Implementation details (archived)

**Note:** These can be safely deleted or moved to an `archive/` folder.

### New Documentation

1. **`docs/CATALOG_ONLY_DESIGN.md`** - Explains catalog-only philosophy
2. **Updated `README.md`** - Clarifies purpose and architecture

## Current Architecture

```
┌──────────────────┐
│  Stremio Client  │
└────────┬─────────┘
         │
         ├─→ This Addon (Catalog)
         │   - Shows Hungarian TV movies
         │   - Returns empty streams
         │
         └─→ Stream Addons (User's choice)
             - Torrentio
             - IPTV addon
             - YouTube
             - etc.
```

## How Users Use It

1. **Install this catalog addon**
   ```
   http://your-server.com/manifest.json
   ```

2. **Install stream provider addons** (if not already)
   - Torrentio (most popular)
   - IPTV addon for Hungarian TV
   - Any other stream sources

3. **Browse and watch**
   - Browse Hungarian TV movies in this catalog
   - Click a movie
   - Stremio queries installed stream addons
   - Watch via available streams

## Metadata Enhancements

Even as catalog-only, we provide rich metadata:

```json
{
  "id": "musortv:rtl:1760943000:matrix",
  "type": "movie",
  "name": "The Matrix",
  "release_info": "21:00 • RTL",
  "description": "📺 RTL • 21:00 • Akciófilm",
  "genres": ["Akció"],
  "poster": "https://musor.tv/..."
}
```

This helps stream addons:
- Match content by title
- Provide relevant streams
- Show better results

## Benefits Realized

### For Users
- ✅ Works with their existing stream addons
- ✅ No configuration needed
- ✅ Multiple stream sources available
- ✅ Consistent Stremio experience

### For Developers
- ✅ Simpler codebase
- ✅ Less maintenance
- ✅ No legal concerns
- ✅ Follows best practices

### For the Ecosystem
- ✅ Proper separation of concerns
- ✅ Composable addons
- ✅ Standard Stremio patterns
- ✅ Future-proof design

## Comparison

| Aspect | Stream Provider | Catalog-Only |
|--------|----------------|--------------|
| Configuration | STREAM_* env vars | None |
| Dependencies | IPTV provider | None |
| Legal | Gray area | Safe |
| Flexibility | Single source | Multiple sources |
| Maintenance | High | Low |
| User Setup | Complex | Simple |
| Stremio Pattern | Non-standard | Standard |

## Future Enhancements

While staying catalog-only, we can improve:

1. **Add IMDb IDs** - For better stream addon matching
2. **Include release years** - More accurate matches
3. **Better genre mapping** - Richer categorization
4. **Enhanced descriptions** - More context
5. **Actor/director info** - If available on musor.tv

All improvements focus on **better discovery**, not streaming.

## Lessons Learned

1. **Follow platform patterns** - Stremio designed catalog/stream separation for good reasons
2. **Keep it simple** - Fewer features, better UX
3. **Legal matters** - Streaming has legal implications, discovery doesn't
4. **User expectations** - Users expect modular addons in Stremio
5. **Maintainability** - Simpler code = easier maintenance

## Conclusion

**The catalog-only design is the right choice** for this addon because:

1. ✅ Follows Stremio's architecture
2. ✅ Better user experience
3. ✅ Simpler implementation
4. ✅ Legally safe
5. ✅ More maintainable
6. ✅ Future-proof

The brief detour into stream provider functionality helped us understand the alternatives and make an informed decision. The final catalog-only design is stronger for having considered both approaches.

## Related Documentation

- [CATALOG_ONLY_DESIGN.md](CATALOG_ONLY_DESIGN.md) - Detailed design rationale
- [README.md](../README.md) - Updated user documentation
- [Stremio Addon SDK](https://github.com/Stremio/stremio-addon-sdk) - Official guidelines

---

**This architectural decision record documents why we chose catalog-only over stream provider, ensuring future developers understand the rationale.**
