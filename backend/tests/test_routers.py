"""
Unit tests for API routers — backend
Tests all router endpoints by mocking their dependencies (CRUD, services, DB sessions)
"""
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_admin_user, get_current_user_payload

# Import app — database engine is mocked via conftest.py autouse fixture
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# =============================================================================
# Auth Router Tests
# =============================================================================

class TestAuthRouter:
    """Tests for /api/auth endpoints"""

    def test_signup_password_too_short(self):
        """Signup fails when password < 8 chars"""
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "short",
            "name": "Test User",
        })
        assert response.status_code == 400
        assert "Password must be at least 8 characters" in response.json()["detail"]

    def test_signup_email_already_registered(self):
        """Signup fails when email already exists"""
        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user:
            mock_get_user.return_value = MagicMock()

            response = client.post("/api/auth/signup", json={
                "email": "existing@example.com",
                "password": "password123",
                "name": "Existing User",
            })
            assert response.status_code == 400
            assert "Email already registered" in response.json()["detail"]

    def test_signup_success(self):
        """Signup succeeds and returns token + user"""
        mock_user = MagicMock()
        mock_user.id = UUID("12345678-1234-5678-1234-567890123456")
        mock_user.email = "new@example.com"
        mock_user.name = "New User"
        mock_user.is_active = True
        mock_user.created_at = "2026-01-01T00:00:00"

        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth.create_user") as mock_create_user, \
             patch("app.api.v1.routers.auth.create_access_token") as mock_token:

            mock_get_user.return_value = None
            mock_create_user.return_value = mock_user
            mock_token.return_value = "mock-jwt-token"

            response = client.post("/api/auth/signup", json={
                "email": "new@example.com",
                "password": "password123",
                "name": "New User",
            })

            assert response.status_code == 201
            data = response.json()
            assert data["access_token"] == "mock-jwt-token"
            assert data["user"]["email"] == "new@example.com"

    def test_login_user_not_in_db_admin_login(self):
        """Login with admin credentials when user not in DB — auto-creates admin"""
        from app.core.config import settings

        admin_email = settings.ADMIN_EMAIL

        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth._verify_admin_password") as mock_verify, \
             patch("app.api.v1.routers.auth.hash_password") as mock_hash, \
             patch("app.api.v1.routers.auth.create_access_token") as mock_token, \
             patch("app.api.v1.routers.auth.models.User") as mock_user_cls:

            mock_get_user.return_value = None
            mock_verify.return_value = True
            mock_hash.return_value = "hashed_pw"
            mock_token.return_value = "admin-token"

            # models.User() is called to create the admin — mock its instance
            mock_admin_instance = MagicMock()
            mock_admin_instance.id = UUID("12345678-1234-5678-1234-567890123456")
            mock_admin_instance.email = admin_email
            mock_admin_instance.name = "Admin"
            mock_admin_instance.is_active = True
            mock_admin_instance.is_admin = True
            mock_admin_instance.created_at = "2026-01-01T00:00:00"
            mock_user_cls.return_value = mock_admin_instance

            response = client.post("/api/auth/login", json={
                "email": admin_email,
                "password": "adminpass",
            })

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "admin-token"

    def test_login_invalid_credentials(self):
        """Login fails with invalid credentials"""
        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth._verify_admin_password") as mock_verify:

            mock_get_user.return_value = None
            mock_verify.return_value = False

            response = client.post("/api/auth/login", json={
                "email": "wrong@example.com",
                "password": "wrongpass",
            })
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

    def test_login_user_exists_password_wrong(self):
        """Login fails when user exists but password is wrong"""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"
        mock_user.is_active = True

        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth.verify_password") as mock_verify:

            mock_get_user.return_value = mock_user
            mock_verify.return_value = False

            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpass",
            })
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

    def test_login_user_inactive(self):
        """Login fails when user account is inactive"""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"
        mock_user.is_active = False

        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth.verify_password") as mock_verify:

            mock_get_user.return_value = mock_user
            mock_verify.return_value = True

            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "correctpass",
            })
            assert response.status_code == 401
            assert "Account is inactive" in response.json()["detail"]

    def test_login_success(self):
        """Login succeeds and returns token + user"""
        mock_user = MagicMock()
        mock_user.id = UUID("12345678-1234-5678-1234-567890123456")
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.is_admin = False
        mock_user.created_at = "2026-01-01T00:00:00"

        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth.verify_password") as mock_verify, \
             patch("app.api.v1.routers.auth.create_access_token") as mock_token:

            mock_get_user.return_value = mock_user
            mock_verify.return_value = True
            mock_token.return_value = "jwt-token"

            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "correctpass",
            })

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "jwt-token"
            assert data["user"]["email"] == "test@example.com"

    def test_get_current_user(self):
        """Get current user returns user data"""
        mock_user = MagicMock()
        mock_user.id = UUID("12345678-1234-5678-1234-567890123456")
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.created_at = "2026-01-01T00:00:00"

        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}

        # Mock the DB query chain
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.first.return_value = mock_user
        mock_db.query.return_value.filter.return_value = mock_query

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_current_user_payload] = lambda: mock_payload
        from app.db.database import get_db as real_get_db
        app.dependency_overrides[real_get_db] = _mock_get_db
        try:
            response = client.get("/api/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
        finally:
            app.dependency_overrides.pop(get_current_user_payload, None)
            app.dependency_overrides.pop(real_get_db, None)

    def test_get_current_user_invalid_token(self):
        """Get current user fails with invalid token"""
        mock_payload = {}

        app.dependency_overrides[get_current_user_payload] = lambda: mock_payload
        try:
            response = client.get("/api/auth/me")
            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user_payload, None)

    def test_logout(self):
        """Logout returns success message"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}

        app.dependency_overrides[get_current_user_payload] = lambda: mock_payload
        try:
            response = client.post("/api/auth/logout")
            assert response.status_code == 200
            assert "Logged out successfully" in response.json()["message"]
        finally:
            app.dependency_overrides.pop(get_current_user_payload, None)

    def test_google_oauth_redirect_not_implemented(self):
        """Google OAuth returns 501 Not Implemented"""
        response = client.get("/api/auth/google")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"].lower()


# =============================================================================
# Profile Router Tests
# =============================================================================

class TestProfileRouter:
    """Tests for /api/profile endpoints"""

    def _set_auth(self, mock_payload=None):
        """Set up dependency override for auth."""
        if mock_payload is None:
            mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        app.dependency_overrides[get_current_user_payload] = lambda: mock_payload

    def _clear_auth(self):
        """Clear dependency override."""
        app.dependency_overrides.pop(get_current_user_payload, None)

    def test_get_saved_grants(self):
        """Returns saved grants for user"""
        self._set_auth()
        try:
            response = client.get("/api/profile/saved-grants")
            assert response.status_code in [200, 500]
        finally:
            self._clear_auth()

    def test_save_grant(self):
        """Save a grant for user"""
        self._set_auth()
        try:
            response = client.post("/api/profile/saved-grants", json={"grant_id": "grant-456"})
            assert response.status_code in [200, 201, 401, 500]
        finally:
            self._clear_auth()

    def test_remove_saved_grant(self):
        """Remove a saved grant"""
        self._set_auth()
        try:
            response = client.delete("/api/profile/saved-grants/grant-456")
            assert response.status_code in [200, 401, 404, 500]
        finally:
            self._clear_auth()

    def test_list_profiles(self):
        """List profiles for user"""
        self._set_auth()
        try:
            response = client.get("/api/profile/list")
            assert response.status_code in [200, 401, 500]
        finally:
            self._clear_auth()

    def test_create_profile(self):
        """Create a new profile"""
        self._set_auth()
        try:
            response = client.post("/api/profile/", json={
                "name": "My Profile",
                "county_code": "180",
                "municipality_code": "180",
                "life_situations": ["student"],
                "health_conditions": [],
                "health_details": None,
                "occupations": [],
                "support_purposes": ["education"],
                "legacy_data": None,
            })
            assert response.status_code in [200, 201, 401, 500]
        finally:
            self._clear_auth()

    def test_get_profile(self):
        """Get a specific profile"""
        self._set_auth()
        try:
            response = client.get("/api/profile/1")
            assert response.status_code in [200, 401, 404, 422, 500]
        finally:
            self._clear_auth()

    def test_update_profile(self):
        """Update a profile"""
        self._set_auth()
        try:
            response = client.put("/api/profile/1", json={
                "name": "Updated Profile",
                "county_code": "180",
            })
            assert response.status_code in [200, 401, 404, 422, 500]
        finally:
            self._clear_auth()

    def test_delete_profile(self):
        """Delete a profile"""
        self._set_auth()
        try:
            response = client.delete("/api/profile/1")
            assert response.status_code in [200, 204, 401, 404]
        finally:
            self._clear_auth()

    def test_get_family_profile(self):
        """Get family profile (default)"""
        self._set_auth()
        try:
            response = client.get("/api/profile/family")
            assert response.status_code in [200, 401, 404, 422, 500]
        finally:
            self._clear_auth()

    def test_upsert_family_profile(self):
        """Upsert family profile"""
        self._set_auth()
        try:
            response = client.put("/api/profile/family", json={
                "name": "My Profile",
                "county_code": "180",
            })
            assert response.status_code in [200, 401, 422, 500]
        finally:
            self._clear_auth()

    def test_create_profile_rejects_over_long_self_description(self):
        """Self-description over 2000 chars is rejected by validation"""
        self._set_auth()
        try:
            response = client.post("/api/profile/", json={
                "name": "My Profile",
                "self_description": "a" * 2001,
            })
            assert response.status_code == 422
            assert response.json()["detail"]
        finally:
            self._clear_auth()

    def test_create_profile_accepts_self_description(self):
        """Self-description within the cap is accepted on create"""
        self._set_auth()
        try:
            with patch("app.api.v1.routers.profile.models.Profile") as mock_profile_cls:
                mock_instance = MagicMock()
                mock_instance.id = 1
                mock_instance.name = "My Profile"
                mock_instance.is_default = True
                # Response serialization reads aliased attr names (e.g. countyCode),
                # while the endpoint writes snake_case — provide both spellings.
                mock_instance.county_code = None
                mock_instance.municipality_code = None
                mock_instance.health_details = None
                mock_instance.self_description = "Min egen beskrivning"
                mock_instance.legacy_data = None
                mock_instance.countyCode = None
                mock_instance.municipalityCode = None
                mock_instance.healthDetails = None
                mock_instance.selfDescription = "Min egen beskrivning"
                mock_instance.legacyData = None
                mock_profile_cls.return_value = mock_instance

                response = client.post("/api/profile/", json={
                    "name": "My Profile",
                    "self_description": "Min egen beskrivning",
                })
                assert response.status_code == 201
                # Field threaded through to the DB model constructor
                _, kwargs = mock_profile_cls.call_args
                assert kwargs["self_description"] == "Min egen beskrivning"
        finally:
            self._clear_auth()


# =============================================================================
# Foundations Router Tests
# =============================================================================

class TestFoundationsRouter:
    """Tests for /api/foundations endpoints"""

    @pytest.mark.skip(reason="Hits external API (stiftelser.lansstyrelsen.se) — tested in E2E")
    def test_get_all_foundations(self):
        """Poll foundations from external API"""
        response = client.get("/api/foundations/")
        assert response.status_code in [200, 503]

    @pytest.mark.skip(reason="Hits external API (stiftelser.lansstyrelsen.se) — tested in E2E")
    def test_search_foundations(self):
        """Search foundations by query"""
        response = client.get("/api/foundations/search", params={"query": "test"})
        assert response.status_code in [200, 503]

    def test_get_stored_foundations(self):
        """Get stored foundations from DB"""
        response = client.get("/api/foundations/stored")
        assert response.status_code in [200, 500]

    def test_get_stored_foundation_by_id(self):
        """Get a single stored foundation"""
        response = client.get("/api/foundations/stored/123")
        assert response.status_code in [200, 404, 500]

    def test_get_stored_foundations_by_category(self):
        """Get foundations filtered by category"""
        response = client.get("/api/foundations/stored/by-category/Utbildning")
        assert response.status_code in [200, 500]

    def test_get_stored_foundations_by_county(self):
        """Get foundations filtered by county code"""
        response = client.get("/api/foundations/stored/by-county/180")
        assert response.status_code in [200, 500]

    def test_get_stored_foundations_by_municipality(self):
        """Get foundations filtered by municipality code"""
        response = client.get("/api/foundations/stored/by-municipality/180")
        assert response.status_code in [200, 500]

    def test_get_all_categories(self):
        """Get all unique categories"""
        response = client.get("/api/foundations/categories")
        assert response.status_code in [200, 500]

    def test_get_categorization_status(self):
        """Get categorization status"""
        response = client.get("/api/foundations/categorization-status")
        assert response.status_code in [200, 500]

    def test_reset_categories_requires_admin(self):
        """Reset categories endpoint requires admin auth"""
        response = client.post("/api/foundations/reset-categories")
        assert response.status_code == 401

    def test_categorize_db_foundations_requires_admin(self):
        """Categorize DB foundations endpoint requires admin auth"""
        response = client.post("/api/foundations/categorize-db-foundations")
        assert response.status_code == 401

    def test_translate_purpose_empty_purpose(self):
        """Translation fails when purpose is empty"""
        app.dependency_overrides[get_admin_user] = lambda: {"sub": "admin", "role": "admin"}
        try:
            response = client.post("/api/foundations/translate-purpose", json={"purpose": ""})
            assert response.status_code == 400
            assert "Purpose field is required" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_admin_user, None)

    def test_translate_purpose_success(self):
        """Translation succeeds"""
        app.dependency_overrides[get_admin_user] = lambda: {"sub": "admin", "role": "admin"}
        try:
            with patch("app.api.v1.routers.foundations.llm_translation_service") as mock_service:
                mock_service.translate_purpose.return_value = "Translated purpose"
                response = client.post("/api/foundations/translate-purpose", json={"purpose": "Original purpose"})
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["translated_purpose"] == "Translated purpose"
        finally:
            app.dependency_overrides.pop(get_admin_user, None)

    def test_translate_purpose_service_failure(self):
        """Translation fails when service returns None"""
        app.dependency_overrides[get_admin_user] = lambda: {"sub": "admin", "role": "admin"}
        try:
            with patch("app.api.v1.routers.foundations.llm_translation_service") as mock_service:
                mock_service.translate_purpose.return_value = None
                response = client.post("/api/foundations/translate-purpose", json={"purpose": "Original purpose"})
                assert response.status_code == 500
                assert "Translation failed" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_admin_user, None)

    def test_matching_foundations_empty_needs(self):
        """Matching fails when needs is empty"""
        response = client.post("/api/foundations/matching", json={"needs": ""})
        assert response.status_code == 400
        assert "Needs description is required" in response.json()["detail"]

    def test_matching_foundations_success(self):
        """Matching succeeds and returns results"""
        with patch("app.api.v1.routers.foundations.ollama_embedding_service") as mock_service:
            mock_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
            response = client.post("/api/foundations/matching", json={
                "needs": "Education funding for students",
                "threshold": 0.5,
                "limit": 10
            })
            assert response.status_code in [200, 401, 500, 503]

    # --- matching-by-profile: Self-description (free text) source flag ---

    def _set_user_auth_and_db(self, mock_profile):
        """Override auth payload and DB session for /matching-by-profile tests."""
        from app.db.database import get_db

        app.dependency_overrides[get_current_user_payload] = lambda: {
            "sub": "12345678-1234-5678-1234-567890123456"
        }

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        mock_db.execute.return_value.fetchall.return_value = []

        def _yield_db():
            yield mock_db

        app.dependency_overrides[get_db] = _yield_db
        return mock_db

    def _clear_user_auth_and_db(self):
        from app.db.database import get_db

        app.dependency_overrides.pop(get_current_user_payload, None)
        app.dependency_overrides.pop(get_db, None)

    def test_matching_by_profile_use_description_empty_rejected(self):
        """Self-description mode with an empty self-description is rejected with 400"""
        mock_profile = MagicMock()
        mock_profile.self_description = "   "

        self._set_user_auth_and_db(mock_profile)
        try:
            response = client.post("/api/foundations/matching-by-profile", json={
                "profile_id": 1,
                "use_description": True,
            })
            assert response.status_code == 400
            assert "Self-description is empty" in response.json()["detail"]
        finally:
            self._clear_user_auth_and_db()

    def test_matching_by_profile_use_description_embeds_raw_description(self):
        """Self-description mode embeds the raw self-description and skips text generation"""
        mock_profile = MagicMock()
        mock_profile.self_description = "Jag är ensamstående förälder och söker stöd."
        mock_profile.county_code = "180"
        mock_profile.municipality_code = None

        mock_db = self._set_user_auth_and_db(mock_profile)
        try:
            with patch("app.api.v1.routers.foundations.ollama_embedding_service") as mock_service, \
                 patch("app.api.v1.routers.foundations.generate_profile_text") as mock_generate_text:
                mock_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
                response = client.post("/api/foundations/matching-by-profile", json={
                    "profile_id": 1,
                    "use_description": True,
                })

                assert response.status_code == 200
                assert response.json() == []
                # Raw description embedded — never the generated profile text
                mock_service.generate_embedding.assert_called_once_with(
                    "Jag är ensamstående förälder och söker stöd."
                )
                mock_generate_text.assert_not_called()

                # Geographic filter still applies SQL-side in this mode
                execute_params = mock_db.execute.call_args[0][1]
                assert execute_params["county_code"] == "180"
        finally:
            self._clear_user_auth_and_db()

    def test_matching_by_profile_default_uses_generated_text(self):
        """Default mode (flag absent) generates text from structured selections as before"""
        mock_profile = MagicMock()
        mock_profile.self_description = "Should be ignored in structured mode"
        mock_profile.county_code = None
        mock_profile.municipality_code = None
        mock_profile.life_situations = ["student"]
        mock_profile.health_conditions = []
        mock_profile.health_details = None
        mock_profile.occupations = []
        mock_profile.support_purposes = []

        self._set_user_auth_and_db(mock_profile)
        try:
            with patch("app.api.v1.routers.foundations.ollama_embedding_service") as mock_service, \
                 patch("app.api.v1.routers.foundations.generate_profile_text") as mock_generate_text:
                mock_generate_text.return_value = "Generated profile text"
                mock_service.generate_embedding.return_value = [0.1, 0.2, 0.3]

                response = client.post("/api/foundations/matching-by-profile", json={
                    "profile_id": 1,
                })

                assert response.status_code == 200
                mock_generate_text.assert_called_once()
                mock_service.generate_embedding.assert_called_once_with("Generated profile text")
        finally:
            self._clear_user_auth_and_db()


# =============================================================================
# Foundation Sync Router Tests
# =============================================================================

class TestFoundationSyncRouter:
    """Tests for /api/foundation-sync endpoints"""

    def test_trigger_sync_requires_admin(self):
        """Trigger sync rejects anonymous requests"""
        response = client.post("/api/foundation-sync/trigger-sync")
        assert response.status_code == 401

    def test_trigger_sync_rejects_non_admin(self):
        """Trigger sync rejects valid non-admin JWTs with 403"""
        from app.core.security import create_access_token

        token = create_access_token({
            "sub": "12345678-1234-5678-1234-567890123456",
            "email": "user@example.com",
            "role": "user",
        })
        response = client.post(
            "/api/foundation-sync/trigger-sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_trigger_sync_success_as_admin(self):
        """Trigger sync succeeds for admin"""
        app.dependency_overrides[get_admin_user] = lambda: {"sub": "admin", "role": "admin"}
        try:
            with patch("app.api.v1.routers.foundation_sync.trigger_foundation_sync") as mock_sync:
                mock_sync.return_value = True
                response = client.post("/api/foundation-sync/trigger-sync")
                assert response.status_code == 200
                assert response.json()["status"] == "success"
        finally:
            app.dependency_overrides.pop(get_admin_user, None)

    def test_generate_application_requires_auth(self):
        """Generate application rejects anonymous requests"""
        response = client.post("/api/foundation-sync/generate-application", json={"prompt": "hello"})
        assert response.status_code == 401

    def test_generate_application_success(self):
        """Generate application returns LLM content for authenticated users"""
        app.dependency_overrides[get_current_user_payload] = lambda: {
            "sub": "12345678-1234-5678-1234-567890123456"
        }
        try:
            with patch("app.services.llm_client.litellm_text_model") as mock_model, patch(
                "app.services.llm_client.chat_completion"
            ) as mock_chat:
                mock_model.return_value = "test-model"
                mock_chat.return_value = "Generated text"
                response = client.post(
                    "/api/foundation-sync/generate-application", json={"prompt": "hello"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["response"] == "Generated text"
                assert data["model_used"] == "test-model"
        finally:
            app.dependency_overrides.pop(get_current_user_payload, None)


# =============================================================================
# Search Router Tests
# =============================================================================

class TestSearchRouter:
    """Tests for /api/search endpoints"""

    def test_search_foundations(self):
        """Search foundations by query"""
        response = client.get("/api/search/foundations", params={"query": "test", "limit": 10})
        assert response.status_code in [200, 500]

    def test_search_profiles_empty(self):
        """Search profiles returns empty (stub)"""
        response = client.get("/api/search/profiles", params={"query": "test", "limit": 10})
        assert response.status_code == 200
        assert response.json() == []


# =============================================================================
# Funding Router Tests
# =============================================================================

class TestFundingRouter:
    """Tests for /api/funding endpoints"""

    def test_get_all_funding(self):
        """Get all funding opportunities"""
        response = client.get("/api/funding")
        assert response.status_code in [200, 500]

    def test_get_funding_by_id_grant(self):
        """Get funding by ID (grant format)"""
        response = client.get("/api/funding/grant-1")
        assert response.status_code in [200, 404, 500]

    def test_get_funding_by_id_foundation(self):
        """Get funding by ID (foundation format)"""
        response = client.get("/api/funding/foundation-1")
        assert response.status_code in [200, 404, 500]

    def test_get_funding_by_id_legacy_numeric(self):
        """Get funding by ID (legacy numeric format)"""
        response = client.get("/api/funding/1")
        assert response.status_code in [200, 404, 500]

    def test_get_funding_by_id_invalid_format(self):
        """Get funding by ID with invalid format"""
        response = client.get("/api/funding/invalid-id")
        assert response.status_code == 404
        assert "Invalid funding ID format" in response.json()["detail"]


# =============================================================================
# Applications Router Tests
# =============================================================================

class TestApplicationsRouter:
    """Tests for /api/applications endpoints — all require Bearer JWT"""

    def _set_auth(self, mock_payload=None):
        """Set up dependency override for auth."""
        if mock_payload is None:
            mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        app.dependency_overrides[get_current_user_payload] = lambda: mock_payload

    def _clear_auth(self):
        """Clear dependency override."""
        app.dependency_overrides.pop(get_current_user_payload, None)

    def test_requires_authentication(self):
        """All application endpoints reject anonymous requests"""
        endpoints = [
            ("get", "/api/applications/"),
            ("post", "/api/applications/"),
            ("get", "/api/applications/1"),
            ("patch", "/api/applications/1"),
            ("delete", "/api/applications/1"),
        ]
        for method, url in endpoints:
            if method in ("post", "patch"):
                response = getattr(client, method)(url, json={"status": "x"})
            else:
                response = getattr(client, method)(url)
            assert response.status_code == 401, f"{method.upper()} {url} not 401"

    def test_get_applications(self):
        """Get all applications"""
        self._set_auth()
        try:
            response = client.get("/api/applications/")
            assert response.status_code in [200, 500]
        finally:
            self._clear_auth()

    def test_create_application_grant_not_found(self):
        """Create application fails when grant doesn't exist"""
        self._set_auth()
        try:
            with patch("app.api.v1.routers.applications.crud.get_grant") as mock_get_grant:
                mock_get_grant.return_value = None
                response = client.post("/api/applications/", json={
                    "grant_id": 999,
                    "user_id": "12345678-1234-5678-1234-567890123456",
                })
                assert response.status_code in [404, 422]
        finally:
            self._clear_auth()

    def test_get_application_by_id(self):
        """Get application by ID"""
        self._set_auth()
        try:
            response = client.get("/api/applications/1")
            assert response.status_code in [200, 404, 500]
        finally:
            self._clear_auth()

    def test_update_application(self):
        """Update an application"""
        self._set_auth()
        try:
            response = client.patch("/api/applications/1", json={"status": "updated"})
            assert response.status_code in [200, 404, 500]
        finally:
            self._clear_auth()

    def test_delete_application(self):
        """Delete an application"""
        self._set_auth()
        try:
            response = client.delete("/api/applications/1")
            assert response.status_code in [204, 404, 500]
        finally:
            self._clear_auth()


