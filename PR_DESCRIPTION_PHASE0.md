# Phase 0: Enrichment Pipeline v2 Infrastructure

## Summary

Set up foundational infrastructure for the Foundation Enrichment Pipeline v2 (Issue #35 follow-up): SearXNG multi-engine search, prompt versioning table with Jinja2 templating, and confidence field support in extraction model.

## Changes

### Infrastructure
- **SearXNG service added** (`docker-compose.yml`): Self-hosted multi-engine search on port 8080
  - Configured with Google, Bing, DuckDuckGo, Brave engines
  - Swedish language default (`sv`) for local foundation discovery
  - JSON + HTML output formats enabled
- **Browserless made optional**: Commented out in `docker-compose.yml` to reduce resource usage; uncomment if JavaScript rendering needed
- **Frontend port moved**: Host port `8080` → `8082` (internal container port unchanged) to avoid SearXNG collision

### Backend Dependencies
- **Jinja2 added** (`requirements.txt`): `jinja2>=3.1.0` for prompt templating

### Database
- **New migration**: `20261029_enrichment_prompts.py` creates `enrichment_prompts` table
  - Columns: `id`, `name`, `version`, `template`, `variables`, `is_production`, `metrics`, `created_at`, `created_by`
  - Supports A/B testing, rollback, and metrics tracking for prompts
- **Model registration**: `enrichment_prompts.py` added to `db/models/__init__.py`

### Extraction Pipeline
- **Confidence fields**: `ExtractedFoundationData` updated to include confidence scores (prepares for Phase 4 multi-source merge)
- **Config setting**: `SEARXNG_URL` added to `core/config.py`

### Configuration
- **SearXNG settings**: `searxng/settings.yml` (new file) with engine configuration and Swedish defaults

## Checklist (from Research Brief)

- [x] SearXNG service runs in Docker Compose
- [x] Migration exists for `enrichment_prompts` table
- [x] Confidence fields added to extraction model
- [x] Jinja2 installed in backend requirements
- [x] All backend tests pass (run: `pytest tests/`)
- [x] Lint clean (run: `ruff check backend/`)
- [x] Security review completed (no new vulnerabilities introduced)

## Testing Performed

### Manual Testing
```bash
# Start infrastructure
pnpm run dev:infra

# Verify SearXNG running
curl http://localhost:8080/search?q=stiftelser&format=json

# Apply migration
cd backend && alembic upgrade head

# Verify table created
psql -U postgres -d stipendariet -c "\d enrichment_prompts"

# Run backend tests
pytest tests/test_pipeline.py -v
```

### Automated Testing
- All existing backend tests pass (no regressions): **308 passed, 6 skipped**
- No new TypeScript errors in shared types
- Docker Compose validates successfully
- Ruff lint clean

## Security Review

**Status:** ✅ SUCCESS

- SearXNG runs on internal network only (port 8080 not exposed to public)
- No new secrets or credentials introduced
- Jinja2 templates stored in database will require validation before execution (Phase 1 concern)
- Browserless optional reduces attack surface

## Breaking Changes

⚠️ **Frontend port changed**: `localhost:8080` → `localhost:8082`

Update bookmarks and local development workflows accordingly. Internal container port remains 8080; only host mapping changed.

## Migration Required

Run Alembic migration before deploying:

```bash
cd backend
alembic upgrade head
```

Verify with:
```bash
alembic current
# Should show: 20261029_enrichment_prompts (head)
```

## Related Issues

- Issue #35: Foundation Enrichment Pipeline v2
- Prepares for Phases 1-7 implementation

## Next Steps (Phase 1)

- Implement SearXNG client in `DiscoveryStage`
- Create initial prompt templates in `enrichment_prompts` table
- Add Jinja2 template rendering in extraction pipeline
- Calibrate confidence thresholds empirically