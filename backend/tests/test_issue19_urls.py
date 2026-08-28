"""
Issue #19 regression tests.

Verifies that URL identifiers use the canonical external foundation id
(`foundation-{foundation_id}`), never the DB surrogate id (`foundation-{db_id}`),
across the grants, funding, and search routers — and that a synthetic
"clear database + re-sync" (which renumbers `foundations.id`) does NOT break
canonical lookups.

NOTE (env): the LSP "Import could not be resolved" diagnostics are pre-existing
environment noise, not caused by these files. Tests run inside backend/.venv.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _foundation(db_id, foundation_id, name="Test Foundation"):
    """Build a MagicMock Foundation row with a distinct db surrogate vs external id."""
    m = MagicMock()
    m.id = db_id
    m.foundation_id = foundation_id
    m.name = name
    m.orgnr = "123456-7890"
    m.purpose = "Syfte"
    m.translated_purpose = "Purpose"
    m.summary = "summary"
    m.address = "Gata 1"
    m.postnr = "12345"
    m.postort = "Postort"
    m.co_address = None
    m.phone = None
    m.signature = None
    m.roles = []
    m.parsed_service_area = None
    m.category = None
    m.website_url = None
    m.application_deadline = None
    m.application_start = None
    m.application_method = None
    m.contact_email = None
    m.contact_phone = None
    m.who_can_apply = None
    m.target_groups = None
    m.funding_areas = None
    m.tags = None
    return m


def _grant():
    m = MagicMock()
    m.id = 456
    m.name = "Grant"
    m.provider = "Provider AB"
    m.summary = "sum"
    m.description = "desc"
    m.amount = "1 000 kr"
    m.deadline = None
    m.cadence = "Årlig"
    m.link = "https://example.com/grant"
    m.tags = ["tag"]
    m.category = None
    return m


# =============================================================================
# Grants list & detail — canonical id
# =============================================================================

class TestGrantsCanonicalIds:
    def _override_db(self, rows):
        """Override get_db to return a session whose query chain yields rows."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value = mock_db.query.return_value
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows
        mock_db.query.return_value.count.return_value = len(rows)
        from app.db.database import get_db as real_get_db

        def _gen():
            yield mock_db

        app.dependency_overrides[real_get_db] = _gen
        return mock_db

    def _clear_db(self):
        from app.db.database import get_db as real_get_db
        app.dependency_overrides.pop(real_get_db, None)

    def test_list_emits_canonical_foundation_id(self):
        """Grants list `id` uses foundation_{foundation_id}, never db id."""
        row = _foundation(db_id=7, foundation_id=700, name="Fond")
        self._override_db([row])
        try:
            resp = client.get("/api/grants")
            assert resp.status_code == 200
            assert resp.json()["grants"][0]["id"] == "foundation-700"
            assert resp.json()["grants"][0]["id"] != "foundation-7"
        finally:
            self._clear_db()

    def test_get_grant_resolves_canonical_foundation_id(self):
        """GET /api/grants/foundation-700 resolves by foundation_id and echoes canonical."""
        with patch("app.api.v1.routers.grants.crud.get_foundation") as mock_get_foundation:
            mock_get_foundation.return_value = _foundation(db_id=7, foundation_id=700)
            resp = client.get("/api/grants/foundation-700")
            assert resp.status_code == 200
            assert resp.json()["id"] == "foundation-700"
            # Lookup used the EXTERNAL id (700), not the db surrogate (7).
            mock_get_foundation.assert_called_once()
            assert mock_get_foundation.call_args[0][1] == 700

    def test_get_grant_legacy_db_id_does_not_resolve_foundation(self):
        """A bare numeric (db) id no longer resolves a foundation via the legacy path.

        With canonical-only resolution, a numeric id can only match a legacy grant
        row. Here no grant exists, so it 404s — the foundation fallback is gone.
        """
        with patch("app.api.v1.routers.grants.crud.get_grant") as mock_get_grant:
            mock_get_grant.return_value = None
            resp = client.get("/api/grants/7")
            assert resp.status_code == 404


# =============================================================================
# Funding — canonical id
# =============================================================================

