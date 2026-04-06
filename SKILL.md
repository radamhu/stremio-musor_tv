# SKILL.md — stremio-musor_tv Project Workflows

Canonical playbooks for recurring tasks in this repo.
Keep this file up to date when a new repeatable workflow emerges.

---

## 1. Implementing a Phase from LIGHTWEIGHT_SCRAPER_REFACTOR_PLAN.md

### When to use

When the user asks to implement a numbered phase from
`docs/LIGHTWEIGHT_SCRAPER_REFACTOR_PLAN.md`.

### Steps

1. **Read the plan.** Open `docs/LIGHTWEIGHT_SCRAPER_REFACTOR_PLAN.md` and locate the target
   phase section. Note its tasks and acceptance criteria exactly — do not guess or invent tasks.

2. **Read all affected files before editing.** For each file mentioned (e.g. `src/scraper.py`,
   `Dockerfile`, `requirements.txt`), read and understand it before making changes.

3. **Implement tasks in the stated order.** Each task should be a discrete, reviewable change.
   Use `manage_todo_list` to track and mark each task as it completes.

4. **Use subagents for parallel or multi-file work.** When multiple independent files need
   editing (e.g. Dockerfile + docker-compose.yml + render.yaml), delegate to a subagent with
   precise instructions including exact expected file content and context lines.

5. **Verify acceptance criteria.** Run the relevant test commands and/or Docker build to confirm
   each criterion is met before updating the plan doc.
   - Parser/scraper tests: `python -m pytest tests/ -q --ignore=tests/test_stream_support.py --ignore=tests/test_stream_endpoint.py`
   - Docker build + size check:
     ```
     docker build -t stremio-musor-tv:phase-N . && \
     docker image inspect stremio-musor-tv:phase-N --format '{{.Size}}' | \
       awk '{printf "%.0f MB\n", $1/1024/1024}'
     ```
   - Endpoint validation (Phase 7 rollout): start the built image and exercise all endpoints:
     ```bash
     docker run -d --name stremio-val -p 7000:7000 stremio-musor-tv:phase-N
     sleep 6
     # trigger scraper init (lazy — requires first catalog request)
     curl -s "http://localhost:7000/catalog/movie/hu-live.json?time=now"
     curl -s http://localhost:7000/healthz
     curl -s http://localhost:7000/manifest.json
     curl -s "http://localhost:7000/catalog/movie/hu-live.json?time=next2h"
     curl -s "http://localhost:7000/catalog/movie/hu-live.json?search=<title>"
     # pick an id from catalog output for meta check
     curl -s "http://localhost:7000/meta/movie/<id>.json"
     docker rm -f stremio-val
     ```
   - Memory check: `docker stats <container> --no-stream --format "{{.MemUsage}}"`
     Expected steady-state: ~62 MB (no browser runtime).

6. **Record results in the plan doc.** Append a `#### Phase N Results (YYYY-MM-DD)` subsection
   immediately after the acceptance criteria block for the phase. Include:
   - Summary table of changes made
   - Test pass counts and timings
   - Measured metrics (image size, test count, etc.)
   - "All N acceptance criteria satisfied." statement

### Result section template

```markdown
#### Phase N Results (YYYY-MM-DD)

**<Component> changed — <summary description>**

| What          | Before | After |
| ------------- | ------ | ----- |
| <metric>      | <old>  | <new> |

<Prose summary of key changes.>

**Test run: N passed in X.Xs**

All N acceptance criteria satisfied.
```

---

## 2. Running the Test Suite

```bash
# All tests (offline, deterministic)
python -m pytest tests/ -q --ignore=tests/test_stream_support.py --ignore=tests/test_stream_endpoint.py

# Core scraper/parser/time tests
python -m pytest tests/test_musor_parser.py tests/test_scraper_refactor.py tests/test_midnight_boundary.py -q

# Contract tests only
python -m pytest tests/test_contracts.py -q
```

