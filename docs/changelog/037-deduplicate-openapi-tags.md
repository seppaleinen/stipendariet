# Changelog Entry

---

## Fixed

- **OpenAPI tag deduplication** on mixed routers (`foundations.py`, `auth.py`, `foundation_sync.py`)
  - Removed router-level `tags` from `APIRouter` constructors
  - Added explicit endpoint-level `tags` to all public endpoints
  - Admin endpoints retain dual tags (`["<domain>", "admin"]`) for Swagger UI discoverability
  - Eliminates duplicate tags in generated OpenAPI spec and Swagger UI
  - Added explanatory file header comments on affected routers

---

## Verification

- All 308 backend tests pass
- OpenAPI output verified: no duplicate tags
- Swagger UI renders correctly
- Code review: SUCCESS
- Security review: SUCCESS