# ADR 0011: SearXNG Multi-Engine Search as Primary Discovery

## Status
Accepted

## Context
The enrichment pipeline Discovery stage used only DuckDuckGo for candidate URL discovery. DDG has aggressive rate limiting, lower coverage for Swedish foundations, and no caching. Phase 0 provisioned a self-hosted SearXNG instance with four engines (Google, Bing, DuckDuckGo, Brave). Phase 2 connects the pipeline to SearXNG as the primary search engine, with DDG retained as fallback.

## Decision
Replace DDG-only discovery with SearXNG multi-engine search, with the following components:

1. **SearXNGClient** — Async HTTP client with rate limiting (1 req/sec), exponential backoff retry (3 attempts), engine selection, and structured result parsing.

2. **Shared RateLimiter** — Extracted `RateLimiter` class shared between `BolagsverketClient` and `SearXNGClient`. Token-bucket style with minimum interval enforcement via `asyncio.Lock`.

3. **Discovery refactored** — `_searxng_search()` with Redis caching (7-day TTL, SHA256 key). Four Swedish-focused search strategies (site:se, bidrag_ansokan, stipendium, kontakt). DDG fallback when SearXNG returns < 3 candidates or fails.

4. **Configuration** — Five new environment variables: `SEARXNG_URL`, `SEARXNG_RATE_LIMIT`, `SEARXNG_TIMEOUT`, `SEARXNG_MAX_RETRIES`, `SEARXNG_ENGINES`.

## Consequences

### Positive
- Higher candidate URL coverage via four search engines instead of one
- Redis caching eliminates repeated external API calls for identical queries
- Graceful degradation: DDG fallback when SearXNG is unavailable
- Shared rate limiter reduces code duplication between service clients
- Zero external API cost (self-hosted SearXNG, free DDG fallback)

### Negative
- New self-hosted dependency (SearXNG container must be running)
- Cache storage overhead in Redis (negligible at current scale)
- Up to 4 search strategies per foundation (mitigated by max_urls early termination and caching)

### Neutral
- No database schema changes
- No breaking changes to pipeline interface
- DDG library retained as fallback (no new dependencies)
- Rollback: simple code revert
