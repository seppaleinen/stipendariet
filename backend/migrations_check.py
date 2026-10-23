"""Startup pre-flight: verify the database revision is known to the image.

Loads the alembic script directory from the image, connects to the database,
and reads the current ``alembic_version`` table value. If the DB's revision is
not among the revisions known to the image, prints a clear fatal error and
exits with code 1. If the DB has no ``alembic_version`` table yet, or the
table exists but is empty (fresh DB / interrupted migration), exits 0 (let
alembic upgrade handle it). If the DB's revision IS known, exits 0.
Connection errors are handled gracefully (exit 0 — let the retry
loop in the Docker CMD handle postgres-not-ready).
"""

import os
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory


def main() -> int:
    # Locate alembic.ini relative to this file (backend/alembic.ini).
    here = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(here, "alembic.ini")

    cfg = Config(ini_path)
    script_dir = ScriptDirectory.from_config(cfg)

    # Collect every revision the image knows about.
    known_revisions = {sc.revision for sc in script_dir.walk_revisions()}

    # Build a connection string from the same env vars used by alembic/env.py.
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "postgres")
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "stipendariet")

    # SQLAlchemy import is deferred so that a missing psycopg2 driver doesn't
    # prevent the script from running in environments where the DB is simply
    # not reachable yet. The engine is also created inside the same guard:
    # SQLAlchemy imports the DBAPI driver at create_engine() time, so a
    # missing driver raises ModuleNotFoundError here, not at import time.
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
            connect_args={"connect_timeout": 5},
        )
    except Exception:
        # SQLAlchemy or its DBAPI driver is unavailable — bail out gracefully.
        print("migrations_check: sqlalchemy/dbapi unavailable, skipping check")
        return 0

    try:
        with engine.connect() as conn:
            # Does the alembic_version table exist?
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version')"
                )
            )
            table_exists = result.scalar()
            if not table_exists:
                # Fresh DB — let alembic upgrade handle it.
                print("migrations_check: no alembic_version table (fresh DB), OK")
                return 0

            # Read the current revision.
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_rev = result.scalar()
            if current_rev is None:
                # Table exists but is empty (e.g. interrupted migration or
                # manually created table) — treat as a fresh DB.
                print("migrations_check: alembic_version table empty, treating as fresh DB")
                return 0
    except Exception as exc:
        # Connection error (postgres not ready, network issue, etc.) — exit 0
        # so the retry loop in the Docker CMD can keep trying.
        print(f"migrations_check: database unavailable ({exc}), skipping check")
        return 0

    if current_rev in known_revisions:
        print(
            f"migrations_check: database at revision {current_rev} "
            f"is known to the image, OK"
        )
        return 0

    # Fatal: the DB is at a revision this image doesn't know about.
    print(
        f"FATAL: database at revision {current_rev} but image only knows "
        f"revisions {sorted(known_revisions)}. "
        f"Deploy a newer image or restore a newer backup."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
