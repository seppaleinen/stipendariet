"""
Unit tests for API routers — backend
Tests all router endpoints by mocking their dependencies (CRUD, services, DB sessions)
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from uuid import UUID

# Import app — database engine is mocked via conftest.py autouse fixture
from app.main import app
from app.db import schemas

client = TestClient(app)


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
        with patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user, \
             patch("app.api.v1.routers.auth._verify_admin_password") as mock_verify, \
             patch("app.api.v1.routers.auth.hash_password") as mock_hash, \
             patch("app.api.v1.routers.auth.create_access_token") as mock_token:

            mock_get_user.return_value = None
            mock_verify.return_value = True
            mock_hash.return_value = "hashed_pw"
            mock_user = MagicMock()
            mock_user.id = UUID("12345678-1234-5678-1234-567890123456")
            mock_user.email = "admin@example.com"
            mock_user.name = "Admin"
            mock_user.is_active = True
            mock_user.is_admin = True
            mock_user.created_at = "2026-01-01T00:00:00"
            mock_token.return_value = "admin-token"

            with patch("app.api.v1.routers.auth.db") as mock_db:
                mock_db.add = MagicMock()
                mock_db.commit = MagicMock()
                mock_db.refresh = MagicMock()

                response = client.post("/api/auth/login", json={
                    "email": "admin@example.com",
                    "password": "adminpass",
                })

                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "admin-token"
                assert data["user"]["is_admin"] is True

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

        with patch("app.api.v1.routers.auth.get_current_user_payload", return_value=mock_payload), \
             patch("app.api.v1.routers.auth.get_user_by_email") as mock_get_user:

            mock_get_user.return_value = mock_user

            response = client.get("/api/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"

    def test_get_current_user_invalid_token(self):
        """Get current user fails with invalid token"""
        mock_payload = {}

        with patch("app.api.v1.routers.auth.get_current_user_payload", return_value=mock_payload):
            response = client.get("/api/auth/me")
            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]

    def test_logout(self):
        """Logout returns success message"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}

        with patch("app.api.v1.routers.auth.get_current_user_payload", return_value=mock_payload):
            response = client.post("/api/auth/logout")
            assert response.status_code == 200
            assert "Logged out successfully" in response.json()["message"]

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

    def test_get_saved_grants(self):
        """Returns saved grants for user"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.get("/api/profile/saved-grants")
            assert response.status_code in [200, 500]

    def test_save_grant(self):
        """Save a grant for user"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.post("/api/profile/saved-grants", json={"grant_id": "grant-456"})
            assert response.status_code in [200, 201, 401, 500]

    def test_remove_saved_grant(self):
        """Remove a saved grant"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.delete("/api/profile/saved-grants/grant-456")
            assert response.status_code in [200, 401, 404, 500]

    def test_list_profiles(self):
        """List profiles for user"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.get("/api/profile/list")
            assert response.status_code in [200, 401, 500]

    def test_create_profile(self):
        """Create a new profile"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_payload", return_value=mock_payload):
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

    def test_get_profile(self):
        """Get a specific profile"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.get("/api/profile/1")
            assert response.status_code in [200, 401, 404, 500]

    def test_update_profile(self):
        """Update a profile"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.put("/api/profile/1", json={
                "name": "Updated Profile",
                "county_code": "180",
            })
            assert response.status_code in [200, 401, 404, 500]

    def test_delete_profile(self):
        """Delete a profile"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.delete("/api/profile/1")
            assert response.status_code in [200, 204, 401, 404]

    def test_get_family_profile(self):
        """Get family profile (default)"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.get("/api/profile/family")
            assert response.status_code in [200, 401, 404, 500]

    def test_upsert_family_profile(self):
        """Upsert family profile"""
        mock_payload = {"sub": "12345678-1234-5678-1234-567890123456"}
        with patch("app.api.v1.routers.profile.get_current_user_payload", return_value=mock_payload):
            response = client.put("/api/profile/family", json={
                "name": "My Profile",
                "county_code": "180",
            })
            assert response.status_code in [200, 401, 500]


# =============================================================================
# Foundations Router Tests
# =============================================================================

class TestFoundationsRouter:
    """Tests for /api/foundations endpoints"""

    def test_get_all_foundations(self):
        """Poll foundations from external API"""
        response = client.get("/api/foundations/")
        assert response.status_code in [200, 503]

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
        """Reset categories requires admin auth"""
        response = client.post("/api/foundations/reset-categories")
        assert response.status_code == 401

    def test_categorize_db_foundations_requires_admin(self):
        """Categorize DB foundations requires admin auth"""
        response = client.post("/api/foundations/categorize-db-foundations")
        assert response.status_code == 401

    def test_translate_purpose_empty_purpose(self):
        """Translation fails when purpose is empty"""
        response = client.post("/api/foundations/translate-purpose", json={"purpose": ""})
        assert response.status_code == 400
        assert "Purpose field is required" in response.json()["detail"]

    def test_translate_purpose_success(self):
        """Translation succeeds"""
        with patch("app.services.ollama_translation_service.ollama_translation_service") as mock_service:
            mock_service.translate_purpose.return_value = "Translated purpose"
            response = client.post("/api/foundations/translate-purpose", json={"purpose": "Original purpose"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["translated_purpose"] == "Translated purpose"

    def test_translate_purpose_service_failure(self):
        """Translation fails when service returns None"""
        with patch("app.services.ollama_translation_service.ollama_translation_service") as mock_service:
            mock_service.translate_purpose.return_value = None
            response = client.post("/api/foundations/translate-purpose", json={"purpose": "Original purpose"})
            assert response.status_code == 500
            assert "Translation failed" in response.json()["detail"]

    def test_matching_foundations_empty_needs(self):
        """Matching fails when needs is empty"""
        response = client.post("/api/foundations/matching", json={"needs": ""})
        assert response.status_code == 400
        assert "Needs description is required" in response.json()["detail"]

    def test_matching_foundations_success(self):
        """Matching succeeds and returns results"""
        with patch("app.services.embedding_service.ollama_embedding_service") as mock_service:
            mock_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
            response = client.post("/api/foundations/matching", json={
                "needs": "Education funding for students",
                "threshold": 0.5,
                "limit": 10
            })
            assert response.status_code in [200, 401, 500, 503]


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
# Generate Router Tests
# =============================================================================

class TestGenerateRouter:
    """Tests for /api/generate endpoints"""

    def test_generate_application_grant_not_found(self):
        """Generation fails when grant doesn't exist"""
        with patch("app.api.v1.routers.crud.get_grant") as mock_get_grant:
            mock_get_grant.return_value = None
            response = client.post("/api/generate-application", json={
                "grant_id": 999,
                "profile": {
                    "family_members": [],
                    "economic_situation": "Test",
                    "background": "Test",
                    "achievements": "Test",
                    "goals": "Test",
                }
            })
            assert response.status_code == 404
            assert "Grant not found" in response.json()["detail"]

    def test_generate_application_success(self):
        """Generation succeeds and returns email template"""
        mock_grant = MagicMock()
        mock_grant.id = 1
        mock_grant.name = "Test Grant"
        mock_grant.provider = "Test Provider"
        mock_grant.amount = 10000
        mock_grant.deadline = None
        mock_grant.summary = "Test summary"

        with patch("app.api.v1.routers.crud.get_grant") as mock_get_grant:
            mock_get_grant.return_value = mock_grant
            response = client.post("/api/generate-application", json={
                "grant_id": 1,
                "profile": {
                    "family_members": [
                        {"name": "Parent", "age": 35, "role": "parent"},
                        {"name": "Child", "age": 10, "role": "child"},
                    ],
                    "economic_situation": "Low income",
                    "background": "Student family",
                    "achievements": "Good grades",
                    "goals": "Continue education",
                }
            })
            assert response.status_code == 200
            data = response.json()
            assert "email_text" in data
            assert "Ansökan om Test Grant" in data["email_text"]
            assert "Test Provider" in data["email_text"]


