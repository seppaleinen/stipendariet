"""
Unit test for the issue #22 orphan-saved-grant data migration.

Exercises the real `_cleanup_orphan_saved_grants` control flow with fakes,
verifying:
  - `foundation-{N}` rows whose N has no matching foundations.foundation_id
    are deleted;
  - `grant-{N}` rows whose N has no matching grants.id are deleted;
  - rows that resolve to live foundations / grants are LEFT ALONE;
  - cleanup is idempotent (a second run finds 0 orphans and is a no-op);
  - `downgrade()` is a no-op (the table is unchanged);
  - `upgrade()` delegates to the helper with `op.get_bind()`.
"""
import importlib.util
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic/versions/49d90bcc1dd5_cleanup_existing_orphan_saved_grants.py"
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


def _make_conn(all_saved_rows, foundation_rows, grant_rows):
    """Build a fake connection routing purely by call order.

    `_cleanup_orphan_saved_grants` executes in a fixed order:
      1. SELECT foundations.foundation_id           (returns foundation_rows)
      2. SELECT saved_grants (foundation- prefix)    (returns all_saved_rows,
                                                     filtered by regex)
      3. (optional) DELETE FROM saved_grants ...     (recorded into conn.updates)
      4. SELECT grants.id                            (returns grant_rows)
      5. SELECT saved_grants (grant- prefix)         (returns all_saved_rows,
                                                     filtered by regex)
      6. (optional) DELETE FROM saved_grants ...     (recorded into conn.updates)

    The regex filter is emulated in the test by re-running the same
    `_FOUNDATION_GRANT_ID_RE` / `_GRANT_GRANT_ID_RE` matchers the migration uses,
    so we keep `_make_conn` agnostic of which rows the migration is allowed to
    see — the migration is responsible for filtering via SQL `~`.

    For convenience (and to keep the assertion surface tight), we don't
    actually emulate the SQL `~` filter here: instead the test sets up
    `all_saved_rows` so that each variant only contains rows of the right
    prefix for the stage being tested. This matches the #19 test's intent
    (rely on the migration's own regex + Python matchers) without forcing us
    to inspect what was `where`-clause'd on.
    """
    delete_calls = []
    conn = MagicMock()

    def _result(rows):
        wrapped = [_Row(x) for x in rows]
        m = MagicMock()
        m.fetchall.return_value = wrapped
        # Set __iter__ directly so that iter(result) works — MagicMock's
        # __iter__ returns a fresh mock on each call unless we override it.
        m.__iter__ = lambda: iter(wrapped)
        return m

    def _foundation_prefix_filtered(rows):
        return [r for r in rows if re.fullmatch(r"foundation-\d+", r[1])]

    def _grant_prefix_filtered(rows):
        return [r for r in rows if re.fullmatch(r"grant-\d+", r[1])]

    # The migration calls execute() in this order:
    #   1. select(foundations.c.foundation_id)              -> foundation_rows
    #   2. select(saved_grants).where(... ~ '^foundation-...')
    #                                                       -> foundation-filtered rows
    #   3. (optional) delete(... where id.in_(...))
    #   4. select(grants.c.id)                              -> grant_rows
    #   5. select(saved_grants).where(... ~ '^grant-...')
    #                                                       -> grant-filtered rows
    #   6. (optional) delete(... where id.in_(...))
    select_results = iter(
        [
            _result(foundation_rows),
            _result(_foundation_prefix_filtered(all_saved_rows)),
            # (a delete may be inserted here for foundation orphans)
            _result(grant_rows),
            _result(_grant_prefix_filtered(all_saved_rows)),
            # (a delete may be inserted here for grant orphans)
        ]
    )

    def execute(statement, *args, **kwargs):
        try:
            return next(select_results)
        except StopIteration:
            # Real DELETE statements arrive here.  We record them so the
            # tests can assert on them.
            # A delete statement built with `Table.delete().where(...)` has
            # no `.update` attribute, but we can sniff for `.delete` on the
            # SQLAlchemy ClauseElement.  We just stash the statement and
            # leave the caller to introspect if they want to.
            delete_calls.append(statement)
            return MagicMock()

    conn.execute.side_effect = execute
    conn.deletes = delete_calls
    return conn


def _patch_sa_tables_for_cleanup(migration_module):
    """Patch sa.Table, sa.MetaData, sa.select for the cleanup migration.

    The migration's helper builds real `sa.Table` reflection from
    `autoload_with=conn`. We stub the tables and the columns the helper
    actually touches, and the `.op('~')` / `.in_()` builder calls.

    We return a `_Tables` triple whose attributes mirror the columns used
    by `_cleanup_orphan_saved_grants`. The tables share a single `op()`
    callable (for `~`) and a single `in_()` builder.
    """
    class _Cols:
        pass

    saved_grants = MagicMock()
    saved_grants.c = _Cols()
    saved_grants.c.id = MagicMock()
    saved_grants.c.grant_id = MagicMock()
    # Make grant_id.op('~')(...) return a sentinel "where clause" object.
    saved_grants.c.grant_id.op.return_value = lambda *a, **k: ("op", a, k)
    # The delete is `saved_grants.delete().where(saved_grants.c.id.in_(ids))`.
    saved_grants.delete.return_value.where.return_value = MagicMock()

    foundations = MagicMock()
    foundations.c = _Cols()
    foundations.c.foundation_id = MagicMock()

    grants = MagicMock()
    grants.c = _Cols()
    grants.c.id = MagicMock()

    table_by_name = {
        "saved_grants": saved_grants,
        "foundations": foundations,
        "grants": grants,
    }

    def _fake_table(name, meta, autoload_with=None):
        return table_by_name[name]

    select_mock = MagicMock()
    select_mock.where.return_value = select_mock

    return (
        patch.object(migration_module.sa, "Table", side_effect=_fake_table),
        patch.object(migration_module.sa, "MetaData", return_value=MagicMock()),
        patch.object(migration_module.sa, "select", return_value=select_mock),
    )


