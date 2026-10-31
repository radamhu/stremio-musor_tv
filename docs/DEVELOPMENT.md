# Development Guide

Single home for all development-related notes. Repo-wide invariants live in [AGENTS.md](../AGENTS.md).

## Contents

1. [Architecture](#architecture)
2. [Data flow](#data-flow)
3. [Local setup and tests](#local-setup-and-tests)
4. [Scraper](#scraper)
5. [Parser fixture maintenance](#parser-fixture-maintenance)
6. [Midnight boundary handling](#midnight-boundary-handling)
7. [IMDb enrichment](#imdb-enrichment)
8. [CI/CD](#cicd)
9. [History: Playwright to httpx migration](#history-playwright-to-httpx-migration)
10. [Troubleshooting](#troubleshooting)

## Architecture

```
Stremio client
   │  GET /manifest.json | /catalog/... | /meta/...
   ▼
FastAPI (src/main.py)
   ├── catalog_handler.py ──► cache.py (TTL 10 min)
   │        │                   │ miss
   │        │                   ▼
   │        │             scraper.py ──► musor_parser.py ──► musor.tv
   │        ▼
   │   imdb_lookup.py + imdb_cache.py ──► TMDB API (optional)
   └── meta_handler.py
```

| Module | Responsibility |
| --- | --- |
| `src/main.py` | HTTP wiring, lifecycle, landing page, `/healthz` |
| `src/manifest.py` | Addon manifest (catalog + meta only) |
| `src/catalog_handler.py` | Cache, category/time/search filtering, IMDb lookup, Stremio transform |
| `src/meta_handler.py` | Detailed meta response (IMDb and `musortv:` ids) |
| `src/scraper.py` | `httpx` fetch, rate limit, retry/backoff, in-flight dedupe, health |
| `src/musor_parser.py` | Pure HTML parsing (`selectolax`), no network |
| `src/imdb_lookup.py`, `src/imdb_cache.py` | TMDB title to IMDb id lookup, 7-day cache of hits and misses |
| `src/time_window.py` | `now` / `next2h` / `tonight` presets, `Europe/Budapest` |
| `src/models.py`, `src/utils.py` | Pydantic models, slugify / accent stripping |

Stable integration points (do not change without approval): `fetch_live_movies(force=False)`, `get_scraper()`.

Catalog-only by design: no `/stream` route exists. Playback is handled by the user's other addons via IMDb ids.

## Data flow

1. Request arrives with optional `search` and `time`.
2. Catalog handler checks the TTL cache for the time preset.
3. Miss: scraper fetches musor.tv via plain HTTP and parses it.
4. Filter: films only, then time window.
5. IMDb lookup (title + year from category). Hit gives `tt…` id, miss falls back to `musortv:{channel}:{timestamp}:{slug}`.
6. Transform to Stremio preview (`release_info` = `"21:00 • RTL"`, mapped genres, description).
7. Cache result, apply accent-insensitive search, return JSON.

## Local setup and tests

```bash
pip install -r requirements.txt
cp .env.example .env
cd src && python main.py            # http://localhost:7000
```

```bash
# full offline suite
python -m pytest tests/ -q --ignore=tests/test_stream_support.py --ignore=tests/test_stream_endpoint.py

# scraper / parser / time
python -m pytest tests/test_musor_parser.py tests/test_scraper_refactor.py tests/test_midnight_boundary.py -q

# contracts
python -m pytest tests/test_contracts.py -q

# coverage
python -m pytest tests/ --cov=src --cov-report=html --ignore=tests/test_stream_support.py --ignore=tests/test_stream_endpoint.py
```

`tests/test_stream_support.py` and `tests/test_stream_endpoint.py` import modules that do not exist (catalog-only addon); exclude them.

Coverage: IMDb lookup + cache, Hungarian title normalization, midnight boundary, scraper lifecycle/retry, parser extraction, catalog/meta contract shapes, graceful degradation.

## Scraper

musor.tv is server-rendered; plain `httpx.get()` with a browser-like `User-Agent` returns full listing HTML. No browser needed.

- Rate limit: `SCRAPE_RATE_MS` (default 30 s), kept in one place.
- Retry with exponential backoff on transport errors; parse failures are logged separately and skipped.
- One scrape at a time (in-flight dedupe). Failures degrade to empty/partial results.
- Client is closed on shutdown.

Pages: `https://musor.tv/filmek` (`table.showeventtable`) and `https://musor.tv/most/tvben` (EPG grid, `div[itemtype="…BroadcastEvent"]`).

### Selector reference (`musor_parser.parse_filmek`)

| Field | Selector | Notes |
| --- | --- | --- |
| Container | `table.showeventtable` | one per entry |
| Title | `.showeventtitle a` | text |
| Start time | `.showeventtime` | text; ISO also in `content` attr |
| Channel | `.showeventchannel img` | `alt` attribute |
| Category | `td[itemprop="description"]` | optional |
| Poster | `img.showeventimg` | `src`, optional, relative URL absolutized |

Treat these as unstable. They are the first thing to update when musor.tv changes markup.

## Parser fixture maintenance

Fixtures in `tests/fixtures/`: `musor_filmek_sample.html` (5 entries), `musor_filmek.html` (full snapshot), `musor_tvben.html`, `musor_tvben_sample.html`.

Update when parser tests fail after an upstream change, `tests/test_live_selectors.py --live` reports 0 matches, or a new optional field needs coverage.

```bash
curl -sA "Mozilla/5.0" https://musor.tv/filmek -o tests/fixtures/musor_filmek.html
python -m pytest tests/test_live_selectors.py --live -q -s   # which selectors still match
# refresh the sample fixture by hand: keep title+time+channel, optional poster, optional category
python -m pytest tests/test_musor_parser.py -q
```

Drift checklist: run the live selector test, find which selector returns 0, inspect `https://musor.tv/filmek` in DevTools, update `src/musor_parser.py`, update the sample fixture, rerun parser tests.

## Midnight boundary handling

Listings only show `HH:MM`. A scrape at 23:00 containing a `01:00` entry must resolve to tomorrow, not 22 h ago. `infer_start_iso` uses a 12-hour threshold against the current Budapest time to detect the crossing. Covered by `tests/test_midnight_boundary.py`; keep it green for any time-logic change. `Europe/Budapest` is the canonical timezone, set `TZ` accordingly.

Presets: `now` = next 90 min, `next2h` = next 2 h, `tonight` = 18:00–23:59.

## IMDb enrichment

Optional augmentation via TMDB; the addon works without `TMDB_API_KEY`.

- Accepts a v3 API key (32 hex chars) or a Bearer JWT (`eyJ…`).
- Rate limit `IMDB_RATE_LIMIT_PER_SEC` (default 40), Hungarian-to-English fallback lookup.
- Cache keys are accent-normalized; successes and failures cached `IMDB_CACHE_TTL_DAYS` (default 7).
- About 75 % match rate on international films; Hungarian/regional titles fall back to custom ids.
- Without a match the id is `musortv:…`, which stream addons cannot resolve.

## CI/CD

Workflows in `.github/workflows/`:

| Workflow | Purpose |
| --- | --- |
| `ci.yml` | Pytest, lint, Hadolint, Trivy scan; Discord summary for non-PR runs |
| `build-and-push.yml` | Multi-arch (amd64/arm64) image to `ghcr.io/radamhu/stremio-musor-tv`; push to `main`/`develop`, `v*` tags, manual; PRs build only |
| `dependabot-automerge.yml` | Auto-merge eligible Dependabot PRs; Discord summary on merge, failure, skip |

Image tags: `latest` (main), branch name, `vX.Y.Z`, `X.Y`, `X`, `branch-sha`. Release with `git tag vX.Y.Z && git push origin vX.Y.Z`.

Discord notifications need the `DISCORD_WEBHOOK_URL` repository secret (Settings, Secrets and variables, Actions). Registry push uses the built-in `GITHUB_TOKEN`.

Check runs: `gh run list`, `gh run watch`.

Deploy targets: `render.yaml` (Docker runtime, `TMDB_API_KEY` as secret), `docker-compose.yml` (256 MB limit, `/healthz` healthcheck).

## History: Playwright to httpx migration

April 2026. Scraper rewritten from Playwright/Chromium to `httpx` + `selectolax`. No HTTP contract change.

| Area | Before | After |
| --- | --- | --- |
| Scraper | Playwright + headless Chromium | `httpx` + `selectolax` |
| Image size | ~1.18 GB | ~221 MB |
| Steady RAM | ~400–800 MB | ~62 MB |
| Dockerfile | multi-stage with Chromium | single-stage `python:3.11-slim` |
| Compose limits | 1 GB / 2 CPU | 256 MB / 1 CPU |
| Healthcheck | `/manifest.json` | `/healthz` |
| Removed env | `PLAYWRIGHT_BROWSERS_PATH`, `NODE_OPTIONS` | n/a |

Decision gate: musor.tv listing data is present in the initial HTML, so no browser. Do not reintroduce browser dependencies without an ADR.

Rollback: find the last Playwright commit (`git log --oneline --all -- requirements.txt | grep -i playwright`), branch from it, restore `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `render.yaml`, raise memory limits to 1 GB, and fix the parser regression before redeploying.

## Troubleshooting

**Empty catalog.** Check `/healthz` (`scraper.healthy`). Run `python -m pytest tests/test_live_selectors.py --live -q -s`. Logs: `transport failure` means network, `parse failure` means selector drift.

**Scraper errors at startup.** Scraper is lazy; first error shows on first catalog request. Check container egress to musor.tv, HTTP 200, and whether the `User-Agent` is blocked (`curl -sI -A "Mozilla/5.0" https://musor.tv/filmek`).

**No IMDb ids.** Need `IMDB_LOOKUP_ENABLED=true`, valid `TMDB_API_KEY`, `/healthz` `imdb_lookup.api_key_configured` true. Cache is cold on first run.

**Container exits immediately.** Read `docker logs <container>`; confirm `TZ=Europe/Budapest` and that `PORT` matches the port mapping.

**Import errors in stream tests.** Exclude `tests/test_stream_support.py` and `tests/test_stream_endpoint.py`.
