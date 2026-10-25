# ADR-0002: Migrations Check No-Driver Regression Test

## Status

Accepted

## Context

Issue #30 introduced a regression where `create_engine` in `backend/migrations_check.py` was placed outside the `try/except` guard. When the PostgreSQL DBAPI driver `psycopg2`/`psycopg` was not importable, the script raised `ModuleNotFoundError` with a traceback and exited 1, instead of gracefully skipping.

`migrations_check.py` is a startup pre-flight check. Its graceful-skip contract is: if SQLAlchemy or its DBAPI driver is unavailable, print `migrations_check: sqlalchemy/dbapi unavailable, skipping check` and return 0. This allows the container to start and retry when the database becomes reachable.

Issue #31 requested a regression test that ensures this skip path is exercised and protected against future refactoring.

## Decision

Implement the regression test using an in-process `sys.meta_path` import blocker rather than a separate virtual environment or subprocess.

New file `backend/tests/test_migrations_check.py` provides:
- `_DriverBlocker`: a `sys.meta_path` finder that raises `ModuleNotFoundError` for top-level modules `psycopg2`, `psycopg`, `psycopg2-binary`, `psycopg2_binary`.
- `block_db_drivers` fixture: saves any already-loaded driver modules, inserts the blocker at `sys.meta_path[0]`, yields, then restores state and cleans up any modules created during the test.
- `test_migrations_check_graceful_skip`: imports `migrations_check.main` inside the fixture, calls it, asserts return code is 0, stdout contains the exact skip message, and no traceback appears in stdout/stderr.

The CI change adds a step in `.github/workflows/ci.yml` `docker-build` job:
```
Run migrations_check no-driver regression test
working-directory: backend
run: pytest tests/test_migrations_check.py -v
```

Rationale:
- In-process blocking reproduces the import error exactly as the production code would see it, without requiring a driver-less environment.
- It runs in the existing pytest session, reusing the same interpreter and dependencies.
- No Docker image rebuild, no separate venv, and no network requirements.

## Consequences

Positive:
- The graceful-skip behavior is now covered by an automated test that runs on every PR.
- Failure is fast and deterministic; the test executes in milliseconds.
- The test verifies both the exit code and the user-visible message, preventing silent changes.

Negative:
- The test relies on implementation details of Python import machinery; changes to driver module names or import paths require updating `_BLOCKLIST`.
- Meta-path manipulation is harder to read than a simple mock; teardown must carefully restore `sys.modules` to avoid cross-test contamination.

No changes were made to `backend/migrations_check.py` itself.
