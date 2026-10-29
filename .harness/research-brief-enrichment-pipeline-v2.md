# Research Brief: Foundation Enrichment Pipeline v2

**Task:** Improve foundation data enrichment pipeline for higher field completeness
**Domain:** Backend (enrichment pipeline, search, crawl, extraction)
**Date:** 2026-10-29
**Issue:** Follow-up to Issue #35 post-mortem — foundation data extraction needs improvement

---

## Executive Summary

**Goal:** Increase field completeness from ~30% to 85% of foundations with ≥5/8 extracted fields.

**Root Causes Identified:**
1. Single search engine (DDG) misses many Swedish foundation websites
2. No official registry lookup (Bolagsverket) despite having orgnr for every foundation
3. Single-shot extraction with no retry for missing fields
4. No per-source confidence scoring — can't merge intelligently
5. Browserless dependency makes crawl brittle and slow
6. Static prompts with no versioning or A/B testing

**Solution:** 7-phase refactoring of the enrichment pipeline with:
- Bolagsverket registry lookup (Stage 0)
- SearXNG self-hosted search (multi-engine)
- Trafilatura-first crawl (Playwright fallback)
- Per-source extraction + confidence merge
- Prompt versioning in DB + Jinja2 templates
- Targeted re-search for missing fields

**Budget:** $0/month (all self-hosted/free tiers)
**Estimated Effort:** 13-17 dev-days total

---

## 1. Current State Analysis

### 1.1 Pipeline Architecture (Current)

```
┌─────────────────────────────────────────────────────────────┐
│              CURRENT ENRICHMENT PIPELINE                     │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Discovery (DDG only)  ──→ 7 candidate URLs        │
│       ↓                                                      │
│  Stage 2: Validation (LLM only)  ──→ is_match, confidence   │
│       ↓                                                      │
│  Stage 3: Crawl (Playwright only)  ──→ 5 subpages           │
│       ↓                                                      │
│  Stage 4: Extraction (single-shot)  ──→ 8 fields            │
│       ↓                                                      │
│  Stage 5: Service Area (LLM)  ──→ county/municipality codes │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Field Completeness (Current Baseline)

| Field | Current Fill Rate |
|-------|-------------------|
| `contact_email` | ~25% |
| `contact_phone` | ~15% |
| `application_open` | ~20% |
| `application_deadline` | ~30% |
| `who_can_apply` | ~40% |
| `how_to_apply` | ~35% |
| `notes` | ~50% |
| `enriched_description` | ~45% |
| **≥5/8 fields** | **~30%** |

### 1.3 Code Smells by Area

#### HIGH PRIORITY

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/pipeline/discovery.py:49-115` | Only DDG via `ddgs` library — no official registry lookup | Misses authoritative data sources; DDG rate-limits aggressively |
| `backend/app/pipeline/discovery.py:33-35` | `_ddgs_search()` has no caching, no retry, no fallback | Repeated searches for same foundation; fragile on rate limits |
| `backend/app/pipeline/crawler.py:14-71` | Playwright-only crawl with browserless hard dependency | Heavy, slow, brittle — browserless container is single point of failure |
| `backend/app/pipeline/extraction.py:25-67` | Single-shot extraction, 6000 char truncation, no retry | Loses data when content >6000 chars; no recovery on partial extraction |
| `backend/app/pipeline/extraction.py:12-20` | `ExtractedFoundationData` has no confidence field | Can't score or merge multiple sources intelligently |
| `backend/app/pipeline/orchestrator.py:138-360` | Concatenates all crawled content before extraction | Blends good + bad sources; can't trace field to source |
| `backend/app/pipeline/prompts.py:1-111` | Static module-level constants, no versioning | Can't A/B test prompts; no rollback on bad changes |
| `backend/app/core/config.py:41-42` | `BROWSERLESS_URL` is required dep | Can't run pipeline without browserless container |

