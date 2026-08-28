"""
Unit tests for `_cleanup_orphan_saved_grants` (issue #21).

Verifies that the garbage-collection function:
  - Deletes SavedGrant rows whose grant_id is "foundation-N" where no
    Foundation row has foundation_id = N;
  - Deletes SavedGrant rows whose grant_id is "grant-N" where no Grant row
    has id = N;
  - Leaves live SavedGrant rows (matching foundation or grant) untouched;
  - Is idempotent — running twice produces the same result;
  - Is a no-op when the saved_grants table is empty.
"""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "app/foundation/sync_service.py"
_spec = importlib.util.spec_from_file_location("sync_service_under_test", _MIGRATION_PATH)
assert _spec and _spec.loader, "could not load sync_service module"
sync_service = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_service)

_cleanup_orphan_saved_grants = sync_service._cleanup_orphan_saved_grants


class _Row:
    """Simple indexable row mimicking a DB result row (column-access by index)."""

    def __init__(self, values):
        self._v = values

    def __getitem__(self, idx):
        return self._v[idx]

    def __repr__(self):
        return f"_Row({self._v!r})"


class _FakeConn:
    """Fake DB connection / session that records DELETE statements.

    `_cleanup_orphan_saved_grants` executes SQL in this order:

      1. SELECT foundation_id FROM foundations
      2. SELECT id, grant_id FROM saved_grants   (pass A — find foundation orphans)
      3. DELETE FROM saved_grants WHERE id IN ...  (foundation orphans, optional)
      4. SELECT id FROM grants
      5. SELECT id, grant_id FROM saved_grants   (pass B — find grant orphans)
      6. DELETE FROM saved_grants WHERE id IN ...  (grant orphans, optional)
      7. db.commit()

    We pre-build iterators of results; each execute() call consumes the next
    one. DELETE calls are detected by statement text and are recorded, not
    returned as a fake result.
    """

    def __init__(self, foundation_rows, saved_grant_rows, grant_rows):
        self.deleted_ids: list[int] = []
        self.commit_called = False

        def _make_result(rows):
            """Return a result object that has .fetchall() returning `rows`."""
            wrapped = [_Row(x) for x in rows]
            m = MagicMock()
            m.fetchall.return_value = wrapped
            # Prevent MagicMock from yielding its children when iterated
            m.__iter__ = lambda self: iter(wrapped)
            return m

        # Select results: (1) foundations, (2A) saved_grants A, (3) grants, (4A) saved_grants B
        self._select_results = iter([
            _make_result(foundation_rows),    # step 1
            _make_result(saved_grant_rows),  # step 2
            _make_result(grant_rows),         # step 3
            _make_result(saved_grant_rows),  # step 4  (only reached after foundation DELETE)
        ])

    def execute(self, statement, *args, **kwargs):
        # Detect DELETE vs SELECT by looking at the statement text.
        # We don't use the args/kwargs in this test fake.
        stmt_str = str(statement).upper()
        if "DELETE" in stmt_str:
            # params is passed as positional arg or in args
            params = args[0] if args else kwargs.get("params")
            if params and "ids" in params:
                self.deleted_ids.extend(params["ids"])
            return MagicMock()  # DELETE doesn't need a result object
        # Otherwise it's a SELECT — return the next pre-built result.
        return next(self._select_results)

    def commit(self):
        self.commit_called = True


