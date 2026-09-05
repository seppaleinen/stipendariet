# Enrichment Pipeline TODO

## Current State — Source Table Architecture (Option B)

**Status: Implemented** (backend `0d15fac`/`fff29f5`)

The enrichment pipeline records where each scraped/extracted data point came
from using three database tables that describe "sources" (aggregator sites
like `annsansradstod.se`, official foundation sites, blogs, directories) and
the pages/data harvested from them. Provenance is tracked per foundation:
each matched source, its crawled pages, and the extracted data linked back to
the source that produced it.

### Tables (defined in `backend/app/db/models.py`)

- **`enrichment_sources`** — one row per discovered source for a foundation:
  `id` (PK), `foundation_id` (FK → `foundations.id`, indexed), `url` (NOT
  NULL; **not unique** — the same URL may appear for multiple foundations),
  `source_type` (`'aggregator' | 'official' | 'blog' | 'directory'`, nullable),
  `is_official` (bool, default `false`), `confidence` (float 0–1),
  `last_validated` (datetime), `created_at` (datetime).
  Relationships: `foundation` (back-populated from `Foundation.sources`),
  `pages` → `enrichment_pages`, `data_entries` → `enrichment_data`.
- **`enrichment_pages`** — crawled pages per source: `id` (PK),
  `source_id` (FK → `enrichment_sources.id`), `url` (NOT NULL), `page_type`
  (`'homepage' | 'application' | 'contact' | 'other'`), `raw_content` (Text),
  `scraped_at` (datetime).
- **`enrichment_data`** — extracted LLM output per foundation/source:
  `id` (PK), `foundation_id` (FK → `foundations.id`), `source_id` (FK →
  `enrichment_sources.id`, nullable), `extracted_data` (JSON — structured
  LLM output), `confidence` (float), `extracted_at` (datetime).

Tables are auto-created at startup via `Base.metadata.create_all()`
(`backend/app/db/database.py`) — no manual migration required. The
`Foundation.sources` relationship exposes all sources for a foundation.

### Pipeline integration (`backend/app/pipeline/orchestrator.py`)

- `_db_save_source()` persists each matched candidate per foundation
  (`url`, `is_official`, `confidence`) and returns the new source id.
- `_db_save_pages()` stores the crawled pages for a source.
- `_db_save_extraction()` stores the merged LLM extraction against the
  primary source id.
- Per-source provenance is captured in the pipeline trace (`trace["sources"]`
  entries containing the matched pages and extraction for each source).

### Admin API (`backend/app/api/admin/sources.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/sources` | List sources. Optional filters: `foundation_id`, `is_official`, `source_type` (combinable, AND). |
| GET | `/api/admin/sources/{id}` | Get one source (404 when missing). |
| POST | `/api/admin/sources` | Create. `url` required; `is_official`, `confidence` (0–1), `source_type`, `foundation_id` optional. Duplicate URLs are currently allowed; the response reflects the newest row for the URL. |
| PUT | `/api/admin/sources/{id}` | Partial update of provided fields (404 when missing). |
| DELETE | `/api/admin/sources/{id}` | Delete (404 when missing). |

Admin UI: `apps/admin/src/pages/EnrichmentSourcesPage.tsx`, reachable at the
`/sources` route (Källor nav item), with filters, add/edit modals, and delete.

**Benefits:**
- Track data provenance - know where each piece of data came from
- Pre-parse aggregator sites once, use for multiple foundations
- Compare data from multiple sources for same foundation

## Future Enhancements

- **Source reliability scoring based on user feedback** (original step 4):
  build per-source reliability scores over time by correlating user-confirmed
  accuracy with `confidence`/`is_official` signals. Needs feedback capture
  plumbing that does not exist yet.
- **URL uniqueness/deduplication policy**: `url` is intentionally not unique
  today, so the same aggregator URL can be harvested for several foundations.
  A future change could add dedupe rules (e.g. unique per foundation_id) once
  aggregator normalization is in place.