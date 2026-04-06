# AGENTS.md

Canonical repo rules.

If anything conflicts with this file, this file wins.

## 1. Scope

Applies to:

* humans
* AI agents
* all branches
* all phases

This file defines repo-wide invariants only.
Task workflows, debug playbooks, deployment runbooks, and tool-specific procedures belong in `SKILL.md`, `docs/`, or CI config.

## 2. Product Boundaries

This repo is a catalog-first Stremio addon.
It discovers what is airing on Hungarian TV and exposes Stremio-compatible metadata.
It is not a streaming provider.

Hard constraints:

* FastAPI is the only HTTP server in this repo
* addon output must remain compatible with the Stremio addon protocol
* catalog and meta are supported product surfaces
* stream responses, if present, must remain intentionally non-streaming
* no piracy features
* no embedded or proxied video streams
* no user accounts, auth systems, or persistence layers unless explicitly approved
* no silent breaking changes to addon behavior or endpoint payloads

## 3. Architecture

One repo. One service. Clear module boundaries.

Current architecture:

* `src/main.py` owns HTTP app wiring and lifecycle
* `src/manifest.py` owns addon manifest data
* `src/catalog_handler.py` owns catalog orchestration
* `src/meta_handler.py` owns meta response orchestration
* `src/scraper.py` owns musor.tv fetch orchestration, rate limiting, retries, and scraper health
* `src/musor_parser.py` owns pure musor.tv HTML parsing and scraper normalization helpers
* `src/imdb_lookup.py` and `src/imdb_cache.py` own metadata enrichment and caching
* `src/time_window.py` owns time preset logic
* `src/models.py` owns typed models
* `src/utils.py` owns shared pure helpers

Rules:

* keep route wiring thin
* keep parsing and transformation logic out of endpoint decorators where practical
* scraper code must not leak transport concerns into domain formatting
* keep pure HTML parsing helpers outside transport and lifecycle orchestration
* cache layers must stay replaceable and isolated
* prefer pure functions for normalization, filtering, and time-window logic
* retries and circuit breakers are for external calls only
* `fetch_live_movies(force=False)` and `get_scraper()` are stable scraper integration points unless an explicit contract change is approved
* do not reintroduce browser-class scraping dependencies when plain HTTP and HTML parsing are sufficient unless an ADR approves it
* no new framework, queue, datastore, or background worker without an ADR

## 4. External Dependency Boundaries

External systems in this repo are:

* musor.tv
* TMDB API when configured
* Stremio clients consuming the addon

Rules:

* treat musor.tv HTML as unstable input
* treat musor.tv pages as server-rendered but structurally unstable and potentially different by path
* assume external selectors break over time
* rate-limit scraping and metadata lookups
* prefer direct HTTP fetch plus HTML parsing when the required data is present in initial HTML
* fail soft on external outages
* log enough context to debug external failures without leaking secrets
* distinguish transport failures from parse failures in logs
* do not hard-fail the whole app because one upstream call failed

## 5. API Contracts

Public HTTP responses are contracts.

Every endpoint must have:

* explicit request validation where input is non-trivial
* explicit response shape
* stable content types
* version-conscious changes

Rules:

* existing Stremio paths are part of the public contract
* do not rename or remove response fields without documenting the break
* do not make optional fields required without a versioning plan
* prefer additive changes over shape changes
* health endpoints must stay cheap and deterministic
* if root landing page behavior changes, keep addon install discovery intact

Breaking change examples:

* changing manifest capabilities incompatibly
* changing catalog item identifiers or field names
* changing meta response shape incompatibly
* turning empty stream responses into active streaming behavior

Breaking changes require:

* explicit user approval
* `CHANGELOG.md` update if that file exists or is added as part of the change
* migration notes in `README.md` or `docs/`

## 6. Time and Locale Rules

Time handling is a core business rule.

Hard constraints:

* `Europe/Budapest` is the canonical timezone
* all schedule calculations must use the configured Budapest timezone semantics
* midnight-boundary handling must remain covered by tests
* Hungarian text normalization must preserve accent-insensitive matching behavior

Rules:

* do not scatter ad hoc datetime parsing across modules
* centralize time-window logic in `src/time_window.py` or a dedicated time module
* pass normalized text through shared helpers, not copy-pasted logic

## 7. Scraper Rules

The scraper is the highest-churn area.

Rules:

* isolate selector assumptions in scraper code
* prefer resilient selectors and fallback selector groups
* keep scrape rate limiting in one place
* deduplicate concurrent scrape work where possible
* parser failures should log and continue where practical instead of aborting the full scrape
* transport lifecycle must be explicit
* shutdown must clean up HTTP client resources
* scraper failures must degrade to empty or partial safe responses, not crash loops

