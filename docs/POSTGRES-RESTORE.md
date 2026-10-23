# Postgres Restore Runbook

> Full runbook: `flux/infrastructure/postgres/RESTORE.md` (fleet-infra repo).

## Invariant

The deployed backend image must be **≥ the backup's age**. A backup restored
under a stale image will crash at startup because the image's alembic versions
directory does not contain the revision the DB's `alembic_version` table
points to.

## Quick Check

After restore, verify the deployed image's commit contains the DB's current
revision. GHCR `:<sha>` tags make this a 10-second check:

```bash
docker run --rm ghcr.io/seppaleinen/stipendariet/backend:<sha> \
  ls /app/alembic/versions/ | grep <rev>
```

If the revision is absent, the image is stale — redeploy a newer chart version
**before** the restore, not after.

## Verify After Restore

```bash
kubectl logs deploy/backend -n stipendariet | grep alembic
```

Expected output: `Running upgrade ... -> <head>` (e.g.
`-> 2026_09_02_000001`). The container should then become Ready.

## Rollback Option

If the image is stale, redeploy a newer chart version *before* the restore,
not after. Rolling back the chart after restore will not help — the DB is
already at a revision the old image does not know.

## Startup Pre-Flight

`backend/migrations_check.py` now runs as the first command in the Docker
CMD (before the alembic retry loop). It:

- Loads the image's known alembic revisions.
- Connects to Postgres and reads `alembic_version`.
- Exits 0 if the DB revision is known, the DB is fresh, or Postgres is
  unreachable (lets the retry loop handle it).
- Exits 1 with a clear FATAL message if the DB revision is unknown to the
  image — replacing the cryptic `Can't locate revision` error.