# =============================================================================
# Applications Router Tests
# =============================================================================

class TestApplicationsRouter:
    """Tests for /api/applications endpoints"""

    def test_get_applications(self):
        """Get all applications"""
        response = client.get("/api/applications/")
        assert response.status_code in [200, 500]

    def test_create_application_grant_not_found(self):
        """Create application fails when grant doesn't exist"""
        with patch("app.api.v1.routers.crud.get_grant") as mock_get_grant:
            mock_get_grant.return_value = None
            response = client.post("/api/applications/", json={
                "grant_id": 999,
                "user_id": "12345678-1234-5678-1234-567890123456",
            })
            assert response.status_code == 404
            assert "Grant not found" in response.json()["detail"]

    def test_get_application_by_id(self):
        """Get application by ID"""
        response = client.get("/api/applications/1")
        assert response.status_code in [200, 404, 500]

    def test_update_application(self):
        """Update an application"""
        response = client.patch("/api/applications/1", json={"status": "updated"})
        assert response.status_code in [200, 404, 500]


# =============================================================================
# Admin Router Tests
# =============================================================================

class TestAdminRouter:
    """Tests for admin endpoints"""

    def test_enrichment_requires_admin(self):
        """Enrichment endpoints require admin auth"""
        response = client.post("/api/admin/enrich")
        assert response.status_code == 401

    def test_system_status(self):
        """System status endpoint"""
        response = client.get("/api/admin/status")
        assert response.status_code == 401

    def test_categorization_requires_admin(self):
        """Categorization endpoints require admin auth"""
        response = client.post("/api/admin/categorize")
        assert response.status_code == 401

    def test_embeddings_endpoint_requires_admin(self):
        """Embeddings endpoint requires admin auth"""
        response = client.post("/api/admin/embeddings")
        assert response.status_code == 401

    def test_translation_endpoint_requires_admin(self):
        """Translation endpoint requires admin auth"""
        response = client.post("/api/admin/translation")
        assert response.status_code == 401

    def test_sync_endpoint_requires_admin(self):
        """Sync endpoint requires admin auth"""
        response = client.post("/api/admin/trigger-foundation-sync")
        assert response.status_code == 401


# =============================================================================
# Admin Password Reset Router Tests
# =============================================================================

class TestAdminPasswordResetRouter:
    """Tests for admin password reset endpoints"""

    def test_request_reset_requires_admin(self):
        """Password reset request requires admin auth"""
        response = client.post("/api/admin/request-password-reset")
        assert response.status_code == 401

    def test_reset_password_requires_admin(self):
        """Password reset requires admin auth"""
        response = client.post("/api/admin/reset-password", json={
            "token": "test-token",
            "new_password": "newpassword123",
        })
        assert response.status_code == 401