def test_foundation_orphans_deleted():
    """Foundation-N SavedGrant rows with no matching foundation_id=N are deleted."""
    fake = _FakeConn(
        foundation_rows=[(1,), (2,), (3,)],   # only foundation_ids 1, 2, 3 exist
        saved_grant_rows=[
            (10, "foundation-1"),       # live
            (20, "foundation-99999"),   # orphan — no foundation_id=99999
            (30, "grant-1"),            # not a foundation orphan, should survive
        ],
        grant_rows=[(1,)],
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert 20 in fake.deleted_ids  # orphan deleted
    assert 10 not in fake.deleted_ids
    assert 30 not in fake.deleted_ids


def test_grant_orphans_deleted():
    """Grant-N SavedGrant rows with no matching grants.id=N are deleted.

    We provide a matching foundation so that the foundation- prefix row is NOT
    a foundation orphan — we are isolating the grant-orphan logic here.
    """
    fake = _FakeConn(
        foundation_rows=[(1,)],  # foundation_id=1 exists → foundation-1 is NOT an orphan
        saved_grant_rows=[
            (10, "foundation-1"),  # live — matching foundation exists
            (20, "grant-1"),       # live — grant id=1 exists
            (30, "grant-99999"),   # orphan — no grant id=99999
        ],
        grant_rows=[(1,)],  # only grant.id=1 exists
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert 30 in fake.deleted_ids  # orphan deleted
    assert 10 not in fake.deleted_ids  # foundation-1 is live
    assert 20 not in fake.deleted_ids  # grant-1 is live


def test_live_saved_grant_preserved():
    """A SavedGrant with a matching live foundation is NOT deleted."""
    fake = _FakeConn(
        foundation_rows=[(7,)],  # foundation_id=7 exists
        saved_grant_rows=[
            (10, "foundation-7"),      # live
            (20, "foundation-99999"),  # orphan
        ],
        grant_rows=[],
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert 10 not in fake.deleted_ids  # live — NOT deleted
    assert 20 in fake.deleted_ids      # orphan — deleted


def test_grant_prefix_rows_untouched():
    """A SavedGrant with grant-N where a matching grant.id=N exists is NOT deleted."""
    fake = _FakeConn(
        foundation_rows=[],
        saved_grant_rows=[
            (10, "grant-1"),         # live
            (20, "grant-99999"),     # orphan
        ],
        grant_rows=[(1,)],  # grant.id=1 exists
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert 10 not in fake.deleted_ids  # live — NOT deleted
    assert 20 in fake.deleted_ids      # orphan — deleted


def test_cleanup_is_idempotent():
    """Running cleanup twice produces the same result (idempotent)."""
    # First run: orphans 20 (foundation) and 40 (grant)
    fake_first = _FakeConn(
        foundation_rows=[(7,)],
        saved_grant_rows=[
            (10, "foundation-7"),       # live
            (20, "foundation-99999"),    # orphan
            (30, "grant-1"),             # live
            (40, "grant-99999"),         # orphan
        ],
        grant_rows=[(1,)],
    )
    _cleanup_orphan_saved_grants(fake_first)
    assert sorted(fake_first.deleted_ids) == [20, 40]

    # Second run: nothing left to delete
    fake_second = _FakeConn(
        foundation_rows=[(7,)],
        saved_grant_rows=[
            (10, "foundation-7"),  # only survivors
            (30, "grant-1"),
        ],
        grant_rows=[(1,)],
    )
    _cleanup_orphan_saved_grants(fake_second)
    assert fake_second.deleted_ids == []  # no orphans remain


def test_empty_table_noop():
    """No SavedGrant rows — cleanup is a no-op and does not raise."""
    fake = _FakeConn(
        foundation_rows=[],
        saved_grant_rows=[],  # empty table
        grant_rows=[],
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert fake.deleted_ids == []


def test_mixed_live_and_orphan_rows():
    """Both foundation and grant orphans deleted together; live rows preserved."""
    fake = _FakeConn(
        foundation_rows=[(1,), (2,), (5,)],
        saved_grant_rows=[
            (10, "foundation-1"),       # live
            (20, "foundation-2"),        # live
            (30, "foundation-99998"),  # orphan
            (40, "grant-1"),            # live
            (50, "grant-99997"),        # orphan
        ],
        grant_rows=[(1,), (2,), (6,)],
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    assert 10 not in fake.deleted_ids  # live
    assert 20 not in fake.deleted_ids  # live
    assert 40 not in fake.deleted_ids  # live
    assert 30 in fake.deleted_ids       # foundation orphan
    assert 50 in fake.deleted_ids       # grant orphan


def test_non_string_grant_id_skipped():
    """SavedGrant rows with non-string grant_id are ignored (not deleted)."""
    fake = _FakeConn(
        foundation_rows=[],
        saved_grant_rows=[
            (10, "foundation-1"),
            (20, 123),   # non-string — unexpected, but must not cause issues
            (30, None),  # NULL — must not cause issues
        ],
        grant_rows=[(1,)],
    )
    _cleanup_orphan_saved_grants(fake)
    assert fake.commit_called
    # foundation_id=1 does not exist → 10 is an orphan and gets deleted
    assert 10 in fake.deleted_ids
    # non-string / NULL rows are skipped — NOT deleted
    assert 20 not in fake.deleted_ids
    assert 30 not in fake.deleted_ids
