# ADR-0001: Alembic Migration Gating

## Status

Accepted

## Context

A Postgres restore in production pointed the `alembic_version` table at
revision `2026_09_01_000001`. The deployed backend image was built from a
commit that did not yet include `2026_09_02_000001` (the successor). The
container crashed at startup with the cryptic Alembic error
"Can't locate revision", giving operators no actionable signal.

Root cause: `image.tag: latest` combined with `pullPolicy: IfNotPresent`
allowed a node-cached stale image to serve a DB whose revision was unknown
to the image. The migration graph on `main` was already linear with a single
head (`2026_09_02_000001`) at the time of this fix — no merge migration was
required. The "two heads" premise in the original issue plan was stale; the
dated chain was already threaded through the merge point
(`93d610535c3d`).

## Decision

1. **Startup pre-flight revision-coverage check** (`backend/migrations_check.py`).
   Before the alembic upgrade loop, the container loads the image's known
   revisions, connects to Postgres, reads `alembic_version`, and exits 1
   with a clear FATAL message if the DB's revision is unknown to the image.
   Exits 0 on connection errors, fresh DBs, and empty `alembic_version`
   tables.

2. **CI gate on migration-graph health** (`.github/workflows/ci.yml`,
   "Verify alembic chain" step). Runs after backend tests, before
   QEMU/docker build/push. Asserts a single head, critical revisions are
   present, and every revision file on disk is reachable from the head.

3. **Pinned chart image tag** (`kubernetes/charts/stipendiatet/backend/values.yaml`).
   `tag: "0.15.4"` replaces `latest`. The release workflow retags images to
   release semver via `docker buildx imagetools create` and rewrites
   `tag:` in chart values.yaml via `sed` at publish time, so the in-repo
   default stays pinned.

## Consequences

- **Fail-fast with clear error** instead of a cryptic crash. Operators see
  exactly which revision the DB is at and which revisions the image knows.
- **CI catches graph regressions before image push.** Orphaned branches,
  multiple heads, or missing critical revisions fail the build.
- **Deterministic deploys via pinned tags.** `pullPolicy: IfNotPresent`
  combined with a pinned tag prevents node-cached stale images from serving
  newer backups.
- **No merge migration was required.** The graph was already single-headed
  on `main`; this ADR records that fact so future reviewers do not assume a
  merge was needed.