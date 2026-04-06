# Scraper Refactor Summary

## Overview

The musor.tv scraper was rewritten from a Playwright headless-browser implementation to a
lightweight HTTP + HTML parser stack using `httpx` and `selectolax`. No addon HTTP contract was
changed.

## Motivation

The original scraper launched a headless Chromium browser on startup, which required:

- `playwright==1.47.0` in `requirements.txt`
- Chromium binary (~900 MB download during Docker build)
- Large system library set (`apt-get` installs in Dockerfile)
- 1–2 GB RAM for browser runtime
- Slow Docker builds and deploys

The browser was not needed — musor.tv pages are server-side rendered and return full HTML in
the initial HTTP response.

## Decision Gate Outcome

Plain `httpx.get()` with a browser-like `User-Agent` header returns HTTP 200 from both pages.
Cookie consent HTML is present in the page but does not gate the listing data for server-side
fetches.

| Page                    | Static HTML content                                  |
| ----------------------- | ---------------------------------------------------- |
| `https://musor.tv/filmek`     | `table.showeventtable` — 20 entries      |
| `https://musor.tv/most/tvben` | EPG grid (`div[itemtype="...BroadcastEvent"]`) |

## What Changed

### Dependencies

| Before                   | After                   |
| ------------------------ | ----------------------- |
| `playwright==1.47.0`   | `httpx==0.27.2`       |
| _(implicit chromium)_    | `selectolax==0.3.21`  |

### Source files

| File                     | Change                                                                                              |
| ------------------------ | --------------------------------------------------------------------------------------------------- |
| `src/scraper.py`       | Transport layer rewritten: `httpx.AsyncClient` replaces Playwright browser. Retry with exponential backoff added. Public API (`fetch_live_movies`, `get_scraper`) unchanged. |
| `src/musor_parser.py`  | New module. Pure HTML parsing isolated here. `parse_filmek`, `cleanup`, `infer_start_iso`, `absolutize`, `dedupe`. No network access. |
| `Dockerfile`           | Single-stage `python:3.11-slim`. All Playwright/Chromium install steps removed.                    |
| `docker-compose.yml`   | Memory limit: `1G` → `256M`. CPU limit: `2` → `1`. Healthcheck: `/manifest.json` → `/healthz`. |
| `render.yaml`          | Playwright env vars removed. IMDB env vars added. `TMDB_API_KEY` declared as secret.              |
| `requirements.txt`     | `playwright` replaced by `httpx`. `selectolax` added.                                              |

### Docker image size

| Build       | Size    |
| ----------- | ------- |
| Before      | 1.18 GB |
| After       | 221 MB  |
| Reduction   | −81%   |

### Memory usage (steady-state)

| Before (Playwright) | After (lightweight) |
| ------------------- | ------------------- |
| ~400–800 MB        | ~62 MB              |

## Public API Stability

The following interfaces are unchanged and remain stable:

- `fetch_live_movies(force=False)` — returns `List[LiveMovieRaw]`
- `get_scraper()` — returns singleton `MusorTvScraper`
- `get_status()` — returns health dict consumed by `/healthz`
- All Stremio HTTP endpoints and response shapes

## Architecture After Refactor

```
src/scraper.py          — orchestration, retry, rate limit, health
src/musor_parser.py     — pure HTML parsing (selectolax CSS selectors)
```

`scraper.py` calls `parse_filmek(html)` and `dedupe(items)` from `musor_parser.py`.
The parser has no dependency on the scraper and is independently testable with HTML fixtures.

## Selector Reference

These CSS selectors are used by `musor_parser.parse_filmek`:

| Field      | Selector                                        | Notes                              |
| ---------- | ----------------------------------------------- | ---------------------------------- |
| Container  | `table.showeventtable`                        | One per listing entry              |
| Title      | `.showeventtitle a`                           | `.text(strip=True)`              |
| Start time | `.showeventtime`                              | `.text(strip=True)`; ISO also in `content` attr |
| Channel    | `.showeventchannel img` → `alt` attribute     |                                    |
| Category   | `td[itemprop="description"]`                  | Optional — may be absent           |
| Poster     | `img.showeventimg` → `src` attribute          | Optional; relative URL absolutized |

If musor.tv changes its HTML structure, these selectors are the first place to update. See
[Parser Fixture Maintenance](#parser-fixture-maintenance) below.

## Parser Fixture Maintenance

Test stability depends on HTML fixture files that mirror live musor.tv page structure.

### Fixtures location

```
tests/fixtures/musor_filmek_sample.html    — 5 showeventtable entries (unit tests)
tests/fixtures/musor_filmek.html           — full live snapshot (~163 KB)
tests/fixtures/musor_tvben.html            — full live snapshot (~1.1 MB)
tests/fixtures/musor_tvben_sample.html     — 5 BroadcastEvent entries
```

### When to update fixtures

Update fixtures when:
- Parser tests start failing after a musor.tv HTML structure change
- `python debug/debug_selectors_v2.py` shows 0 matches for a previously-working selector
- A new optional field needs to be covered (add a sample entry with that field)

### How to update fixtures

```bash
# Dump fresh HTML from live pages
python debug/dump_html.py
# Outputs to /tmp/musor_filmek.html and /tmp/musor_tvben.html

# Inspect which selectors still match
python debug/debug_selectors_v2.py

# Copy the updated page snapshot to fixtures
cp /tmp/musor_filmek.html tests/fixtures/musor_filmek.html

# For the sample fixture, extract 5 representative entries manually
# (keep entries that cover: title+time+channel, optional poster, optional category,
#  and update musor_filmek_sample.html accordingly)

# Re-run parser tests to confirm
python -m pytest tests/test_musor_parser.py -q
```

### Selector drift diagnosis checklist

1. Run `python debug/debug_selectors_v2.py` against live site
2. Check which of the six selectors above returns 0 matches
3. Use browser DevTools on `https://musor.tv/filmek` to find the new element name
4. Update the selector in `src/musor_parser.py`
5. Update the relevant `tests/fixtures/musor_filmek_sample.html` entry if structure changed
6. Run `python -m pytest tests/test_musor_parser.py -q` — all tests must pass

## Rollback

The Playwright-based implementation no longer exists on `main`. To roll back if a critical
parser regression is discovered:

1. Identify the last Playwright commit: `git log --oneline --all -- requirements.txt | grep playwright`
2. Create `rollback/playwright` branch from that commit
3. Revert `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `render.yaml`
4. Raise memory limits back to `1G` in docker-compose and Render
5. Root-cause and fix the parser regression before re-deploying the lightweight build
