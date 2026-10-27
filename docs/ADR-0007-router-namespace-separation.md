# ADR-0007: Router Namespace Separation by Access Level

## Status

Accepted

## Context

The backend API lived under a single flat `backend/app/api/v1/routers/` package with all router modules at one level. As the codebase grew, this created ambiguity around which endpoints were public-facing versus admin-only, and mixed concerns within the same directory. The `admin.py` aggregator module imported from sibling router files without any structural distinction between access tiers.

The modular refactoring plan (Phase 6) called for separating routers by access level into `public/` and `admin/` subpackages, giving the codebase a clear namespace boundary that mirrors the API's two consumer classes.

## Decision

Reorganize `backend/app/api/v1/routers/` into two subpackages:

- **`public/`** — 9 routers for the public frontend API:
  - `auth.py`, `profile.py`, `applications.py`, `grants.py`, `search.py`, `funding.py`, `foundations.py`, `foundation_sync.py`, `foundations_api.py`
- **`admin/`** — the admin aggregator plus 8 submodules:
  - `admin.py` (aggregator), `admin_password_reset.py`
  - `categorization.py`, `embeddings.py`, `enrichment.py`, `foundations.py`, `sources.py`, `sync.py`, `system.py`, `translation.py`

Delete the legacy `backend/app/api/admin/` package (8 files relocated into `v1/routers/admin/`).

Update `main.py` imports to the new subpackage paths; include order unchanged. Add `routers/__init__.py` re-exports for backward compatibility. Tag 4 mixed endpoints with the `admin` OpenAPI tag (`/reset-categories`, `/categorize-db-foundations`, `/exchange`, `/trigger-sync`) so API consumers can distinguish admin-only routes.

## Consequences

### Positive

- **Clear access-level boundary** — Public and admin routers live in separate namespaces; a developer can immediately see which tier a route belongs to by its path.
- **Backward compatible** — `routers/__init__.py` re-exports preserve any existing import paths; zero endpoint path changes, zero response shape changes. All 79 `/api/` routes identical to HEAD.
- **Admin aggregator simplified** — `admin.py` now imports from sibling submodules within the same package rather than mixing flat-file imports, making the admin router easier to read and extend.
- **OpenAPI tags added** — The `admin` tag on 4 mixed endpoints lets API consumers filter admin-only routes in generated docs.

### Negative

- **Import path churn** — Every file that imported from the old flat layout required updates; test patches in `test_routers.py`, `test_admin_sources.py`, `test_backfill_service_area.py`, and `test_issue19_urls.py` had to be updated.
- **E402 ignores expanded** — `pyproject.toml` per-file E402 ignores updated to accommodate the new subpackage import ordering.
- **Bonus bug fix surfaced** — During review, `public/foundations.py` was found to call itself recursively (`reset_categories` and `categorize_db_foundations` endpoints delegated to their own module names, causing `RecursionError`). These now delegate to `app.services.foundation_service` via aliased imports.

## Alternatives Considered

1. **Keep flat layout with tags only** — Adding OpenAPI tags to distinguish public/admin endpoints would have been the least invasive change, but it would leave the directory structure ambiguous and fail to enforce the namespace boundary at the filesystem level.
2. **Split `admin.py` endpoints per module** — Dismantling the aggregator entirely and merging each admin submodule's routes into the corresponding router file would have maximized locality but would have broken the existing `admin.py` entry point, required widespread consumer changes, and offered no clear benefit over the subpackage approach.

---