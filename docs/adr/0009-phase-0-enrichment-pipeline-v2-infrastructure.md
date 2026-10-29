# ADR 009: Phase 0 Enrichment Pipeline v2 Infrastructure

**Status:** Accepted

**Date:** 2026-10-29

---

## Context

The Foundation Enrichment Pipeline v2 (Issue #35 follow-up) requires new infrastructure components to support multi-source discovery, prompt versioning, and intelligent extraction. Phase 0 establishes the foundational infrastructure before implementing the seven subsequent phases.

The previous enrichment pipeline relied solely on DuckDuckGo for web search, had no prompt versioning capability, and lacked confidence scoring for extracted data.

---

## Decision

### 1. Self-Hosted Search: SearXNG

**Add SearXNG service** (`docker-compose.yml` port 8080) with configuration in `searxng/settings.yml`.

**Why SearXNG over DuckDuckGo-only:**
- **Multi-engine aggregation**: Queries Google, Bing, DuckDuckGo, and Brave simultaneously
- **Swedish language focus**: Default `sv` lang improves local foundation discovery
- **JSON output format**: Native JSON responses simplify pipeline integration
- **No rate limiting**: Self-hosted instance avoids API throttling
- **Privacy**: No tracking or query logging

**Trade-offs:**
- **Maintenance overhead**: One more service to monitor and update
- **Resource usage**: Additional container (~200MB RAM)
- **Configuration complexity**: Engine tuning required for optimal results

### 2. Prompt Versioning Infrastructure

**Add `enrichment_prompts` table** (Alembic migration `20261029_enrichment_prompts`) with Jinja2 templating (`jinja2>=3.1.0` in requirements).

**Why prompt versioning:**
- **A/B testing capability**: Run multiple prompt variants against live data
- **Rollback safety**: Revert to previous prompt version if metrics degrade
- **Metrics tracking**: Store performance data per version (`metrics` JSON column)
- **Template variables**: Jinja2 enables dynamic prompt construction without code changes

**Schema:**
- `name`: Unique identifier (e.g., "discovery_prompt_v1")
- `version`: Semantic version string
- `template`: Jinja2 template text
- `variables`: JSON default values for template variables
- `is_production`: Boolean flag for active version
- `metrics`: JSON storage for accuracy/latency metrics

**Trade-offs:**
- **Database complexity**: New table requires migration management
- **Template injection risk**: Jinja2 templates must be validated before execution
- **Version drift**: Multiple versions may diverge without governance

### 3. Confidence Field Support

**Update `ExtractedFoundationData`** (`backend/app/pipeline/extraction.py`) to include confidence scores on extracted fields.

**Why confidence fields:**
- **Multi-source merge intelligence**: Phase 4 will merge results from multiple search engines
- **Quality gating**: Filter low-confidence extractions before database write
- **Human review prioritization**: Surface low-confidence items for manual verification
- **Model comparison**: Compare confidence distributions across LLM models

**Trade-offs:**
- **Extraction latency**: Confidence calculation adds ~50-100ms per field
- **Threshold tuning**: Requires empirical calibration (no universal "good" threshold)

### 4. Browserless Made Optional

**Comment out browserless service** in `docker-compose.yml`. Enrichment worker can run headless Playwright locally or connect to remote browser if needed.

**Why optional:**
- **Reduced resource usage**: Browserless consumes ~500MB RAM idle
- **Flexibility**: Local Playwright sufficient for most foundations; browserless reserved for JavaScript-heavy sites
- **Cost control**: No always-on container if not needed

**Trade-offs:**
- **Manual configuration**: Must uncomment and set `BROWSERLESS_URL` if needed later
- **Fallback complexity**: Pipeline must handle missing browserless gracefully

### 5. Frontend Port Change

**Move frontend host port** from 8080 to 8082 (`docker-compose.yml` line 138). Internal container port remains 8080.

**Why:**
- SearXNG requires host port 8080 for its web interface
- Avoids port collision during local development

**Trade-offs:**
- **Breaking change**: Developers must update bookmarks from `localhost:8080` to `localhost:8082`
- **Documentation updates**: All references to frontend URL must be updated

---

## Consequences

### Positive

- **Multi-engine search**: 4x coverage for Swedish foundation discovery
- **Prompt iteration without deployment**: Update templates via database, not code
- **Data quality visibility**: Confidence scores enable intelligent filtering
- **Resource efficiency**: Browserless only when needed

### Negative

- **Port change breaks existing workflows**: Developers must update `localhost:8080` → `localhost:8082`
- **New service to maintain**: SearXNG requires monitoring and occasional engine tuning
- **Migration required**: `enrichment_prompts` table must be created before Phase 1

### Neutral

- **Jinja2 dependency**: Minimal overhead (~50KB), widely-used template engine
- **SearXNG configuration**: Default settings sufficient for initial phases; tuning comes later

---

## Related

- Issue #35: Foundation Enrichment Pipeline v2
- Files modified:
  - `docker-compose.yml` (SearXNG service, browserless optional, frontend port)
  - `searxng/settings.yml` (new file)
  - `backend/requirements.txt` (jinja2)
  - `backend/alembic/versions/20261029_enrichment_prompts.py` (new migration)
  - `backend/app/db/models/enrichment_prompts.py` (new model)
  - `backend/app/db/models/__init__.py` (model registration)
  - `backend/app/pipeline/extraction.py` (confidence fields)
  - `backend/app/core/config.py` (SEARXNG_URL setting)