#### MEDIUM PRIORITY

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/foundation/sync_service.py:292-466` | `sync_foundations()` doesn't use enrichment pipeline | Two separate data ingestion paths; confusing |
| `backend/app/services/scraper_service.py:64-119` | `trafilatura` + `browserless` as parallel options, not fallback | Doesn't try lightweight option first |
| `backend/app/pipeline/validation.py:12-55` | LLM-only validation — no structural heuristics | Wastes LLM calls on obviously-bad URLs |
| `backend/app/api/v1/routers/admin/enrichment.py:424-442` | Admin can override prompts per-run, but no persistence | Can't track what prompt versions work best |
| `backend/app/db/models/enrichment.py:43-55` | `EnrichmentData.extracted_data` is raw JSON, no confidence | Can't audit which source contributed which field |

#### LOW PRIORITY

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/pipeline/service_area.py:139-247` | Service area extraction is solid, but runs even when no geo restriction | Wastes LLM call; could short-circuit on foundation name analysis |
| `backend/app/pipeline/base.py:7-46` | `PipelineContext` has no `bolagsverket_data` field | Can't pass registry data through stages |
| `apps/admin/src/pages/EnrichmentResultsPage.tsx:480-625` | Results page shows status but no per-field confidence | Can't identify low-confidence extractions for review |

---

## 2. Target Architecture

### 2.1 Pipeline v2 Structure

```
┌─────────────────────────────────────────────────────────────┐
│              ENRICHMENT PIPELINE v2                          │
├─────────────────────────────────────────────────────────────┤
│  Stage 0: BolagsverketLookup  ──→ legal address, website    │
│       ↓ (skip Discovery if website found)                   │
│  Stage 1: Discovery (SearXNG + DDG fallback)  ──→ candidates│
│       ↓                                                      │
│  Stage 2: Validation (LLM + structural heuristics) ──→ OK   │
│       ↓                                                      │
│  Stage 3: Crawl (Trafilatura → Playwright fallback)         │
│       ↓                                                      │
│  Stage 4: Per-Source Extraction (LLM + confidence)          │
│       ↓                                                      │
│  Stage 5: Merge (highest confidence wins per field)         │
│       ↓                                                      │
│  Stage 6: Gap Analysis + Targeted Re-Search (max 2 iter)    │
│       ↓                                                      │
│  Stage 7: Service Area (unchanged)                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **Stage 0: Registry** | Official data lookup by orgnr | Bolagsverket API call |
| **Stage 1: Discovery** | Multi-engine search, caching | SearXNG (Google/Bing/DDG), DDG fallback |
| **Stage 2: Validation** | URL quality gate | Structural heuristics + LLM |
| **Stage 3: Crawl** | Content extraction | Trafilatura (fast), Playwright (JS fallback) |
| **Stage 4: Extraction** | Per-source field extraction | LLM with confidence scoring |
| **Stage 5: Merge** | Intelligent field merge | Highest-confidence-wins per field |
| **Stage 6: Re-Search** | Targeted missing field recovery | Field-specific queries |
| **Stage 7: Service Area** | Geographic classification | Unchanged from current |

### 2.3 New Components

| Component | File | Purpose |
|-----------|------|---------|
| `BolagsverketClient` | `backend/app/services/bolagsverket_client.py` | API client for Swedish company registry |
| `BolagsverketStage` | `backend/app/pipeline/bolagsverket.py` | Pipeline stage for registry lookup |
| `SearXNGClient` | `backend/app/services/searxng_client.py` | Self-hosted search engine client |
| `extract_from_source()` | `backend/app/pipeline/extraction.py` | Per-source extraction with confidence |
| `merge_extractions()` | `backend/app/pipeline/extraction.py` | Merge multiple extractions by confidence |
| `enrichment_prompts` table | `alembic/versions/` | Prompt versioning schema |
| Jinja2 templates | `backend/app/pipeline/prompts/` | Templated prompts (validation.j2, extraction.j2, etc.) |

### 2.4 Infrastructure Changes

| Component | Current | Target |
|-----------|---------|--------|
| Search | DDG only (`ddgs` lib) | SearXNG (self-hosted) + DDG fallback |
| Crawl | Playwright + browserless (required) | Trafilatura-first, Playwright optional |
| Prompts | Module constants | DB versioning + Jinja2 templates |
| Registry | None | Bolagsverket API (free) |
| Docker Compose | `browserless` required | `searxng` added, `browserless` optional |

---

## 3. Phased Implementation Plan

### Phase 0 — Infrastructure & Prereqs (1-2 days)

**Goal:** Set up self-hosted search and prompt versioning infrastructure.

**Scope:**
- Add SearXNG to `docker-compose.yml` + k8s chart
- Add Bolagsverket client to `requirements.txt`
- Add Jinja2 to `requirements.txt`
- Create `enrichment_prompts` table migration
- Add `confidence` field to `ExtractedFoundationData`

**Deliverables:**
- `docker-compose.yml` — SearXNG service
- `backend/app/services/bolagsverket_client.py` — NEW
- `backend/app/db/models/enrichment_prompts.py` — NEW
- `alembic/versions/YYYYMMDD_enrichment_prompts.py` — NEW
- `backend/app/pipeline/extraction.py` — `ExtractedFoundationData` updated with `confidence: float` + `per_field_confidence: dict`

**Definition of Done:**
- [x] SearXNG running locally (`docker compose up searxng`)
- [x] `enrichment_prompts` table exists with migration
- [x] `ExtractedFoundationData` has confidence fields
- [x] Jinja2 installed and importable
- [x] All existing tests pass

**Estimated Effort:** 1-2 dev-days

> **STATUS: Phase 0 COMPLETE (2026-10-29)**
> - SearXNG service in `docker-compose.yml` (host port 8080) + `searxng/settings.yml` (google/bing/duckduckgo/brave, `sv` default, html+json formats).
> - `jinja2>=3.1.0` in `backend/requirements.txt`.
> - Migration `backend/alembic/versions/20261029_enrichment_prompts.py` (revision `20261029_enrichment_prompts` → `2026_09_02_000001`) + model `backend/app/db/models/enrichment_prompts.py` (`EnrichmentPrompt`, registered in `db/models/__init__.py`).
> - `ExtractedFoundationData` gained `confidence: float = 0.0` + `per_field_confidence: dict[str, float] = {}` (declared, not yet populated — Phase 4 wires the extraction prompt).
> - `SEARXNG_URL` config setting added; enrichment-worker gets `SEARXNG_URL=http://searxng:8080`.
> - **Deviations from brief:** (1) host port 8080 is already used by `frontend`, so frontend moved to host port 8082 (container port unchanged); (2) `bolagsverket_client.py` intentionally NOT created here — it uses only the existing `httpx` dep and is built in Phase 1 (per Phase 0 scope "client to requirements.txt" — nothing to add); (3) `SEARXNG_BASE_URL` in compose points at `http://searxng:8080/` (container-resolvable) per security review.
> - Verified: 308 passed / 6 skipped pytest, `ruff check backend/` clean, `docker compose config` valid, Jinja2 3.1.6 importable.
> - Docs: `docs/adr/0009-phase-0-enrichment-pipeline-v2-infrastructure.md`, `docs/enrichment-pipeline-phase0.md`, `PR_DESCRIPTION_PHASE0.md`.