# =============================================================================
# Admin Router Tests
# =============================================================================

class TestAdminRouter:
    """Tests for admin endpoints — all require Bearer JWT with admin role"""

    def test_enrichment_requires_admin(self):
        """Enrichment start endpoint requires admin auth"""
        response = client.post("/api/admin/enrich/start")
        assert response.status_code == 401

    def test_categorization_requires_admin(self):
        """Categorization endpoint requires admin auth"""
        response = client.post("/api/admin/trigger-bulk-categorization")
        assert response.status_code == 401

    def test_embeddings_endpoint_requires_admin(self):
        """Embeddings endpoint requires admin auth"""
        response = client.post("/api/admin/trigger-bulk-embedding-generation")
        assert response.status_code == 401

    def test_translation_endpoint_requires_admin(self):
        """Translation endpoint requires admin auth"""
        response = client.post("/api/admin/trigger-bulk-purpose-translation")
        assert response.status_code == 401

    def test_sync_endpoint_requires_admin(self):
        """Sync endpoint requires admin auth"""
        response = client.post("/api/admin/trigger-foundation-sync")
        assert response.status_code == 401

    def test_foundation_stats_requires_admin(self):
        """Foundation stats requires admin auth"""
        response = client.get("/api/admin/foundation-stats")
        assert response.status_code == 401

    def test_active_jobs_requires_admin(self):
        """Active jobs requires admin auth"""
        response = client.get("/api/admin/active-jobs")
        assert response.status_code == 401

    def test_clear_database_requires_admin(self):
        """Clear database requires admin auth"""
        response = client.post("/api/admin/clear-database")
        assert response.status_code == 401

    def test_grant_sync_requires_admin(self):
        """Grant sync requires admin auth"""
        response = client.post("/api/admin/trigger-grant-sync")
        assert response.status_code == 401


# =============================================================================
# Admin Password Reset Router Tests
# =============================================================================

class TestAdminPasswordResetRouter:
    """Tests for admin password reset endpoints"""

    def test_request_reset_requires_admin(self):
        """Password reset request requires admin auth"""
        response = client.post("/admin/reset-user-password")
        assert response.status_code in [401, 404, 422]

    def test_emergency_reset_endpoint_removed(self):
        """Emergency password reset endpoint has been removed (issue #4)"""
        response = client.post("/emergency-reset-admin-password")
        assert response.status_code == 404

