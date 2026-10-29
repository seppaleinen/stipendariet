# Enrichment Pipeline v2 — Developer Notes (Phase 0)

**Status:** Phase 0 (Infrastructure & Prereqs) complete ✅
**Next:** Phase 1 — Stage 0: Bolagsverket Registry Lookup

Phase 0 added the infrastructure prerequisites for the enrichment pipeline v2 refactor
(see `.harness/research-brief-enrichment-pipeline-v2.md`). No user-facing changes.

## What Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | SearXNG service on host port 8080; browserless commented out (optional); frontend host port 8080 → 8082 |
| `searxng/settings.yml` | NEW — SearXNG config: google, bing, duckduckgo, brave engines; `sv` default lang; html + json formats |
| `backend/requirements.txt` | `jinja2>=3.1.0` added |
| `backend/alembic/versions/20261029_enrichment_prompts.py` | NEW migration — creates `enrichment_prompts` table |
| `backend/app/db/models/enrichment_prompts.py` | NEW `EnrichmentPrompt` model (registered in `db/models/__init__.py`) |
| `backend/app/pipeline/extraction.py` | `ExtractedFoundationData` gained `confidence: float = 0.0` and `per_field_confidence: dict[str, float] = {}` |
| `backend/app/core/config.py` | `SEARXNG_URL` setting (default `http://searxng:8080`) |

## Local Setup

```bash
# 1. Start infra (postgres, redis, searxng)
docker compose up -d postgres redis searxng

# 2. Verify SearXNG
curl "http://localhost:8080/search?q=stiftelser&format=json"
# or open the web UI: http://localhost:8080

# 3. Apply the new migration
cd backend && alembic upgrade head

# 4. Verify the table
psql -U postgres -d stipendariet -c "\d enrichment_prompts"

# 5. Tests + lint
python3 -m pytest tests/ -q
ruff check .
```

## Notes

- **Port map:** SearXNG `localhost:8080`, frontend `localhost:8082` (was 8080), admin `localhost:8081`.
- **Browserless is optional now.** The compose service is commented out. `crawler.py`
  falls back to a local headless Chromium launch if it can't reach a browserless CDP
  endpoint. To re-enable, uncomment the `browserless` block in `docker-compose.yml` and
  set `BROWSERLESS_URL` on the worker.
- **SearXNG is dev-only as committed:** `settings.yml` has `limiter: false` and an empty
  `secret_key` — fine for local dev, do not expose to a network beyond that.
- **Jinja2 SSTI (Phase 5 prerequisite):** when `PromptService` renders DB-stored
  templates, render in a `SandboxedEnvironment` (templates will be admin-authored but
  must not allow `__import__`/`getattr`-style escapes).
- **Confidence fields are declared but not yet populated.** The extraction prompt does
  not ask the LLM for confidence (Phase 4 adds per-source extraction + merge). The
  defaults (`0.0` / `{}`) keep all existing serialization working.

## Phase Roadmap (from research brief)

| Phase | Scope |
|-------|-------|
| 0 | ✅ Infrastructure & Prereqs (this) |
| 1 | Stage 0: Bolagsverket registry lookup (`BolagsverketClient`, `BolagsverketStage`) |
| 2 | Search upgrade: SearXNG client, DDG fallback, Redis caching |
| 3 | Crawl refactor: trafilatura-first, Playwright fallback, dedup |
| 4 | Per-source extraction + confidence scoring + merge |
| 5 | Prompt versioning: Jinja2 templates, `PromptService`, admin UI |
| 6 | Targeted re-search for missing fields (max 2 iterations) |
| 7 | Observability & admin polish |

## Related

- ADR: [`docs/adr/0009-phase-0-enrichment-pipeline-v2-infrastructure.md`](adr/0009-phase-0-enrichment-pipeline-v2-infrastructure.md)
- Research brief: `.harness/research-brief-enrichment-pipeline-v2.md`