---

### Phase 1 — Stage 0: Bolagsverket Registry Lookup (2-3 days)

**Goal:** Add official registry lookup as first pipeline stage.

**Scope:**
- Implement `lookup_foundation_by_orgnr(orgnr)` → legal name, address, status, reps
- Add `BolagsverketStage` as first pipeline stage
- Populate `PipelineContext` with `bolagsverket_data`
- Use address to construct probable website URL
- Skip Discovery if Bolagsverket returns website

**Deliverables:**
- `backend/app/services/bolagsverket_client.py` — `BolagsverketClient` class with:
  - `lookup_by_orgnr(orgnr: str) → dict | None`
  - Rate limiting (1 req/sec, per Bolagsverket terms)
  - Retry with exponential backoff
- `backend/app/pipeline/bolagsverket.py` — `BolagsverketStage(PipelineStage)`:
  - `name = "bolagsverket"`
  - `async run(ctx: PipelineContext) → None`
  - Sets `ctx.bolagsverket_data`, `ctx.official_website`
- `backend/app/pipeline/base.py` — `PipelineContext` updated:
  - `bolagsverket_data: dict | None = None`
  - `official_website: str | None = None`
- `backend/app/pipeline/orchestrator.py` — updated to:
  - Run Stage 0 first
  - Skip Stage 1 (Discovery) if `ctx.official_website` is set

**Definition of Done:**
- [x] `BolagsverketStage` exists and implements `PipelineStage`
- [x] Orchestrator runs Stage 0, skips Discovery on official website found
- [x] Rate limiting enforced (1 req/sec)
- [x] Tests pass (mocked Bolagsverket API)
- [x] Trace includes Bolagsverket result

**Estimated Effort:** 2-3 dev-days

