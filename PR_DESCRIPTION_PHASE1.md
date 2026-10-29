## Summary
Adds Bolagsverket (Swedish Companies Registration Office) registry lookup as Stage 0 of the enrichment pipeline v2. Every foundation has an orgnr; use it to fetch authoritative data (legal name, address, status, representatives) before searching the web. Skips Discovery stage when official website found.

## Changes

### New Files
- `backend/app/services/bolagsverket_client.py` — Async HTTP client with rate limiting (1 req/sec), exponential backoff retry (3 retries), optional Bearer auth, structured response parsing
- `backend/app/pipeline/bolagsverket.py` — PipelineStage implementation; constructs probable official_website from legal name; outputs bolagsverket_data, official_website, trace
- `backend/tests/test_bolagsverket_client.py` — 10 unit tests (success, 404, invalid orgnr, rate limiting, retry/backoff, 429 Retry-After, auth header, no auth, timeout config, missing fields)
- `backend/tests/test_pipeline_bolagsverket.py` — 8 integration tests (stage run success, no orgnr, not found, trace fields, discovery skip logic, orchestrator injection, slugify, construct_probable_website)

### Modified Files
- `backend/app/core/config.py` — Added 5 Bolagsverket env var settings (BOLAGSVERKET_URL, BOLAGSVERKET_API_KEY, BOLAGSVERKET_RATE_LIMIT, BOLAGSVERKET_MAX_RETRIES, BOLAGSVERKET_TIMEOUT)
- `backend/app/pipeline/base.py` — PipelineContext: added bolagsverket_data (dict | None), official_website (str | None)
- `backend/app/pipeline/orchestrator.py` — Added BolagsverketStage import; _get_default_stages() includes bolagsverket as Stage 0; trace dict includes bolagsverket key; Stage 0 executes before service_area; Discovery skipped when official_website set
- `backend/tests/test_pipeline_abstraction.py` — STAGE_KEYS includes "bolagsverket"; added BolagsverketStage import and parametrized test; _make_stub_stages() includes bolagsverket stub that simulates finding official website

## Testing
- All 327 backend tests pass (including 18 new tests)
- Unit tests cover: successful lookup, 404 handling, invalid orgnr format, rate limiting enforcement, exponential backoff retry, 429 Retry-After header respect, Bearer auth header, timeout configuration, missing field handling
- Integration tests cover: stage execution with mocked client, missing orgnr handling, 404/not found handling, trace dict completeness, discovery skip logic verification, orchestrator stage injection, helper functions (slugify, website construction)
- No schema changes — no migration needed

## Configuration
5 new environment variables (all optional with sensible defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `BOLAGSVERKET_URL` | `https://data.bolagsverket.se/api` | API base URL |
| `BOLAGSVERKET_API_KEY` | `""` | Optional OAuth 2.0 Bearer token for production |
| `BOLAGSVERKET_RATE_LIMIT` | `1.0` | Requests per second (Bolagsverket ToS: 60/min) |
| `BOLAGSVERKET_MAX_RETRIES` | `3` | Max retry attempts with exponential backoff |
| `BOLAGSVERKET_TIMEOUT` | `10.0` | HTTP request timeout in seconds |

## Performance
- **+1 second** per foundation when Bolagsverket lookup runs (network call + rate limit)
- **-2 to -5 seconds** per foundation when Discovery stage is skipped (no search API calls)
- **Net benefit** for foundations with valid orgnr (vast majority)

## Rollback
No database migrations or schema changes. To rollback:
1. Revert code deployment (git revert or deploy previous image)
2. No manual steps required

## Related
- ADR: `docs/adr/0010-phase1-bolagsverket-registry-lookup.md`
- Phase 0 ADR: `docs/adr/0009-phase-0-enrichment-pipeline-v2-infrastructure.md`
- Contract: `.harness/contracts/phase1-bolagsverket-stage0.md`