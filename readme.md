# HU Live Movies (musor.tv) — Stremio Catalog Add-on

**What it does:** exposes a single `catalog` of `movie` showing films airing in Hungary _now / next_ from musor.tv.

## Dev
```bash
# Node 18+
cp .env.example .env
npm i
npm run dev
# open http://localhost:7000/manifest.json
# add to Stremio: http://localhost:7000/manifest.json

# Directory layout
stremio-hu-live-movies/
├─ src/
│  ├─ index.ts            # entry: manifest + HTTP server + catalog handler
│  ├─ scraper.ts          # Playwright scraper (musor.tv)
│  ├─ types.ts            # small shared types
│  ├─ cache.ts            # in-memory LRU + TTL
│  ├─ timeWindow.ts       # parses extra.time and computes ranges
│  └─ util.ts             # helpers (slugify, diacritics, logging)
├─ test/
│  └─ scraper.fixtures.html  # optional: for offline parser tests
├─ .env.example
├─ .gitignore
├─ Dockerfile
├─ docker-compose.yml
├─ package.json
├─ tsconfig.json
├─ README.md
