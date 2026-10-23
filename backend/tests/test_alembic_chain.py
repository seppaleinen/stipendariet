"""Pure unit tests for the alembic migration graph — no database required.

These tests inspect the alembic script directory to verify:
- The migration graph has a single head (no unresolved merge branches).
- Critical revisions are present.
- Every revision file in ``versions/`` is reachable from the head (no orphaned
  branches that would silently break a fresh checkout).
"""

import os

from alembic.config import Config
from alembic.script import ScriptDirectory


def _script_dir() -> ScriptDirectory:
    """Return the ScriptDirectory for the backend alembic config."""
    here = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(here)
    ini_path = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(ini_path)
    return ScriptDirectory.from_config(cfg)


def test_single_head() -> None:
    """The migration graph must have exactly one head."""
    s = _script_dir()
    heads = s.get_heads()
    assert len(heads) == 1, (
        f"Expected exactly one alembic head, got {len(heads)}: {heads}. "
        f"Run `alembic merge` to resolve multiple heads."
    )


def test_known_revisions_present() -> None:
    """Critical revisions must exist in the script directory."""
    s = _script_dir()
    known = {sc.revision for sc in s.walk_revisions()}
    critical = [
        "2026_09_02_000001",
        "2026_09_01_000001",
        "93d610535c3d",
        "abc123def456",
    ]
    missing = [r for r in critical if r not in known]
    assert not missing, f"Critical revisions missing from migration graph: {missing}"


def test_all_revisions_reachable_from_head() -> None:
    """Every revision file in versions/ must be reachable from the single head."""
    s = _script_dir()
    heads = s.get_heads()
    assert len(heads) == 1, (
        f"Cannot verify reachability: expected single head, got {heads}"
    )

    head = next(iter(heads))

    # Collect every revision file on disk.
    disk_files = set()
    for versions_dir in s._version_locations:
        for fname in os.listdir(versions_dir):
            if fname.endswith(".py") and not fname.startswith("_"):
                disk_files.add(fname)

    # Collect every file that alembic knows about via walk_revisions.
    walked_files = {os.path.basename(sc.path) for sc in s.walk_revisions()}

    # Every file on disk must be reachable from the head.
    orphaned = disk_files - walked_files
    assert not orphaned, (
        f"Orphaned revision files (not reachable from head {head}): {orphaned}"
    )
