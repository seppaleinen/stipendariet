# PR Description: Deduplicate OpenAPI Tags on Mixed Routers

---

## Summary

Fix cosmetic OpenAPI tag duplication on three mixed routers that serve both public and admin endpoints.

---

## Changes

- **`backend/app/api/v1/routers/public/foundations.py`**
  - Removed `tags=["foundations"]` from `APIRouter` constructor
  - Added explicit `tags=["foundations"]` to all 13 public endpoints
  - Admin endpoints (`/reset-categories`, `/categorize-db-foundations`) unchanged — already have `tags=["foundations", "admin"]`

- **`backend/app/api/v1/routers/public/auth.py`**
  - Removed `tags=["auth"]` from `APIRouter` constructor
  - Added explicit `tags=["auth"]` to 5 public endpoints (`/signup`, `/login`, `/me`, `/logout`, `/google`)
  - Admin endpoint (`/exchange`) unchanged — already has `tags=["auth", "admin"]`

- **`backend/app/api/v1/routers/public/foundation_sync.py`**
  - Removed `tags=["foundation-sync"]` from `APIRouter` constructor
  - Added explicit `tags=["foundation-sync"]` to 4 public endpoints (`/foundations`, `/foundations/{id}`, `/status`, `/generate-application`)
  - Admin endpoint (`/trigger-sync`) unchanged — already has `tags=["foundation-sync", "admin"]`

- Added file header comments on all three routers explaining the design decision

---

## Testing

- All 308 backend tests pass (`pytest tests/`)
- Verified OpenAPI output: no duplicate tags in `/openapi.json`
- Swagger UI renders correctly at `/docs`
- Admin endpoints retain `"admin"` tag for discoverability
- Public endpoints have single appropriate tags

---

## Breaking Changes

None. Purely cosmetic OpenAPI improvement — no runtime behavior changes.