> **STATUS: Phase 1 COMPLETE (2026-10-29)**
> - `BolagsverketClient` implemented with rate limiting (1 req/sec), exponential backoff retry (3 attempts), optional Bearer auth
> - `BolagsverketStage` implemented as Stage 0, runs before service_area
> - `PipelineContext` extended with `bolagsverket_data` and `official_website`
> - Orchestrator updated: runs Stage 0 first, skips Discovery when `official_website` set, adds trace entry
> - 5 new config settings: `BOLAGSVERKET_URL`, `BOLAGSVERKET_API_KEY`, `BOLAGSVERKET_RATE_LIMIT`, `BOLAGSVERKET_MAX_RETRIES`, `BOLAGSVERKET_TIMEOUT`
> - All 327 backend tests pass, `ruff check backend/` clean
> - New tests: `test_bolagsverket_client.py` (10 unit), `test_pipeline_bolagsverket.py` (8 integration), updated `test_pipeline_abstraction.py`
> - Docs: ADR `docs/adr/0010-phase1-bolagsverket-registry-lookup.md`, `PR_DESCRIPTION_PHASE1.md`, `CHANGELOG_PHASE1.md`
> - Security audit: [SUCCESS] — no critical/high vulnerabilities
> - Code review: [SUCCESS] — spec-complete, quality gates passed
> - Simplicity audit: [SUCCESS] — advisory findings only, no Critical blockers

---

### Phase 2 — Search Upgrade: SearXNG + Multi-Engine (2-3 days)

**Goal:** Replace DDG-only with SearXNG multi-engine search.

**Scope:**
- Deploy SearXNG container (Google + Bing + DDG + Brave engines enabled)
- Replace `_ddgs_search()` with `searxng_search(query, engines=[...])`
- Add search result caching (Redis, 7-day TTL)
- Keep DDG as fallback if SearXNG fails
- Add structured search strategies

**Deliverables:**
- `docker-compose.yml` — SearXNG service:
  ```yaml
  searxng:
    image: searxng/searxng:latest
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080
    volumes:
      - ./searxng/settings.yml:/etc/searxng/settings.yml
    ports:
      - "8080:8080"
  ```
- `backend/app/services/searxng_client.py` — NEW:
  - `SearXNGClient` class
  - `search(query: str, engines: list[str], max_results: int) → list[dict]`
  - Rate limiting + retry
- `backend/app/pipeline/discovery.py` — refactored:
  - `_searxng_search()` replaces `_ddgs_search()`
  - `_ddgs_search()` kept as fallback
  - Search strategies: `"foundation_name orgnr site:se"`, `"foundation_name bidrag ansökan"`
- Redis caching:
  - `cache_key = hash(foundation_name + orgnr + strategy)`
  - TTL: 7 days

**Definition of Done:**
- [ ] SearXNG running in docker-compose
- [ ] Discovery uses SearXNG first, DDG fallback
- [ ] Search results cached in Redis
- [ ] All existing tests pass
- [ ] Candidate URL quality (validation pass rate) ≥ current

**Estimated Effort:** 2-3 dev-days

---

### Phase 3 — Crawl Refactor: Trafilatura-First (2-3 days)

**Goal:** Make crawl faster and less brittle by trying trafilatura first.

**Scope:**
- New `crawl_with_trafilatura(url)` → markdown content
- `crawl_foundation_site()` tries trafilatura first; on failure/low-content → Playwright
- Remove `browserless` from required deps (make optional)
- Add content deduplication (simhash or embedding similarity)
- Add `robots.txt` check + polite delay (1s between requests)

**Deliverables:**
- `backend/app/pipeline/crawler.py` — refactored:
  - `crawl_with_trafilatura(url: str) → dict | None` — NEW
  - `crawl_foundation_site(url: str) → list[dict]` — updated:
    - Try trafilatura first
    - On failure or content <500 chars → Playwright fallback
    - Return `[{"url", "markdown", "type", "content_hash", "source": "trafilatura|playwright"}]`
- `backend/app/utils/content_dedup.py` — NEW:
  - `compute_content_hash(content: str) → str` (simhash or embedding-based)
  - `deduplicate_pages(pages: list[dict]) → list[dict]`
- `docker-compose.yml` — `browserless` service moved to optional section (commented out by default)
- `backend/requirements.txt` — `playwright` marked as optional (comment: "Only needed for JS-heavy sites")

**Definition of Done:**
- [ ] Trafilatura-first crawl implemented
- [ ] Content deduplication working
- [ ] `browserless` optional (pipeline runs without it)
- [ ] Tests pass (mocked crawl)
- [ ] Crawl latency ↓ (target: 45s avg vs 60s current)

**Estimated Effort:** 2-3 dev-days

---

### Phase 4 — Per-Source Extraction + Confidence Scoring (3-4 days)

**Goal:** Extract from each source independently, merge by confidence.