When changing scraper behavior:

* verify selector fallbacks
* verify midnight-boundary handling
* verify fixture-backed parser coverage stays realistic
* verify catalog output still matches expected Stremio fields
* document non-obvious selector assumptions in code comments near the selector

## 8. Metadata Enrichment Rules

IMDb and TMDB enrichment is optional augmentation, not the source of truth.

Rules:

* addon must still operate when TMDB credentials are absent
* cache success and failure states intentionally
* normalize lookup keys consistently
* do not block the main catalog path on slow metadata calls more than necessary
* treat match quality as probabilistic and code defensively
* never expose API secrets in logs, docs, or examples

## 9. Configuration

No hidden config.

Rules:

* config via environment variables
* `.env` is local-dev only
* production config must come from runtime environment
* code must define safe defaults only for non-secret optional settings
* secrets must never be committed

Current environment surface includes at least:

* `PORT`
* `TZ`
* `LOG_LEVEL`
* `CACHE_TTL_MIN`
* `SCRAPE_RATE_MS`
* `TMDB_API_KEY`
* `IMDB_LOOKUP_ENABLED`
* `IMDB_CACHE_TTL_DAYS`
* `IMDB_RATE_LIMIT_PER_SEC`
* `BASE_URL` if deployment needs canonical URL generation

Rules for changes:

* document every new env var in `README.md` and deployment config
* do not change semantic meaning of existing env vars silently
* prefer booleans and durations with explicit naming

## 10. Runtime

Rules:

* service must stay stateless
* service must run correctly in Docker
* service must expose `/healthz`
* process must exit non-zero on fatal startup failures
* lifecycle shutdown must release external resources cleanly
* scraper lifecycle must not depend on browser startup while the lightweight HTTP parser stack is the chosen implementation
* logging must go to stdout/stderr
* no `print()` in application code

## 11. Dependencies

Rules:

* dependencies must be explicitly declared
* do not add heavy dependencies for trivial problems
* prefer standard library when it keeps code clear
* pin or constrain dependencies intentionally
* prefer lightweight HTTP and HTML parsing dependencies over browser automation when they satisfy scraper needs
* upgrade external libraries with compatibility review, especially FastAPI, Pydantic, `httpx`, `selectolax`, and cache libraries

## 12. Testing

Test critical logic and contracts.

Must test when changed:

* time-window calculations
* midnight-boundary logic
* Hungarian text normalization
* scraper parsing with realistic HTML fixtures or equivalent focused coverage
* contract-sensitive endpoint behavior
* IMDb lookup normalization and cache behavior

Do not over-invest in:

* framework internals
* cosmetic landing page markup
* trivial passthrough wiring with no branching logic

Rules:

* tests live in `tests/`
* mirror source structure where practical
* every bug fix should add or update a regression test unless impossible
* scraper and parser tests should run deterministically offline with fixtures and mocks in normal CI
* if scraper selectors change, run the most relevant targeted tests

## 13. Documentation

Rules:

* `README.md` explains user-facing setup and behavior
* `docs/` holds design notes, incident writeups, and implementation details
* `AGENTS.md` holds only durable repo invariants
* create or update a project-specific `SKILL.md` when a recurring repo task, workflow, or debug playbook emerges and is likely to be reused
* docs must not instruct users to install Playwright or Chromium while the scraper stack is HTTP and HTML parser based
* do not leave stale docs after behavior changes
* no TODO without issue reference

## 14. Change Management

Before merging behavior changes, verify the full chain:

1. request shape and query parsing
2. handler orchestration
3. scraper or metadata dependency behavior
4. cache implications
5. output contract to Stremio clients
6. docs and env var updates
7. tests for the changed behavior

Do not guess when context is missing.
If endpoint behavior, Stremio compatibility, or scraper intent is unclear, stop and clarify.

## 15. AI Guardrails

Be concise. Prefer exactness over fluency.

AI may not invent:

* endpoints
* capabilities
* external integrations
* deployment guarantees
* supported Stremio behaviors

AI must:

* follow current repo structure
* preserve catalog-only product intent unless explicitly directed otherwise
* not convert optional enrichment into required infrastructure
* not claim a selector or upstream behavior is stable without evidence
* not guess when missing context would risk a wrong contract change
* use subagents when an agent is actively working on the repo and delegation materially helps progress
* capture recurring project-specific workflows in `SKILL.md` for future reuse instead of re-deriving them repeatedly
* update tests and docs with code changes when relevant