class TestFundingCanonicalIds:
    def _override_db(self):
        mock_db = MagicMock()
        from app.db.database import get_db as real_get_db

        def _gen():
            yield mock_db

        app.dependency_overrides[real_get_db] = _gen
        return mock_db

    def _clear_db(self):
        from app.db.database import get_db as real_get_db
        app.dependency_overrides.pop(real_get_db, None)

    @patch("app.api.v1.routers.funding.crud.get_grants")
    @patch("app.api.v1.routers.funding.crud.get_foundations")
    def test_list_emits_canonical_foundation_id(self, mock_get_foundations, mock_get_grants):
        """Funding list emits foundation-{foundation_id}."""
        self._override_db()
        try:
            mock_get_foundations.return_value = [
                _foundation(db_id=7, foundation_id=700, name="Fond")
            ]
            mock_get_grants.return_value = []
            resp = client.get("/api/funding")
            assert resp.status_code == 200
            data = resp.json()
            assert data[0]["id"] == "foundation-700"
        finally:
            self._clear_db()

    def test_get_funding_foundation_canonical(self):
        """GET /api/funding/foundation-700 resolves via foundation_id and echoes canonical."""
        self._override_db()
        try:
            with patch("app.api.v1.routers.funding.crud.get_foundation") as mock_get_foundation:
                mock_get_foundation.return_value = _foundation(db_id=7, foundation_id=700)
                resp = client.get("/api/funding/foundation-700")
                assert resp.status_code == 200
                assert resp.json()["id"] == "foundation-700"
                assert mock_get_foundation.call_args[0][1] == 700
        finally:
            self._clear_db()

    def test_get_funding_legacy_numeric_foundation_not_resolved(self):
        """A bare numeric id can only be a legacy grant; missing grant -> 404."""
        self._override_db()
        try:
            with patch("app.api.v1.routers.funding.crud.get_grant") as mock_get_grant:
                mock_get_grant.return_value = None
                resp = client.get("/api/funding/7")
                assert resp.status_code == 404
        finally:
            self._clear_db()


# =============================================================================
# Search payload — canonical id
# =============================================================================

class TestSearchCanonicalIds:
    def test_search_payload_id_is_canonical_string(self):
        """Search results `id` is a canonical `foundation-{foundation_id}` string."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            _foundation(db_id=7, foundation_id=700)
        ]
        from app.db.database import get_db as real_get_db

        def _gen():
            yield mock_db

        app.dependency_overrides[real_get_db] = _gen
        # Pre-existing quirk (out of scope for #19): search.py calls
        # `models.Foundation.tags.any(query)` where tags is a plain JSON column
        # that has no `.any()` comparator — it raises during expression
        # construction. We stub it here (plus `or_`) so this unit test can
        # exercise the canonical-id payload without a live Postgres.
        from app.db import models as db_models

        tags_mock = MagicMock()
        tags_mock.contains.return_value = MagicMock()
        with patch("app.api.v1.routers.search.or_", return_value=MagicMock()), \
             patch.object(db_models.Foundation, "tags", tags_mock):
            try:
                resp = client.get("/api/search/foundations", params={"query": "test", "limit": 10})
                assert resp.status_code == 200
                data = resp.json()
                assert data[0]["id"] == "foundation-700"
            finally:
                app.dependency_overrides.pop(real_get_db, None)


# =============================================================================
# Synthetic "clear database + re-sync" stability
# =============================================================================

def test_canonical_grant_roundtrip_survives_db_renumber():
    """A canonical grant id is stable across a clear-database + re-import.

    Simulates: user saves grant 'foundation-700' (the canonical external id).
    Admin clears the DB (delete_all_foundations) and re-syncs from the external
    API. The new rows get fresh db surrogate ids (foundation.id renumbers, e.g.
    from 7 -> 1), but foundation_id (700) is stable. The canonical lookup must
    still resolve — proving the surrogate renumber no longer breaks saved links.
    """
    with patch("app.api.v1.routers.grants.crud.get_foundation") as mock_get_foundation:
        # After re-sync: same foundation_id (700), DIFFERENT db id (now 1).
        mock_get_foundation.return_value = _foundation(db_id=1, foundation_id=700)
        resp = client.get("/api/grants/foundation-700")
        assert resp.status_code == 200
        assert resp.json()["id"] == "foundation-700"
        # The lookup key is the canonical external id regardless of db surrogate.
        assert mock_get_foundation.call_args[0][1] == 700
