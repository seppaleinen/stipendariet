### Added
- Bolagsverket registry lookup (Stage 0) in enrichment pipeline v2
- `BolagsverketClient` — async HTTP client for Swedish Companies Registration Office API with 1 req/sec rate limiting, exponential backoff retry (3 retries), optional Bearer token auth
- `BolagsverketStage` — pipeline stage that runs first, fetches authoritative data (legal name, address, status, registration date, legal form, SNI codes), constructs probable official website URL
- 18 new tests (10 unit + 8 integration) covering client, stage, and orchestrator integration
- Trace dict now includes `bolagsverket` key with full lookup result for audit/debugging

### Changed
- Pipeline now runs Bolagsverket lookup as Stage 0 (before Service Area)
- Discovery stage is skipped when `official_website` is found via Bolagsverket (saves 2–5 seconds per foundation)
- `PipelineContext` gains `bolagsverket_data` and `official_website` fields
- Orchestrator trace initialization includes `bolagsverket` key

### Configuration
- New env vars (all optional with defaults):
  - `BOLAGSVERKET_URL` — API base URL (default: `https://data.bolagsverket.se/api`)
  - `BOLAGSVERKET_API_KEY` — Optional OAuth 2.0 Bearer token (default: empty)
  - `BOLAGSVERKET_RATE_LIMIT` — Requests per second (default: `1.0`, per ToS 60/min)
  - `BOLAGSVERKET_MAX_RETRIES` — Max retry attempts (default: `3`)
  - `BOLAGSVERKET_TIMEOUT` — HTTP timeout seconds (default: `10.0`)

### Performance
- +1 second per foundation for Bolagsverket API call
- -2 to -5 seconds when Discovery stage skipped (net positive for foundations with orgnr)

### Notes
- No database schema changes — rollback by code revert only
- Bolagsverket API does not provide website URLs; probable URL constructed from legal name (`https://{slug}.se`)
- Graceful fallback: if orgnr missing or Bolagsverket returns no data, pipeline proceeds to normal Discovery flow