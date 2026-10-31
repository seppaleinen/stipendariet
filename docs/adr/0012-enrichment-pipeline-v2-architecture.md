# ADR 0012: Foundation Enrichment Pipeline v2 Architecture

## Status
Accepted

## Context

The Foundation Enrichment Pipeline v2 processes Swedish nonprofit foundations (from Bolagsverket registry) through a multi-stage extraction pipeline to produce structured data for the stipendariet assistant. Phase 7 adds observability and admin polish capabilities.

## Pipeline Stages

### Stage 0: Bolagsverket Registry Lookup
- **Purpose**: Authoritative foundation data from Swedish Companies Registration Office
- **Implementation**: `backend/app/services/bolagsverket_client.py`
- **Output**: Legal name, address, status, registration date, constructed probable website URL
- **Rate Limiting**: 1 req/sec via token-bucket, exponential backoff
- **Environment**: `BOLAGSVERKET_URL`, `BOLAGSVERKET_API_KEY`, `BOLAGSVERKET_RATE_LIMIT`

### Stage 1: SearXNG Multi-Engine Search (Discovery)
- **Purpose**: Find candidate URLs for foundation websites
- **Implementation**: `backend/app/pipeline/discovery.py` (`_searxng_search()`)
- **Engines**: 4 Swedish-focused search strategies (site:se, bidrag_ansokan, stipendium, kontakt)
- **DDG Fallback**: DuckDuckGo used when SearXNG returns < 3 candidates
- **Redis Cache**: SHA256 key, 7-day TTL for search results

### Stage 2: Validation
- **Purpose**: LLM-based validation that URLs are relevant to the foundation
- **Implementation**: `backend/app/pipeline/validation.py`
- **Output**: Matched candidates with confidence scores
- **Trace**: Validation steps stored with URL, title, snippet, confidence, raw LLM response

### Stage 3: Trafilatura-First Crawl
- **Purpose**: Extract structured content from candidate URLs
- **Implementation**: `backend/app/pipeline/crawl.py`
- **Primary**: Trafilatura library for markdown extraction
- **Playwright Fallback**: When Trafilatura fails
- **Simhash Dedup**: Duplicate page detection across sources
- **Output**: `EnrichmentPage` records with raw markdown content

### Stage 4: Per-Source Extraction + Confidence Merge
- **Purpose**: Extract 8 fields from crawled content
- **Implementation**: `backend/app/pipeline/extraction.py`
- **LLM**: `gemma-4-12b` via LiteLLM proxy
- **Output Fields**:
  - `contact_email`
  - `contact_phone`
  - `application_open`
  - `application_deadline`
  - `who_can_apply`
  - `how_to_apply`
  - `notes`
  - `enriched_description`
- **Per-Request Tracking**: `source_per_field`, `per_field_confidence`

### Stage 5: Targeted Re-Search (Phase 6 Extension)
- **Purpose**: Fill missing fields via targeted queries
- **Implementation**: `backend/app/pipeline/orchestrator.py`
- **Max Iterations**: 2
- **Gap Analysis**: `missing_fields = [f for f in REQUIRED_FIELDS if not merged_data.get(f)]`
- **Targeted Queries**: Field-specific search strings (e.g. "foundation_name kontakt e-post")
- **Merge Strategy**: Fill only missing fields, preserve existing high-confidence values

### Stage 6: Service Area Extraction
- **Purpose**: Geographic service area from foundation name/purpose
- **Implementation**: `backend/app/pipeline/service_area.py`
- **LLM**: Structured JSON output
- **Output**: Region list at county/municipality level

## Rationale

### Why Multi-Stage?

Each stage has distinct concerns:
1. **Discovery** finds candidates
2. **Validation** ensures relevance
3. **Crawl** extracts content
4. **Extraction** parses fields

This separation allows:
- Independent testing of each stage
- Clear audit trails for debugging
- Graceful degradation (skip expensive stages when possible)

### Why Trafilatura-First?

Trafilatura provides:
- High-quality text extraction
- Metadata preservation
- Fast processing (no browser overhead)

Playwright fallback handles JavaScript-heavy sites where Trafilatura fails.

### Why Confidence-Based Merging?

Web scraping yields varying quality. Per-field confidence:
- Tracks extraction quality per field
- Enables targeted re-search (Phase 6)
- Provides observability for admin dashboard

## Key Decisions

| Decision | Location | Rationale |
|----------|----------|-----------|
| SearXNG as primary search | `pipeline/discovery.py` | Better coverage, self-hosted, no API cost |
| Trafilatura-first crawl | `pipeline/crawl.py` | Fast text extraction, Playwright fallback |
| Highest-confidence-wins merge | `pipeline/extraction.py` | Simple, deterministic |
| Redis caching for search | `pipeline/discovery.py` | Avoids rate limits, improves performance |
| Phase 0 Bolagsverket lookup | `pipeline/bolagsverket.py` | Skip search when official site known |

## Implementation Details (Phase 7 Additions)

### Field Completeness Dashboard
- **Endpoint**: `GET /admin/enrich/field-completeness`
- **Logic**: Query `EnrichmentData` records grouped by day, calculate fill rates per field
- **Metric**: Ratio of foundations with ≥5/8 fields

### Prompt Metrics Endpoint
- **Endpoint**: `GET /admin/enrich/prompt-metrics`
- **Source**: `EnrichmentPrompt.metrics` JSON column
- **Metrics**: `avg_confidence`, `field_completeness`, `runs_count`

### Data Export
- **Endpoint**: `POST /admin/enrich/export`
- **Formats**: CSV, JSON
- **Filters**: Optional foundation IDs whitelist

### Admin UI Enhancements
- Per-field source URL display
- Per-field confidence scores
- "View Trace" modal with full pipeline execution

## Rollout Plan

1. **Deploy** new endpoints and UI
2. **Monitor** field completeness dashboard
3. **Verify** prompt metrics accuracy
4. **Document** admin usage via user guide

## Rollback Plan

- Revert code deployment
- No database migrations required (new columns nullable)
- Trace column populated from existing `_trace` in extracted_data via migration if needed

## Future Considerations

- Prompt version management UI
- Automated re-enrichment scheduling
- Export scheduling (daily/weekly reports)