**Scope:**
- Refactor `extract_data_from_content()` → `extract_from_source(content, url, foundation_name, prompts)`
- Run extraction **per validated source** (not concatenated)
- Add field-level confidence: LLM returns `{"contact_email": {"value": "...", "confidence": 0.9}}`
- Merge strategy: for each field, pick value from source with highest confidence
- If merged result has <5 fields populated → trigger targeted re-search (Phase 6)

**Deliverables:**
- `backend/app/pipeline/extraction.py` — refactored:
  - `extract_from_source(content: str, url: str, foundation_name: str, prompts: dict) → ExtractedFoundationData | None` — NEW
  - `merge_extractions(extractions: list[tuple[ExtractedFoundationData, dict]]) → ExtractedFoundationData` — NEW
  - `ExtractedFoundationData` updated with:
    - `confidence: float` — overall confidence
    - `per_field_confidence: dict[str, float]` — per-field confidence
- `backend/app/pipeline/orchestrator.py` — updated:
  - Run extraction per source (parallel via `asyncio.gather()`)
  - Call `merge_extractions()` after all sources processed
  - Pass merged result to Service Area stage
- `backend/app/db/models/enrichment.py` — updated:
  - `EnrichmentData.extracted_data` now includes `per_field_confidence`
  - New column: `source_url: str` (which URL contributed this extraction)

**Definition of Done:**
- [ ] Per-source extraction implemented
- [ ] Merge by confidence implemented
- [ ] `ExtractedFoundationData` has confidence fields
- [ ] Tests pass (mocked extraction)
- [ ] Field completeness % ≥70% (target: 70% of foundations with ≥5/8 fields)

**Estimated Effort:** 3-4 dev-days

---

### Phase 5 — Prompt Versioning + Jinja2 Templates (1-2 days)

**Goal:** Enable A/B testing and rollback for prompts.

**Scope:**
- Create `enrichment_prompts` table + migration
- Jinja2 templates for each prompt type
- Admin UI: list prompts, create version, set production, view metrics
- Pipeline loads production prompt by default
- Log prompt version used in pipeline trace

**Deliverables:**
- `alembic/versions/YYYYMMDD_enrichment_prompts.py` — NEW migration:
  ```sql
  CREATE TABLE enrichment_prompts (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,  -- e.g., "extraction", "validation"
    version VARCHAR(50) NOT NULL,  -- e.g., "1.0.0", "1.1.0"
    template TEXT NOT NULL,  -- Jinja2 template
    variables JSON,  -- list of required template variables
    is_production BOOLEAN DEFAULT FALSE,
    metrics JSON,  -- {avg_confidence, field_completeness, runs_count}
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255)
  );
  ```
- `backend/app/pipeline/prompts/` — NEW directory:
  - `validation.j2` — Jinja2 template for validation prompt
  - `extraction.j2` — Jinja2 template for extraction prompt
  - `service_area.j2` — Jinja2 template for service area prompt
- `backend/app/services/prompt_service.py` — NEW:
  - `PromptService` class
  - `get_production_prompt(name: str) → str` — loads production template, renders with Jinja2
  - `create_prompt_version(name: str, version: str, template: str) → int` — creates new version
  - `set_production_version(name: str, version: str) → None` — sets production
- `backend/app/pipeline/prompts.py` — updated:
  - `VALIDATION_SYSTEM_PROMPT`, etc. now load from `PromptService`
  - Fallback to module constants if DB unavailable
- `apps/admin/src/pages/EnrichmentPromptsPage.tsx` — NEW:
  - List all prompts + versions
  - Create new version form
  - Set production button
  - View metrics (avg confidence, field completeness)

**Definition of Done:**
- [ ] `enrichment_prompts` table exists
- [ ] Jinja2 templates for all prompt types
- [ ] Admin UI for prompt management
- [ ] Pipeline loads production prompts
- [ ] Prompt version logged in trace
- [ ] Tests pass

**Estimated Effort:** 1-2 dev-days

---

### Phase 6 — Targeted Re-Search for Missing Fields (2-3 days)

**Goal:** Retry with field-specific queries when extraction is incomplete.

