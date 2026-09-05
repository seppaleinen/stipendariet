"""
Admin enrichment-sources CRUD API tests.

Hermetic unit tests for /api/admin/sources (list/get/create/update/delete).
The DB session is replaced with an in-memory fake so no network or real
database is touched (conftest.py already mocks app.db.database globally).

The endpoints in app/api/admin/sources.py use the SQLAlchemy 2.0 style
``db.execute(select/insert/update/delete)`` API, so the fake session
dispatches on the statement class and keeps a small in-memory row store.
"""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _admin_headers():
    """Bearer JWT headers for an admin user (matches test_admin_functionality_bdd.py)."""
    from app.core.config import settings

    email = settings.ADMIN_EMAIL or "admin@test.com"
    token = create_access_token({"sub": email, "email": email, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# In-memory fake session
# ---------------------------------------------------------------------------


class _FakeSource:
    """Plain stand-in for an EnrichmentSource ORM row (attribute-based)."""

    def __init__(self, source_id, url, is_official=False, confidence=0.0,
                 source_type=None, foundation_id=None):
        self.id = source_id
        self.foundation_id = foundation_id
        self.url = url
        self.source_type = source_type
        self.is_official = is_official
        self.confidence = confidence
        now = datetime.utcnow()
        self.last_validated = now
        self.created_at = now


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


def _and_clauses(clause):
    """Flatten a where-clause tree into a list of binary (==) expressions.

    SQLAlchemy composes chained ``.where()``/``and_()`` predicates into a
    BooleanClauseList; this fake only needs to understand AND combinations of
    simple equality comparisons.
    """
    if type(clause).__name__ == "BooleanClauseList":
        out = []
        for sub in clause.clauses:
            out.extend(_and_clauses(sub))
        return out
    return [clause]


def _unwrap(value):
    """Unwrap a SQLAlchemy BindParameter (or return the raw value)."""
    from sqlalchemy.sql.expression import BindParameter

    return value.value if isinstance(value, BindParameter) else value


def _row_matches(row, clause):
    """Evaluate a where-clause against a _FakeSource row (== comparisons only)."""
    left = getattr(clause, "left", None)
    right = getattr(clause, "right", None)
    if left is None or right is None:
        return True  # Unknown predicate — keep the row (lenient)
    col = getattr(left, "name", None)
    if col is None:
        return True
    value = getattr(right, "value", None)
    if value is None:
        # Boolean comparisons compile right-hand side to the true()/false()
        # singletons (True_/False_) rather than BindParameter.
        kind = type(right).__name__
        if kind == "True_":
            value = True
        elif kind == "False_":
            value = False
        else:
            value = getattr(right, "effective_value", None)
    return getattr(row, col, None) == value


def _extract_values(stmt):
    """Read insert/update value dicts into {column_name: python value}.

    Keys may be Column objects (endpoint flow) or plain strings (kwargs),
    and values may be pre-bound BindParameters — normalize both.
    """
    out = {}
    for key, value in stmt._values.items():
        name = key if isinstance(key, str) else getattr(key, "name", key)
        if isinstance(name, str):
            out[name] = _unwrap(value)
    return out


class _FakeSourceSession:
    """In-memory session supporting the statement shapes sources.py emits."""

    def __init__(self):
        self._rows = []
        self._next_id = 1

    # -- statement dispatch -------------------------------------------------

    def execute(self, stmt):
        name = type(stmt).__name__
        if name == "Select":
            return self._select(stmt)
        if name == "Insert":
            return self._insert(stmt)
        if name == "Update":
            return self._update(stmt)
        if name == "Delete":
            return self._delete(stmt)
        raise AssertionError(f"test fake: unexpected statement type {name}")

    def commit(self):
        pass

    def close(self):
        pass

    # -- handlers -----------------------------------------------------------

    def _select(self, stmt):
        rows = list(self._rows)
        where = getattr(stmt, "whereclause", None)
        if where is not None:
            rows = [r for r in rows if all(_row_matches(r, c) for c in _and_clauses(where))]
        clauses = getattr(stmt, "_order_by_clauses", None) or []
        if clauses:
            rows = sorted(rows, key=lambda r: r.id, reverse=True)
        limit = getattr(stmt, "_limit", None)
        if limit is not None:
            rows = rows[:limit]
        return _FakeResult(rows)

    def _insert(self, stmt):
        values = _extract_values(stmt)
        row = _FakeSource(
            source_id=self._next_id,
            url=values.get("url", ""),
            is_official=values.get("is_official", False),
            confidence=values.get("confidence", 0.0),
            source_type=values.get("source_type"),
            foundation_id=values.get("foundation_id"),
        )
        self._next_id += 1
        self._rows.append(row)
        return _FakeResult([])

    def _update(self, stmt):
        where = getattr(stmt, "whereclause", None)
        values = _extract_values(stmt)
        for row in self._rows:
            if where is not None and not all(_row_matches(row, c) for c in _and_clauses(where)):
                continue
            for name, value in values.items():
                setattr(row, name, value)
        return _FakeResult([])

    def _delete(self, stmt):
        where = getattr(stmt, "whereclause", None)
        kept = []
        for row in self._rows:
            if where is not None and all(_row_matches(row, c) for c in _and_clauses(where)):
                continue
            kept.append(row)
        self._rows = kept
        return _FakeResult([])


def _patched_session():
    """Context manager: run the TestClient endpoint against a fresh fake session."""
    return patch("app.api.admin.sources._get_session", lambda: _FakeSourceSession())


def _insert_direct(session, payload):
    row = _FakeSource(
        source_id=session._next_id,
        url=payload.url,
        is_official=payload.is_official,
        confidence=payload.confidence,
        source_type=payload.source_type,
        foundation_id=payload.foundation_id,
    )
    session._next_id += 1
    session._rows.append(row)
    return row


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_sources_empty():
    with _patched_session():
        response = client.get("/api/admin/sources", headers=_admin_headers())
    assert response.status_code == 200
    assert response.json() == []


def test_list_sources_after_creation_and_filters():
    session = _FakeSourceSession()
    _insert_direct(session, _mk_payload("https://annsansradstod.se", source_type="aggregator", foundation_id=1, is_official=False))
    _insert_direct(session, _mk_payload("https://stiftelsen.se", source_type="official", foundation_id=2, is_official=True))
    _insert_direct(session, _mk_payload("https://blogg.se", source_type="blog", foundation_id=None, is_official=False))

    with patch("app.api.admin.sources._get_session", lambda: session):
        # All rows
        resp = client.get("/api/admin/sources", headers=_admin_headers())
        assert resp.status_code == 200
        assert [s["id"] for s in resp.json()] == [1, 2, 3]

        # Filter by foundation_id
        resp = client.get("/api/admin/sources?foundation_id=1", headers=_admin_headers())
        assert [s["id"] for s in resp.json()] == [1]

        # Filter by is_official
        resp = client.get("/api/admin/sources?is_official=true", headers=_admin_headers())
        assert [s["id"] for s in resp.json()] == [2]

        # Filter by source_type
        resp = client.get("/api/admin/sources?source_type=blog", headers=_admin_headers())
        assert [s["id"] for s in resp.json()] == [3]

        # Combined filters (AND)
        resp = client.get(
            "/api/admin/sources?is_official=true&source_type=official", headers=_admin_headers()
        )
        assert [s["id"] for s in resp.json()] == [2]

        # No match
        resp = client.get("/api/admin/sources?source_type=directory", headers=_admin_headers())
        assert resp.json() == []


def test_list_sources_requires_admin_auth():
    with _patched_session():
        response = client.get("/api/admin/sources")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------


def test_get_source_found():
    session = _FakeSourceSession()
    _insert_direct(session, _mk_payload("https://stiftelsen.se", source_type="official"))
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.get("/api/admin/sources/1", headers=_admin_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["url"] == "https://stiftelsen.se"
    assert data["source_type"] == "official"
    assert data["is_official"] is False
    assert data["last_validated"] is not None
    assert data["created_at"] is not None


def test_get_source_not_found():
    session = _FakeSourceSession()
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.get("/api/admin/sources/999", headers=_admin_headers())
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_source_success():
    session = _FakeSourceSession()
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.post(
            "/api/admin/sources",
            json={
                "url": "https://stiftelsen.se",
                "is_official": True,
                "confidence": 0.9,
                "source_type": "official",
                "foundation_id": 7,
            },
            headers=_admin_headers(),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["url"] == "https://stiftelsen.se"
    assert data["is_official"] is True
    assert data["confidence"] == 0.9
    assert data["source_type"] == "official"
    assert data["foundation_id"] == 7

    # Persisted — a subsequent list sees it
    with patch("app.api.admin.sources._get_session", lambda: session):
        listing = client.get("/api/admin/sources", headers=_admin_headers())
    assert [s["url"] for s in listing.json()] == ["https://stiftelsen.se"]


def test_create_source_duplicate_url_allowed():
    """sources.py has no unique constraint on url: a second create with the
    same URL succeeds, both rows are listed, and the response reflects the
    newest row (re-fetch orders by id desc)."""
    session = _FakeSourceSession()
    payload = {"url": "https://annsansradstod.se", "source_type": "aggregator"}
    with patch("app.api.admin.sources._get_session", lambda: session):
        first = client.post("/api/admin/sources", json=payload, headers=_admin_headers())
        second = client.post("/api/admin/sources", json=payload, headers=_admin_headers())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == 1
    assert second.json()["id"] == 2

    with patch("app.api.admin.sources._get_session", lambda: session):
        listing = client.get("/api/admin/sources", headers=_admin_headers())
    assert [s["id"] for s in listing.json()] == [1, 2]
    # The newest row for the duplicate URL is returned by a create re-fetch
    with patch("app.api.admin.sources._get_session", lambda: session):
        third = client.post("/api/admin/sources", json=payload, headers=_admin_headers())
    assert third.json()["id"] == 3


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_source_fields():
    session = _FakeSourceSession()
    _insert_direct(session, _mk_payload("https://old.se", source_type="blog"))
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.put(
            "/api/admin/sources/1",
            json={"url": "https://new.se", "is_official": True, "confidence": 0.7, "source_type": "official"},
            headers=_admin_headers(),
        )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://new.se"
    assert data["is_official"] is True
    assert data["confidence"] == 0.7
    assert data["source_type"] == "official"

    # Untouched fields preserved (foundation_id was never sent)
    with patch("app.api.admin.sources._get_session", lambda: session):
        got = client.get("/api/admin/sources/1", headers=_admin_headers())
    assert got.json()["foundation_id"] is None


def test_update_source_missing_404():
    session = _FakeSourceSession()
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.put(
            "/api/admin/sources/999",
            json={"url": "https://nope.se"},
            headers=_admin_headers(),
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_source_then_missing():
    session = _FakeSourceSession()
    _insert_direct(session, _mk_payload("https://stiftelsen.se"))
    with patch("app.api.admin.sources._get_session", lambda: session):
        deleted = client.delete("/api/admin/sources/1", headers=_admin_headers())
    assert deleted.status_code == 200
    assert deleted.json() == {"detail": "Source deleted successfully"}

    with patch("app.api.admin.sources._get_session", lambda: session):
        gone = client.get("/api/admin/sources/1", headers=_admin_headers())
        listing = client.get("/api/admin/sources", headers=_admin_headers())
    assert gone.status_code == 404
    assert listing.json() == []


def test_delete_source_missing_404():
    session = _FakeSourceSession()
    with patch("app.api.admin.sources._get_session", lambda: session):
        response = client.delete("/api/admin/sources/999", headers=_admin_headers())
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_payload(url, source_type=None, foundation_id=None, is_official=False):
    """Build an EnrichmentSourceCreate payload without going through the API."""
    from app.api.admin.sources import EnrichmentSourceCreate

    return EnrichmentSourceCreate(
        url=url,
        is_official=is_official,
        source_type=source_type,
        foundation_id=foundation_id,
    )


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
