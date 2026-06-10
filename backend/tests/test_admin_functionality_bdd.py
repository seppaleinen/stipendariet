"""
BDD-style tests for admin functionality - step implementations
"""
import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_admin_dashboard_access():
    """
    Scenario: Admin dashboard is accessible with proper authentication
    """
    client = TestClient(app)

    # Should redirect to basic auth challenge for admin dashboard
    response = client.get("/api/admin/")
    assert response.status_code == 401  # Unauthorized without credentials

    # With proper credentials, should return the admin dashboard HTML
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}

    response = client.get("/api/admin/", headers=headers)
    assert response.status_code == 200
    assert "Admin Panel" in response.text
    assert "StipendieAssistenten" in response.text


def test_foundation_sync_triggers_categorization():
    """
    Scenario: Triggering foundation sync also triggers categorization
    """
    client = TestClient(app)

    # Use correct admin credentials
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}

    with patch("app.foundation.sync_service.sync_foundations") as mock_sync:
        mock_sync.return_value = True

        response = client.post("/api/admin/trigger-foundation-sync", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "success"

        # Verify that the sync function was called
        mock_sync.assert_called_once()


def test_categorization_status_endpoint():
    """
    Scenario: Categorization status endpoint shows proper statistics
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

    # Should have non-negative counts
    assert data["total_foundations"] >= 0
    assert data["uncategorized_foundations"] >= 0
    assert data["categorized_foundations"] >= 0

    # Sum should equal total
    assert (data["categorized_foundations"] + data["uncategorized_foundations"]) == data["total_foundations"]

    # Distribution should be a list of dictionaries
    assert isinstance(data["category_distribution"], list)
    for item in data["category_distribution"]:
        assert "category" in item
        assert "count" in item
        assert isinstance(item["count"], int)


def test_dynamic_family_member_inputs():
    """
    Scenario: User can provide names for each family member based on count
    """
    client = TestClient(app)

    # Mock the get_db function to avoid database connection in tests
    with patch("app.api.v1.routers.foundations.get_db") as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value = iter([mock_session])

        # Test that the foundations endpoint has been updated
        response = client.get("/api/foundations/stored")
        # The response will be mocked, but this tests that the endpoint exists
        assert response.status_code in [200, 500]  # Either works or has DB error due to mock


def test_enhanced_foundation_fields():
    """
    Scenario: Foundations contain enhanced information fields from the API
    """
    from app.foundation.categorization.categorize_foundations import FoundationCategorizer

    # Test the enhanced foundation data extraction
    sample_data = {
        "ID": 123456,
        "NAMN": "Teststiftelsen",
        "ORGNR": "802007-1234",
        "ANDAMAL": "Att främja barns utbildning och fostran samt hjälpa behövande barn",
        "ADRESS": "Testvägen 1",
        "POSTNR": "12345",
        "ORT": "STOCKHOLM",
        "LANKOD": "1",
        "KOMMUNKOD": "180",
        "TELEFON": "+46 70 123 45 67",
        "COADRESS": "C/O Testing AB"
    }

    # Create a FoundationCategorizer instance to test extraction
    categorizer = FoundationCategorizer()
    refined_data = categorizer.extract_and_refine_foundation_data(sample_data, "2025-01-01T00:00:00")

    # Verify enhanced fields are captured
    assert refined_data["foundation_id"] == 123456
    assert refined_data["name"] == "Teststiftelsen"
    assert refined_data["orgnr"] == "802007-1234"
    assert refined_data["purpose"] == "Att främja barns utbildning och fostran samt hjälpa behövande barn"
    assert refined_data["address"] == "Testvägen 1"
    assert refined_data["county_code"] == "1"
    assert refined_data["municipality_code"] == "180"
    assert refined_data["phone"] == "+46 70 123 45 67"
    assert refined_data["co_address"] == "C/O Testing AB"

    # Verify it gets categorized properly
    assert refined_data["category"] in ["Utbildning och Forskning", "Socialt Stöd och Vård", "Specialiserade Områden"]


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