**Scope:**
- After merge, identify missing fields
- Generate targeted queries: `"foundation_name kontakt e-post"`, `"foundation_name ansökan öppnar"`
- Re-run Discovery + Validation + Crawl + Extraction for missing fields only
- Merge new extractions (only fill missing fields, don't overwrite high-confidence)
- Max 2 re-search iterations per foundation

**Deliverables:**
- `backend/app/pipeline/orchestrator.py` — updated:
  - Gap analysis after merge: `missing_fields = [f for f in REQUIRED_FIELDS if not merged_data.get(f)]`
  - If `len(missing_fields) > 0` and `iterations < 2`:
    - Generate targeted queries per missing field
    - Re-run Stages 1-4 for targeted search only
    - Merge new extractions (only for missing fields)
- `backend/app/pipeline/discovery.py` — updated:
  - `generate_targeted_query(field_name: str, foundation_name: str) → str` — NEW
  - Query templates:
    - `contact_email` → `"foundation_name kontakt e-post"`
    - `application_deadline` → `"foundation_name sista ansökningsdag"`
    - `who_can_apply` → `"foundation_name vem kan söka"`
- `backend/app/pipeline/base.py` — `PipelineContext` updated:
  - `re_search_iterations: int = 0` — track re-search count
  - `missing_fields: list[str] = []` — fields to target

**Definition of Done:**
- [ ] Gap analysis implemented
- [ ] Targeted queries generated per missing field
- [ ] Re-search runs max 2 iterations
- [ ] New extractions merge only for missing fields
- [ ] Field completeness % ≥85% (target: 85% of foundations with ≥5/8 fields)
- [ ] Tests pass

**Estimated Effort:** 2-3 dev-days

---

### Phase 7 — Observability & Admin Polish (1-2 days)

**Goal:** Make pipeline results auditable and measurable.

**Scope:**
- Per-foundation trace: which source contributed which field + confidence
- Dashboard: field completeness over time, per-prompt performance
- Export enrichment data (CSV/JSON) for manual review
- Document pipeline architecture (ADR)

**Deliverables:**
- `apps/admin/src/pages/EnrichmentResultsPage.tsx` — updated:
  - Per-field source + confidence display
  - "View Trace" modal showing full pipeline execution
- `backend/app/api/v1/routers/admin/enrichment.py` — NEW endpoints:
  - `GET /admin/enrich/field-completeness` — field completeness over time
  - `GET /admin/enrich/prompt-metrics` — per-prompt performance
  - `POST /admin/enrich/export` — export enrichment data (CSV/JSON)
- `docs/adr/XXX-enrichment-pipeline-v2.md` — NEW ADR documenting architecture
- `docs/enrichment-pipeline.md` — NEW user guide for admin users

**Definition of Done:**
- [ ] Per-field source + confidence visible in admin UI
- [ ] Field completeness dashboard
- [ ] Export functionality working
- [ ] ADR published
- [ ] User guide published

**Estimated Effort:** 1-2 dev-days

---

## 4. What NOT to Change

### 4.1 Working Behavior to Preserve

| Area | What to Keep |
|------|--------------|
| **API Endpoints** | All admin enrichment endpoints (`/admin/enrich/*`) |
| **Pipeline Orchestration** | `run_foundation_pipeline_task()` signature unchanged |
| **Service Area Logic** | Service area extraction unchanged (Phase 7 only adds observability) |
| **Foundation ID Format** | `foundation-{foundation_id}` canonical format |
| **LLM Backend** | LiteLLM proxy + `gemma-4-12b` (no changes to model selection) |
| **Redis/Dragonfly** | Existing Redis for Arq queue (reuse for search caching) |

### 4.2 Conventions Worth Keeping

| Convention | Reason |
|------------|--------|
| `PipelineStage` ABC (Phase 9 of modular refactor) | Clean interface for stages |
| `PipelineContext` dataclass | Consistent state passing |
| Module-level prompt constants (fallback) | Backward compatibility |
| Trafilatura for text extraction | Works well; no need to replace |

### 4.3 Trade-offs and Risks

| Risk | Mitigation |
|------|------------|
| **SearXNG maintenance** — self-hosted search requires upkeep | Document setup; use official Docker image; monitor uptime |
| **Bolagsverket rate limits** — API may throttle | Enforce 1 req/sec client-side; cache results |
| **Prompt versioning complexity** — DB schema + UI + pipeline integration | Keep schema simple; test rollback path |
| **Per-source extraction cost** — more LLM calls | Limit to 5 validated sources max; parallelize |
| **Re-search cost** — 2 iterations × multiple sources | Cap at 2 iterations; only search for missing fields |
| **Browserless removal** — some sites need JS rendering | Keep as optional fallback; document which sites need it |

### 4.4 Out of Scope (Explicitly Excluded)

| Item | Reason |
|------|--------|
| Human review queue | Defer until confidence scoring exists (Phase 4) |
| Active learning from corrections | Too complex for now; build signal first |
| Multi-LLM routing | Stick with LiteLLM + gemma-4-12b |
| Frontend changes | This is backend-only work |
| Kubernetes/Flux manifests | Infra team handles deployment |
| Alembic migrations (existing) | Immutable; only add new migrations |

---

## 5. Success Metrics

| Metric | Current | Phase 4 Target | Phase 6 Target | Measurement |
|--------|---------|----------------|----------------|-------------|
| Foundations with ≥5/8 fields | ~30% | 70% | 85% | `SELECT COUNT(*) FROM foundations WHERE jsonb_array_length(extracted_data->'fields') >= 5` |
| Avg fields per foundation | ~2.5 | 5.5 | 6.5 | `AVG(jsonb_array_length(extracted_data->'fields'))` |
| Pipeline latency (per foundation) | ~60s | ~45s | ~60s | Pipeline trace timestamps |
| External API cost | $0 | $0 | $0 | N/A (all self-hosted) |
| Browserless container | Required | Optional | Optional | `docker compose ps` |
| Search success rate | ~70% | ~85% | ~90% | `validated_sources / candidate_urls` |
| Crawl success rate | ~80% | ~90% | ~90% | `crawled_pages / validated_sources` |

---

## 6. Technical Debt to Address

### 6.1 Pre-Existing (Not Caused by This Plan)

| Debt | Location | Impact |
|------|----------|--------|
| No unit tests for `discovery.py` | `backend/tests/test_pipeline_discovery.py` missing | Can't regression-test search logic |
| No integration tests for full pipeline | `backend/test_run_pipeline.py` is manual script | Hard to verify end-to-end |
| Prompts not versioned | `backend/app/pipeline/prompts.py` constants | Can't track what prompt produced what result |
| No content deduplication | `backend/app/pipeline/crawler.py` | Wastes LLM tokens on duplicate content |

### 6.2 Introduced by This Plan (To Track)

| Debt | Phase | Mitigation |
|------|-------|------------|
| SearXNG self-hosted maintenance | Phase 2 | Document setup; monitor uptime |
| Bolagsverket API dependency | Phase 1 | Cache results; fallback to search |
| Prompt versioning schema | Phase 5 | Keep schema simple; add migration rollback |
| Per-source extraction complexity | Phase 4 | Limit sources; parallelize; test merge logic |

---

## 7. Testing Strategy

### 7.1 Unit Tests (New)

| Test File | Coverage |
|-----------|----------|
| `backend/tests/test_bolagsverket_client.py` | `BolagsverketClient.lookup_by_orgnr()` with mocked API |
| `backend/tests/test_searxng_client.py` | `SearXNGClient.search()` with mocked HTTP |
| `backend/tests/test_crawler_trafilatura.py` | `crawl_with_trafilatura()` with sample HTML |
| `backend/tests/test_extraction_confidence.py` | `extract_from_source()` confidence scoring |
| `backend/tests/test_merge_extractions.py` | `merge_extractions()` highest-confidence-wins logic |
| `backend/tests/test_prompt_service.py` | `PromptService` CRUD + Jinja2 rendering |

### 7.2 Integration Tests (New)

| Test File | Coverage |
|-----------|----------|
| `backend/tests/test_pipeline_bolagsverket.py` | Full Stage 0 execution (mocked API) |
| `backend/tests/test_pipeline_discovery_searxng.py` | Stage 1 with SearXNG (local instance) |
| `backend/tests/test_pipeline_full_v2.py` | Full pipeline Stages 0-7 (mocked external APIs) |

### 7.3 Manual Verification (Per Phase)

| Phase | Manual Test |
|-------|-------------|
| Phase 0 | SearXNG UI accessible; Jinja2 renders template |
| Phase 1 | Bolagsverket lookup returns data for known orgnr |
| Phase 2 | SearXNG returns results for Swedish foundation query |
| Phase 3 | Trafilatura extracts content from static site; Playwright fallback works |
| Phase 4 | Per-source extraction returns confidence scores |
| Phase 5 | Admin UI creates prompt version; pipeline uses production |
| Phase 6 | Re-search fills missing fields on test foundation |
| Phase 7 | Admin dashboard shows field completeness metrics |

---

## 8. Dependencies & Prerequisites

### 8.1 External Services

| Service | Purpose | Cost | Setup |
|---------|---------|------|-------|
| **SearXNG** | Multi-engine search | $0 (self-hosted) | Docker container + settings.yml |
| **Bolagsverket API** | Official registry lookup | $0 (public API) | No auth; rate limit 1 req/sec |
| **LiteLLM** | LLM proxy (existing) | $0 (self-hosted) | Already deployed |
| **Redis/Dragonfly** | Search caching (existing) | $0 (self-hosted) | Already deployed |

### 8.2 Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `jinja2` | `>=3.1.0` | Prompt templating |
| `httpx` | `>=0.28.1` (existing) | Bolagsverket + SearXNG HTTP client |
| `simhash` | `>=2.1.0` | Content deduplication (optional) |
| `ddgs` | `>=9.10.0` (existing) | DDG fallback search |
| `trafilatura` | `>=2.0.0` (existing) | Content extraction |
| `playwright` | `>=1.49.1` (existing, optional) | JS rendering fallback |

### 8.3 Infrastructure Changes

| Change | File | Impact |
|--------|------|--------|
| Add SearXNG service | `docker-compose.yml` | New container; port 8080 |
| Add SearXNG to k8s | `kubernetes/charts/stipendiatet/backend/values.yaml` | Helm chart update |
| Mark browserless optional | `docker-compose.yml` | Comment out by default |
| Add Jinja2 to requirements | `backend/requirements.txt` | New dependency |

---

## 9. Rollback Plan

### 9.1 Per-Phase Rollback

| Phase | Rollback Action |
|-------|-----------------|
| Phase 0 | Remove SearXNG container; drop `enrichment_prompts` table |
| Phase 1 | Disable `BolagsverketStage` in orchestrator; revert `PipelineContext` |
| Phase 2 | Revert `discovery.py` to DDG-only; remove SearXNG client |
| Phase 3 | Revert `crawler.py` to Playwright-only; re-enable browserless |
| Phase 4 | Revert `extraction.py` to single-shot; remove confidence fields |
| Phase 5 | Drop `enrichment_prompts` table; revert to module constants |
| Phase 6 | Disable re-search logic in orchestrator |
| Phase 7 | Remove new admin endpoints; revert UI changes |

### 9.2 Full Rollback (All Phases)

```bash
# Revert git to pre-Phase-0 commit
git checkout <commit-before-phase-0>

# Remove SearXNG container
docker compose down searxng

# Drop new tables
alembic downgrade -1  # Repeat until enrichment_prompts table dropped

# Re-enable browserless
# Edit docker-compose.yml: uncomment browserless service

# Restart pipeline
docker compose up -d backend enrichment-worker
```

---

## 10. Open Questions

### 10.1 Decisions Pending

| Question | Options | Recommendation |
|----------|---------|----------------|
| Bolagsverket API: official or third-party? | Official (direct) vs Signicat (paid proxy) | **Official** — free, no vendor lock-in |
| SearXNG: which engines to enable? | Google + Bing + DDG + Brave vs minimal | **All four** — maximize coverage |
| Content dedup: simhash vs embedding? | Simhash (fast) vs embedding (accurate) | **Simhash** — fast, good enough for dedup |
| Prompt versioning: semver or timestamp? | `1.0.0`, `1.1.0` vs `20261029-001` | **Semver** — clearer intent |
| Re-search: max iterations? | 1 vs 2 vs 3 | **2** — balance completeness vs cost |

### 10.2 Unknowns to Investigate

| Unknown | Investigation Plan |
|---------|-------------------|
| Bolagsverket API rate limits | Test with 100 orgnrs; monitor response codes |
| SearXNG performance on Swedish queries | Deploy locally; test with 50 foundation names |
| Trafilatura success rate on Swedish sites | Sample 50 foundation sites; measure extraction quality |
| LLM confidence calibration | Run extraction on 100 known foundations; compare confidence vs accuracy |

---

## Summary

**Problem:** Foundation data enrichment pipeline has ~30% field completeness (≥5/8 fields). Users can't find contact info, deadlines, or eligibility criteria for most foundations.

**Root Cause:** Single search engine (DDG), no official registry lookup, single-shot extraction with no retry, no confidence scoring.

**Solution:** 7-phase refactoring adding Bolagsverket lookup, SearXNG multi-engine search, trafilatura-first crawl, per-source extraction with confidence merge, prompt versioning, and targeted re-search.

**Expected Outcome:** 85% of foundations with ≥5/8 fields populated, $0/month external cost, faster pipeline (45s vs 60s), browserless optional.

**Estimated Effort:** 13-17 dev-days total (can run phases in parallel where independent).

**Next Step:** Dispatch `dev-team-lead` to begin Phase 0 (Infrastructure & Prereqs).