Tests must pass without network access and without browser binaries installed.
If a test requires live network, it should be skipped by default in CI.

`tests/test_stream_support.py` imports a `stream_handler` module that does not exist and
must be excluded until that module is implemented. Use `--ignore` or `-k` to skip it.

`tests/test_stream_endpoint.py` imports `main` with a bare module name (`from main import app`)
which fails outside the `src/` directory. Exclude it with `--ignore` until the import path is
fixed.

---

## 3. Documentation-Only Phases

### When to use

When a phase's tasks are exclusively documentation updates (README edits, new docs files,
cross-reference fixes) with no code, test, or config changes.

### Pattern

1. Read the phase section in the plan to identify exactly which documents and sections to touch.
2. Audit current state of each target file before editing — do not rewrite docs that are already
   accurate (prior phases may have done partial work).
3. Check for broken links in README (referenced `docs/` files that don't exist).
4. Implement changes: README edits, new `docs/` files, updated cross-references.
5. For documentation phases, test verification is: confirm the test suite still passes (docs
   don't add a test surface), and confirm referenced files exist.
6. Record results in the plan using the standard result template, noting "documentation only —
   test count unchanged" instead of a delta.

### Standard test verification for doc-only phases

```bash
python -m pytest tests/ -q --ignore=tests/test_stream_support.py --ignore=tests/test_stream_endpoint.py
```

Expected: same pass count as the preceding phase. If it changes, something beyond docs was touched.

### What belongs in `docs/SCRAPER_REFACTOR_SUMMARY.md`

That file is the canonical reference for the lightweight scraper. Keep it up to date when:
- Selectors change in `src/musor_parser.py`
- New fixtures are added or renamed
- Rollback procedures become stale
- Memory or image size baselines change materially

### Test module map (post Section 8)

| Module | What it covers |
|--------|---------------|
| `test_musor_parser.py` | Pure parser: `parse_filmek`, `cleanup`, `infer_start_iso` (incl. malformed input + per-entry resilience), `absolutize`, `dedupe` |
| `test_scraper_refactor.py` | Scraper lifecycle, `_get_page` retry/failure, integration pipeline with mocked HTTP, health state transitions |
| `test_midnight_boundary.py` | `infer_start_iso` midnight boundary and edge cases (patches `musor_parser.datetime`) |
| `test_contracts.py` | Catalog schema, meta schema, ID format compatibility, graceful degradation on scraper failure |

### Patching conventions

- Midnight boundary tests patch `musor_parser.datetime` (not `scraper.datetime` — `infer_start_iso` lives in `musor_parser`)
- Retry tests patch `asyncio.sleep` via `patch('asyncio.sleep', new=AsyncMock())` to keep execution fast
- Integration tests replace `scraper._http_client.get` with `AsyncMock(return_value=mock_response)` after `initialize()`

---

## 3. Docker Build and Size Check

```bash
# Build and tag
DOCKER_BUILDKIT=1 docker build -t stremio-musor-tv:latest .

# Check image size
docker image inspect stremio-musor-tv:latest --format '{{.Size}}' | \
  awk '{printf "%.0f MB\n", $1/1024/1024}'

# Run locally
docker-compose up --build
```

Expected image size after Phase 4 lightweight refactor: ~220 MB.
Pre-refactor baseline (Playwright): ~1.18 GB.

---

## 4. Adding a New Environment Variable

1. Add to `src/main.py` or the relevant module with a safe default via `os.getenv("VAR", default)`.
2. Add to `docker-compose.yml` under `environment:`.
3. Add to `render.yaml` under `envVars:`.
4. Document in `README.md` under the configuration section.
5. Do NOT commit secrets. Use `${VAR:-}` passthrough patterns for optional secrets in compose.

---

## 5. Updating HTML Fixtures

When musor.tv changes its page structure and scraper tests break:

1. Fetch a fresh snapshot:
   ```python
   import httpx, pathlib
   headers = {"User-Agent": "Mozilla/5.0 ..."}
   r = httpx.get("https://musor.tv/filmek", headers=headers)
   pathlib.Path("tests/fixtures/musor_filmek.html").write_text(r.text)
   ```
2. Inspect the new HTML for selector changes using `debug/debug_selectors_v2.py`.
3. Update selectors in `src/musor_parser.py` with documented comments explaining the structure.
4. Update `tests/fixtures/musor_filmek_sample.html` to a current 5-entry excerpt.
5. Run `python -m pytest tests/test_musor_parser.py -q` to confirm.
6. Commit both fixture and parser changes together.

Key invariant: `table.showeventtable` is the root container on `/filmek`.
If that selector disappears, stop and inspect the new HTML before guessing alternatives.

---

## 6. Debug Script Inventory

All scripts in `debug/` use `httpx` + `selectolax` — no browser required.

| Script | Purpose | Run command |
| ------ | ------- | ----------- |
| `debug_selectors.py` | Count CSS selector hits on live pages; confirm selectors still work | `python debug/debug_selectors.py` |
| `debug_selectors_v2.py` | Inspect filmek table entries and BroadcastEvent entries on both pages | `python debug/debug_selectors_v2.py` |
| `dump_html.py` | Fetch live pages and save full HTML to `/tmp/` for offline inspection | `python debug/dump_html.py` |
| `demo_midnight_fix.py` | Demonstrate midnight boundary detection scenarios | `python debug/demo_midnight_fix.py` |
| `validate_stream_endpoint.py` | Smoke-test running server endpoints via stdlib HTTP | `python debug/validate_stream_endpoint.py [BASE_URL]` |

---

## 7. Scraper Integration Points (Stable API)

These symbols are the public API consumed by catalog and meta handlers.
Do NOT rename or change signatures without updating callers.

| Symbol | Location | Description |
| ------ | -------- | ----------- |
| `fetch_live_movies(force=False)` | `src/scraper.py` | Returns `List[LiveMovie]` |
| `get_scraper()` | `src/scraper.py` | Returns singleton `MusorTvScraper` |
| `get_status()` | `src/scraper.py` | Returns health dict for `/healthz` |
| `parse_filmek(html)` | `src/musor_parser.py` | Pure HTML parser, returns `List[LiveMovieRaw]` |
| `dedupe(items)` | `src/musor_parser.py` | Deduplicates on title+channel key |

---

## 8. Scraper Rollback Procedure

Use when a production regression cannot be quickly fixed in `src/musor_parser.py` and an urgent
rollback to the pre-lightweight build is required.

**Before rolling back** — confirm the failure mode:

1. `python debug/debug_selectors_v2.py` — check if selectors still match live musor.tv HTML.
2. `python -m pytest tests/test_musor_parser.py -q` — confirm fixtures still pass.
3. If only selectors drifted: update `src/musor_parser.py` + fixture, no rollback needed.

**Full rollback steps:**

1. Find the last Playwright commit:
   ```bash
   git log --oneline --all -- requirements.txt | grep -i playwright
   ```
2. Create a rollback branch:
   ```bash
   git checkout -b rollback/playwright <commit-sha>
   ```
3. Files to restore: `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `render.yaml`.
4. On Render: deploy from `rollback/playwright` branch.
   - Build will reinstall Chromium (~10 min).
   - Raise memory limit back to `1G` in `render.yaml` / Render dashboard.
5. Root-cause and fix the lightweight build on a separate branch before re-promoting.

**Key runtime benchmarks (lightweight build — Phase 7 confirmed):**

| Metric | Value |
| ------ | ----- |
| Docker image size | 221 MB |
| Steady-state memory | ~62 MB |
| Scraper init | lazy — on first catalog request |
| Test suite | 40 passed in 0.47 s (offline, no browser) |
