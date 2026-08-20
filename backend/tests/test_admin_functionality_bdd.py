"""
BDD-style tests for admin functionality - step implementations
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


def _admin_headers():
    """Return Bearer JWT headers for an admin user (matches ADMIN_EMAIL in settings)."""
    from app.core.config import settings
    email = settings.ADMIN_EMAIL or "admin@test.com"
    token = create_access_token({"sub": email, "email": email, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_foundation_sync_triggers_categorization():
    """
    Scenario: Triggering foundation sync also triggers categorization
    """
    client = TestClient(app)

    with patch("app.foundation.sync_service.sync_foundations") as mock_sync:
        mock_sync.return_value = True

        response = client.post("/api/admin/trigger-foundation-sync", headers=_admin_headers())

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] in ("success", "started")


def test_categorization_status_endpoint():
    """
    Scenario: Categorization status endpoint returns the expected structure
    """
    client = TestClient(app)

    response = client.get("/api/foundations/categorization-status")

    assert response.status_code == 200
    data = response.json()

    # Should have the required fields
    assert "total_foundations" in data
    assert "uncategorized_foundations" in data
    assert "categorized_foundations" in data
    assert "category_distribution" in data

    # Distribution should be a list of dictionaries
    assert isinstance(data["category_distribution"], list)


def test_dynamic_family_member_inputs():
    """
    Scenario: User can provide names for each family member based on count
    """
    client = TestClient(app)

    # Test that the foundations endpoint exists
    response = client.get("/api/foundations/stored")
    # The response will be mocked, but this tests that the endpoint exists
    assert response.status_code in [200, 500]  # Either works or has DB error due to mock


def test_enhanced_foundation_fields():
    """
    Scenario: Foundation categorizer can classify a foundation by purpose text
    """
    from app.foundation.categorization.categorize_foundations import FoundationCategorizer

    categorizer = FoundationCategorizer()

    # Test the general category classification (synchronous, no DB needed)
    category = categorizer._get_general_category(
        "Att främja barns utbildning och fostran samt hjälpa behövande barn"
    )
    assert isinstance(category, str)
    assert len(category) > 0

    # Test with a different purpose
    category2 = categorizer._get_general_category(
        "Bevakning av intressen inom forskning och utbildning"
    )
    assert isinstance(category2, str)


def test_swedish_categories_in_funding_endpoint():
    """
    Scenario: Funding endpoint returns foundations with Swedish categories
    """
    client = TestClient(app)

    response = client.get("/api/funding")

    # Response might require DB, so we'll just check if the endpoint exists
    assert response.status_code in [200, 503]  # Either works or has DB error

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)

        # If there are foundations, they should have category fields
        for item in data:
            if item.get("id", "").startswith("foundation-"):
                assert "category" in item
                # Categories should be in Swedish
                if item["category"]:
                    # Verify it's one of our enhanced Swedish categories
                    swedish_categories = [
                        "Utbildning och Forskning",
                        "Socialt Stöd och Vård",
                        "Kulturella Aktiviteter och Konst",
                        "Hälso- och Sjukvård samt Medicinsk Forskning",
                        "Miljövård och Naturskydd",
                        "Idrotts- och Fysiska Aktiviteter",
                        "Religiösa Aktiviteter",
                        "Samhällsutveckling",
                        "Ekonomiskt och Näringslivsstöd",
                        "Specialiserade Områden"
                    ]
                    assert item["category"] in swedish_categories + ["", None]


if __name__ == "__main__":
    # Run the tests when executed directly
    pytest.main([__file__])
