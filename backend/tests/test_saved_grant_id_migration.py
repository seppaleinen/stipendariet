"""
Unit test for the issue #19 saved-grant foundation-id migration.

Exercises the real `_rewrite_saved_grant_ids` control flow with fakes, verifying:
  - legacy `foundation-{db_id}` rows are rewritten to `foundation-{foundation_id}`
    via a mapping from the CURRENT foundations table (id -> foundation_id);
  - `grant-{id}` rows are left untouched;
  - rows whose db_id has no matching foundation are left UNCHANGED (never deleted);
  - the rewrite is idempotent (running twice is a no-op);
  - `upgrade()` delegates to the helper with `op.get_bind()`.
"""
import importlib.util
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic/versions/abc123def456_rewrite_saved_grant_foundation_ids.py"
_spec = importlib.util.spec_from_file_location("migration_under_test", _MIGRATION_PATH)
assert _spec and _spec.loader, "could not load migration module"
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


class _Row:
    """Simple indexable row mimicking a DB result row."""

    def __init__(self, values):
        self._v = values

    def __getitem__(self, idx):
        return self._v[idx]


def _make_conn(legacy_rows, foundation_rows):
    """Build a fake connection routing purely by call order.

    `_rewrite_saved_grant_ids` executes in a fixed order:
      1. SELECT active legacy rows   (returns `legacy_rows`)
      2. SELECT foundations mapping  (returns `foundation_rows`)
      3..N UPDATE saved_grants ...   (recorded into `conn.updates`)

    The first two `execute()` calls are the SELECTs (sa.select is patched to
    MagicMock in the tests); all subsequent calls are UPDATEs.
    """
    update_calls = []
    conn = MagicMock()
    # Emulate the SQL `WHERE grant_id ~ '^foundation-\d+$'` filter: only legacy
    # foundation-<digits> rows are returned by the legacy-row SELECT.
    legacy_filtered = [r for r in legacy_rows if re.fullmatch(r"foundation-\d+", r[1])]

    def _result(rows):
        wrapped = [_Row(x) for x in rows]
        m = MagicMock()
        m.fetchall.return_value = wrapped
        m.__iter__.return_value = iter(wrapped)
        return m

    select_results = iter(
        [
            _result(legacy_filtered),
            _result(foundation_rows),
        ]
    )

    def execute(statement, *args, **kwargs):
        try:
            return next(select_results)
        except StopIteration:
            update_calls.append(statement)
            return MagicMock()

    conn.execute.side_effect = execute
    conn.updates = update_calls
    return conn


def test_rewrites_legacy_foundation_db_ids_to_canonical():
    """Legacy foundation-{db_id} rows are rewritten using the current foundations mapping."""
    conn = _make_conn(
        legacy_rows=[(1, "foundation-1"), (2, "foundation-2"), (3, "grant-999")],
        foundation_rows=[(1, 100), (2, 200), (3, 300)],
    )

    # The function builds real sa.Table reflection from autoload_with=conn — stub
    # the columns it needs so no real reflection occurs.
    def _fake_table(name, meta, autoload_with=None):
        t = MagicMock()
        if name == "saved_grants":
            t.c.id = MagicMock()
            t.c.grant_id = MagicMock()
            t.c.grant_id.op.return_value = lambda *a, **k: MagicMock()
            t.update.return_value.where.return_value = MagicMock()
        else:  # foundations
            t.c.id = MagicMock()
            t.c.foundation_id = MagicMock()
        return t

    select_mock = MagicMock()
    select_mock.where.return_value = select_mock
    with patch.object(migration.sa, "Table", side_effect=_fake_table), \
         patch.object(migration.sa, "MetaData", return_value=MagicMock()), \
         patch.object(migration.sa, "select", return_value=select_mock):
        rewritten, unchanged = migration._rewrite_saved_grant_ids(conn, log=lambda *a, **k: None)

    # Only foundation rows 1 and 2 have a matching foundation -> 2 rewritten.
    assert rewritten == 2
    assert unchanged == 0
    assert len(conn.updates) == 2


def test_leaves_orphaned_and_grant_rows_unchanged():
    """Rows with no matching foundation (orphan) or that are `grant-` ids are untouched."""
    conn = _make_conn(
        legacy_rows=[(1, "foundation-1"), (2, "foundation-99"), (3, "grant-999")],
        foundation_rows=[(1, 100)],  # db_id 99 renumbered away; no foundation for it
    )

    def _fake_table(name, meta, autoload_with=None):
        t = MagicMock()
        t.c.id = MagicMock()
        t.c.grant_id = MagicMock()
        t.c.grant_id.op.return_value = lambda *a, **k: MagicMock()
        t.update.return_value.where.return_value = MagicMock()
        return t

    select_mock = MagicMock()
    select_mock.where.return_value = select_mock
    with patch.object(migration.sa, "Table", side_effect=_fake_table), \
         patch.object(migration.sa, "MetaData", return_value=MagicMock()), \
         patch.object(migration.sa, "select", return_value=select_mock):
        rewritten, unchanged = migration._rewrite_saved_grant_ids(conn, log=lambda *a, **k: None)

    # Only db_id 1 has a matching foundation -> exactly 1 rewritten; orphan + grant untouched.
    assert rewritten == 1
    assert unchanged == 1
    assert len(conn.updates) == 1


def test_idempotent_skips_already_canonical():
    """An already-canonical foundation-{foundation_id} row is skipped on re-run."""
    conn = _make_conn(
        legacy_rows=[(1, "foundation-100")],  # db_id 100 -> foundation_id 100 (already canonical)
        foundation_rows=[(100, 100)],
    )

    def _fake_table(name, meta, autoload_with=None):
        t = MagicMock()
        t.c.id = MagicMock()
        t.c.grant_id = MagicMock()
        t.c.grant_id.op.return_value = lambda *a, **k: MagicMock()
        t.update.return_value.where.return_value = MagicMock()
        return t

    select_mock = MagicMock()
    select_mock.where.return_value = select_mock
    with patch.object(migration.sa, "Table", side_effect=_fake_table), \
         patch.object(migration.sa, "MetaData", return_value=MagicMock()), \
         patch.object(migration.sa, "select", return_value=select_mock):
        rewritten, unchanged = migration._rewrite_saved_grant_ids(conn, log=lambda *a, **k: None)

    assert rewritten == 0
    assert unchanged == 0
    assert conn.updates == []


def test_upgrade_uses_get_bind(monkeypatch):
    """upgrade() delegates to _rewrite_saved_grant_ids with op.get_bind()."""
    import alembic.op as op_mod

    fake_conn = object()
    monkeypatch.setattr(op_mod, "get_bind", lambda: fake_conn)

    with patch.object(migration, "_rewrite_saved_grant_ids") as mock_rewrite:
        migration.upgrade()
        mock_rewrite.assert_called_once_with(fake_conn)
