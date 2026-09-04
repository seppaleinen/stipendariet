"""
BDD-style tests for Foundation Categorization and Admin Functionality.
All tests use mocked DB via conftest.py (sys.modules mock).
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _admin_headers():
    """Generate JWT Bearer headers for admin user."""
    token = create_access_token({
        "sub": settings.ADMIN_USERNAME,
        "email": settings.ADMIN_EMAIL,
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}


def test_foundation_categorization_job():
    """
    Scenario: Foundation categorization system properly categorizes foundations with enhanced Swedish categories
    """
    from app.foundation.categorization.categorize_foundations import FoundationCategorizer

    test_purpose = "Stöd till barns utbildning och fostran i skolan"
    categorizer = FoundationCategorizer()
    category = categorizer._find_closest_category(test_purpose)

    assert category in [
        "Utbildning och Forskning",
        "Socialt Stöd och Vård",
        "Kulturella Aktiviteter och Konst",
    ]


def test_admin_authentication_required(client):
    """
    Scenario: Non-admin user cannot access admin endpoints
    """
    response = client.post("/api/admin/trigger-foundation-sync")
    assert response.status_code == 401


def test_admin_access_with_valid_token(client):
    """
    Scenario: Admin user can access protected admin endpoints
    """
    response = client.post(
        "/api/admin/trigger-foundation-sync", headers=_admin_headers()
    )
    assert response.status_code != 401


def test_admin_access_rejected_without_admin_role(client):
    """
    Scenario: Non-admin JWT is rejected by admin endpoints
    """
    token = create_access_token({
        "sub": "user123",
        "email": "user@example.com",
        "role": "user",
    })
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/admin/trigger-foundation-sync", headers=headers)
    assert response.status_code == 403


def test_foundation_sync_endpoint(client):
    """
    Scenario: Foundation synchronization endpoint is callable with admin auth
    """
    # sync_foundations is lazily imported inside trigger_foundation_sync_endpoint()
    with patch("app.foundation.sync_service.sync_foundations") as mock_sync:
        mock_sync.return_value = None
        response = client.post(
            "/api/admin/trigger-foundation-sync", headers=_admin_headers()
        )
        assert response.status_code == 200


def test_category_reset_endpoint(client):
    """
    Scenario: Category reset functionality works correctly
    """
    # FoundationCategorizer is lazily imported inside reset_categories_endpoint()
    with patch(
        "app.foundation.categorization.categorize_foundations.FoundationCategorizer"
    ) as MockCategorizer:
        mock_instance = MockCategorizer.return_value
        mock_instance.reset_categories_in_db.return_value = 10

        response = client.post(
            "/api/admin/reset-categories", headers=_admin_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["foundations_reset"] == 10


def test_database_clear_endpoint(client):
    """
    Scenario: Database clearing endpoint is callable with admin auth
    """
    # crud and get_db are lazily imported inside clear_database_endpoint()
    with patch("app.crud.crud.delete_all_foundations") as mock_df, \
         patch("app.crud.crud.delete_all_applications") as mock_da, \
         patch("app.crud.crud.delete_all_profiles") as mock_dp:

        mock_df.return_value = 100
        mock_da.return_value = 25
        mock_dp.return_value = 1

        response = client.post("/api/admin/clear-database", headers=_admin_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["deleted_foundations"] == 100
        assert data["deleted_applications"] == 25
        assert data["deleted_profiles"] == 1


def test_get_foundation_categories(client):
    """
    Scenario: Foundation categories endpoint returns expected structure
    """
    response = client.get("/api/foundations/categories")
    assert response.status_code == 200
    categories = response.json()
    assert isinstance(categories, (list, dict))


def test_categorization_scheduled_daily():
    """
    Regression test for #28: categorization job must run daily, not weekly.
    """
    from app.foundation.categorization.categorization_job import (
        init_categorization_scheduler,
    )

    # Re-init scheduler with the current config
    init_categorization_scheduler()
    from app.foundation.categorization.categorization_job import (
        get_categorization_scheduler,
    )
    scheduler = get_categorization_scheduler()

    # Access the scheduler's internal APScheduler instance
    job = scheduler.scheduler.get_job("foundation_categorization_job")
    assert job is not None, "Categorization job should be registered"

    # Verify the trigger is daily (day_of_week field must be wildcard "*")
    # APScheduler CronTrigger fields order:
    # [year, month, day, week, day_of_week, hour, minute, second]
    trigger = job.trigger
    fields = trigger.fields
    # fields[4] is day_of_week
    assert str(fields[4]) == "*", (
        f"Expected daily schedule (day_of_week='*'), got day_of_week='{fields[4]}'"
    )
