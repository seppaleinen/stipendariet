# ADR 0010: Bolagsverket Registry Lookup as Pipeline Stage 0

## Status
Accepted

## Context
The Foundation Enrichment Pipeline v2 previously relied solely on web search (DuckDuckGo/SearXNG) to discover foundation websites. This approach was slow (2–5 seconds per foundation) and unreliable for Swedish foundations, which all have a registered organisationsnummer (orgnr) with the Swedish Companies Registration Office (Bolagsverket).

Every foundation in our database has an orgnr. By querying the authoritative Bolagsverket register first, we can:
- Get verified legal name, address, status, registration date, and legal form
- Construct a probable official website URL from the legal name
- Skip the Discovery stage entirely when an official website is found, saving 2–5 seconds per foundation
- Improve data quality with authoritative source data before any web search

The Bolagsverket API (https://data.bolagsverket.se/api) is free (60 req/min = 1 req/sec), requires optional OAuth 2.0 Bearer token for production, and returns JSON. The API does NOT include website URLs — we construct a probable one from the legal name.

## Decision
Implement Bolagsverket registry lookup as Stage 0 of the enrichment pipeline:

1. **New `BolagsverketClient`** (`backend/app/services/bolagsverket_client.py`):
   - Async HTTP client using `httpx`
   - Rate limiting: 1 req/sec via `asyncio.Lock` + `time.monotonic()`
   - Exponential backoff retry (2^attempt seconds), max 3 retries by default
   - Respects `Retry-After` header on 429 responses
   - Optional Bearer token auth via `BOLAGSVERKET_API_KEY`
   - Returns structured dict with legal_name, address, status, registration_date, legal_form, sni_codes, raw_response
   - Returns `None` on 404 (not found) or invalid orgnr — not an error

2. **New `BolagsverketStage`** (`backend/app/pipeline/bolagsverket.py`):
   - Implements `PipelineStage` interface, runs first in pipeline
   - Outputs: `ctx.bolagsverket_data` (structured dict), `ctx.official_website` (constructed probable URL), `ctx.trace["bolagsverket"]`
   - Constructs probable website: `https://{slugified-legal-name}.se`

3. **PipelineContext updates** (`backend/app/pipeline/base.py`):
   - Added `bolagsverket_data: dict | None`
   - Added `official_website: str | None`

4. **Orchestrator updates** (`backend/app/pipeline/orchestrator.py`):
   - Stage 0 executes before Service Area stage
   - If `ctx.official_website` is set, Discovery stage is skipped and candidate_urls is set directly to the official website
   - Trace includes `bolagsverket` key with full lookup result

5. **Configuration** (5 new env vars in `backend/app/core/config.py`):
   - `BOLAGSVERKET_URL` (default: https://data.bolagsverket.se/api)
   - `BOLAGSVERKET_API_KEY` (default: empty, optional)
   - `BOLAGSVERKET_RATE_LIMIT` (default: 1.0 req/sec)
   - `BOLAGSVERKET_MAX_RETRIES` (default: 3)
   - `BOLAGSVERKET_TIMEOUT` (default: 10.0 seconds)

6. **Testing**: 18 new tests (10 unit in `test_bolagsverket_client.py`, 8 integration in `test_pipeline_bolagsverket.py`)

## Consequences

### Positive
- **Authoritative data first**: Legal name, address, status from official Swedish register
- **Performance gain**: ~2–5 seconds saved per foundation when Discovery is skipped (net benefit even with +1 sec Bolagsverket call)
- **Higher quality**: Reduces reliance on web search for basic identity data
- **Audit trail**: Full Bolagsverket response stored in trace for debugging
- **Graceful degradation**: If Bolagsverket fails or orgnr missing, pipeline falls back to normal Discovery flow

### Negative
- **Added latency**: +1 second per foundation when Bolagsverket is called (mitigated by async, rate limiting)
- **New external dependency**: Bolagsverket API availability affects pipeline (but 404/errors fall back gracefully)
- **5 new configuration variables**: Must be documented and set in deployment

### Neutral
- No database schema changes — all data stored in existing trace JSON column
- No breaking changes to API contracts
- Rollback is simple: revert code deployment (no migrations needed)