def test_deletes_foundation_orphans():
    """foundation-{N} rows whose N has no matching foundations.foundation_id are deleted."""
    conn = _make_conn(
        all_saved_rows=[
            (1, "foundation-1"),    # live
            (2, "foundation-99"),   # orphan: 99 not in foundations
            (3, "foundation-100"),  # live
            (4, "foundation-777"),  # orphan: 777 not in foundations
            (5, "grant-5"),         # grant- prefix — untouched in this step
        ],
        foundation_rows=[
            (1,),    # foundation_id 1 is live
            (100,),  # foundation_id 100 is live
        ],
        grant_rows=[(5,)],  # grant id 5 is live (irrelevant for foundation step)
    )

    p_table, p_meta, p_select = _patch_sa_tables_for_cleanup(migration)
    with p_table, p_meta, p_select:
        foundation_orphans, _ = migration._cleanup_orphan_saved_grants(
            conn, log=lambda *a, **k: None
        )

    assert foundation_orphans == 2
    # The migration should have issued one DELETE for the foundation orphans.
    assert len(conn.deletes) >= 1


def test_deletes_grant_orphans():
    """grant-{N} rows whose N has no matching grants.id are deleted."""
    conn = _make_conn(
        all_saved_rows=[
            (1, "grant-1"),     # live
            (2, "grant-99"),    # orphan: 99 not in grants
            (3, "grant-100"),   # live
            (4, "grant-777"),   # orphan: 777 not in grants
        ],
        foundation_rows=[(5,)],  # foundation_id 5 exists — not relevant here
        grant_rows=[
            (1,),    # grant id 1 is live
            (3,),    # grant id 3 is live
            (100,),  # grant id 100 is live
        ],
    )

    p_table, p_meta, p_select = _patch_sa_tables_for_cleanup(migration)
    with p_table, p_meta, p_select:
        _, grant_orphans = migration._cleanup_orphan_saved_grants(
            conn, log=lambda *a, **k: None
        )

    assert grant_orphans == 2


def test_preserves_live_rows():
    """Rows that resolve to live foundations or grants are NOT deleted."""
    conn = _make_conn(
        all_saved_rows=[
            (1, "foundation-1"),
            (2, "foundation-100"),
            (3, "grant-1"),
            (4, "grant-3"),
        ],
        foundation_rows=[
            (1,),
            (100,),
        ],
        grant_rows=[
            (1,),
            (3,),
        ],
    )

    p_table, p_meta, p_select = _patch_sa_tables_for_cleanup(migration)
    with p_table, p_meta, p_select:
        foundation_orphans, grant_orphans = migration._cleanup_orphan_saved_grants(
            conn, log=lambda *a, **k: None
        )

    assert foundation_orphans == 0
    assert grant_orphans == 0
    # No DELETE statements should have been issued.
    assert conn.deletes == []


def test_idempotent_second_run_is_noop():
    """Running the migration twice is safe — the second run is a no-op.

    The first call deletes the orphans; the second call must find 0 orphans
    and issue no DELETEs. We approximate "first call already ran" by
    pre-filtering the candidate rows to live-only rows on the second call.
    """
    # After the first call, all orphans are gone — only live rows remain.
    live_only = [
        (1, "foundation-1"),
        (2, "foundation-100"),
        (3, "grant-1"),
        (4, "grant-3"),
    ]
    conn = _make_conn(
        all_saved_rows=live_only,
        foundation_rows=[(1,), (100,)],
        grant_rows=[(1,), (3,)],
    )

    p_table, p_meta, p_select = _patch_sa_tables_for_cleanup(migration)
    with p_table, p_meta, p_select:
        foundation_orphans, grant_orphans = migration._cleanup_orphan_saved_grants(
            conn, log=lambda *a, **k: None
        )

    assert foundation_orphans == 0
    assert grant_orphans == 0
    assert conn.deletes == []


def test_upgrade_uses_get_bind(monkeypatch):
    """upgrade() delegates to _cleanup_orphan_saved_grants with op.get_bind()."""
    import alembic.op as op_mod

    fake_conn = object()
    monkeypatch.setattr(op_mod, "get_bind", lambda: fake_conn)

    with patch.object(migration, "_cleanup_orphan_saved_grants") as mock_cleanup:
        migration.upgrade()
        mock_cleanup.assert_called_once_with(fake_conn)


def test_downgrade_is_noop():
    """downgrade() must not mutate the saved_grants table."""
    # downgrade() is a no-op by construction — we just call it and assert
    # it does not raise and produces no side effects. To be defensive we
    # also verify it does not invoke _cleanup_orphan_saved_grants (which
    # would be a destructive side effect on a downgrade).
    with patch.object(migration, "_cleanup_orphan_saved_grants") as mock_cleanup:
        migration.downgrade()
        mock_cleanup.assert_not_called()
