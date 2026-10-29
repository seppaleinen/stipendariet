# ADR 007: Deduplicate OpenAPI Tags on Mixed Routers

**Status:** Accepted

**Date:** 2026-10-29

---

## Context

Three API routers in the backend serve both public and admin-gated endpoints:

- `backend/app/api/v1/routers/public/foundations.py` — public search/match endpoints + admin categorization endpoints
- `backend/app/api/v1/routers/public/auth.py` — public auth endpoints + admin token exchange endpoint
- `backend/app/api/v1/routers/public/foundation_sync.py` — public sync/status/generate endpoints + admin trigger-sync endpoint

Originally, each router defined a `tags` parameter in its `APIRouter` constructor (e.g., `tags=["foundations"]`). Individual endpoints also specified their own `tags` parameter. FastAPI merges router-level and endpoint-level tags, resulting in **duplicate tags** in the generated OpenAPI spec and Swagger UI — e.g., `["foundations", "foundations"]` for public endpoints and `["foundations", "foundations", "admin"]` for admin endpoints.

---

## Decision

**Remove router-level `tags` from `APIRouter` constructors on mixed routers.** Instead, set explicit `tags` on every endpoint:

- Public endpoints get a single tag: `tags=["<domain>"]` (e.g., `["foundations"]`, `["auth"]`, `["foundation-sync"]`)
- Admin endpoints keep their explicit dual tags: `tags=["<domain>", "admin"]` (unchanged)

Add a file header comment on each affected router explaining the design decision.

---

## Consequences

### Positive

- **Clean OpenAPI output**: No duplicate tags in the spec or Swagger UI
- **Explicit intent**: Every endpoint declares its own tags, making grouping obvious
- **Admin discoverability preserved**: Admin endpoints still carry `"admin"` tag for filtering in Swagger UI
- **No runtime behavior change**: Purely cosmetic OpenAPI improvement

### Negative

- **Slightly more verbose endpoint definitions**: Each endpoint must specify `tags`
- **Consistency requirement**: New endpoints on these routers must follow the pattern

### Neutral

- Purely cosmetic change — no functional impact on API behavior, authentication, or authorization
- All 308 backend tests pass
- Code review: SUCCESS (one nit: blank line inconsistency in `foundation_sync.py`)
- Security review: SUCCESS (no runtime behavior changes)

---

## Related

- Issue #37: Deduplicate OpenAPI tags on mixed routers
- Files modified:
  - `backend/app/api/v1/routers/public/foundations.py`
  - `backend/app/api/v1/routers/public/auth.py`
  - `backend/app/api/v1/routers/public/foundation_sync.py`