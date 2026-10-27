# ADR-0004: Backend Model Separation

## Status

Accepted

## Context

`backend/app/db/models.py` was a 226-line monolith containing all eight SQLAlchemy ORM entity definitions (User, SavedGrant, Profile, Foundation, EnrichmentSource, EnrichmentPage, EnrichmentData, Grant, Application) plus the shared `Base` in a single file. As the data model grew, the file became unwieldy: every entity change required opening one large file, unrelated models were forced into the same edit context, and the file violated single-responsibility cohesion. `database.py` also independently declared a duplicate `Base = declarative_base()`, creating two distinct `Base` classes in the codebase — a latent source of `metadata` mismatch bugs.

## Decision

Split `models.py` into a `backend/app/db/models/` package with one module per entity:

| File | Entities |
|------|----------|
| `models/__init__.py` | `Base` + re-exports of all model classes |
| `models/user.py` | `User` |
| `models/saved_grant.py` | `SavedGrant` |
| `models/profile.py` | `Profile` |
| `models/foundation.py` | `Foundation` |
| `models/enrichment.py` | `EnrichmentSource`, `EnrichmentPage`, `EnrichmentData` |
| `models/grant.py` | `Grant` |
| `models/application.py` | `Application` |

The single `Base` now lives exclusively in `models/__init__.py`. `database.py` had its duplicate `Base` removed and now imports from `app.db.models`. Every entity module imports `Base` from `app.db.models` (the package), preserving the same `Base.metadata` registry. Backward compatibility is maintained: `from app.db.models import User` continues to work unchanged because `__init__.py` re-exports every class and lists them in `__all__`.

## Consequences

**Positive:**
- Each entity can be understood, tested, and modified in isolation.
- Adding a new model means creating one small file and one import line — no edit to a shared monolith.
- The duplicate `Base` in `database.py` is eliminated; there is now exactly one `Base` class, so `metadata` mismatches are no longer possible.
- All 16 existing import sites (`grep -rn "from app.db.models import"`) require zero changes — the re-export shim preserves the public API.

**Negative:**
- Circular import risk: entity modules import `Base` from the package `__init__`, which imports them. This is safe today because `Base` is defined before the model imports, but adding a model that needs another model at import time (rather than via string-based `relationship()`) would break. All relationships currently use string references, which is the correct pattern.
- Slightly more files to navigate, but each is smaller and focused.

## Implementation Notes

- The `__init__.py` uses `# noqa: E402` on model imports because they follow the `Base` definition (module-level import-not-at-top-of-file).
- `enrichment.py` groups three tightly related enrichment tables (`EnrichmentSource`, `EnrichmentPage`, `EnrichmentData`) that share foreign keys and are co-dependent; splitting them further would add no value.
- `database.py` change: removed `from sqlalchemy.ext.declarative import declarative_base` and the `Base = declarative_base()` lines; `create_tables()` now uses `from app.db.models import Base`.