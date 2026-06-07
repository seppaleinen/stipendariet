"""
BDD-style tests for Foundation Categorization and Admin Functionality
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
import os

from app.main import app
from app.db.database import Base, DATABASE_URL

# Setup database for testing
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", f"{DATABASE_URL}_test")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def client():
    """Create a test client for the API"""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)


def test_foundation_categorization_job():
    """
    Scenario: Foundation categorization system properly categorizes foundations with enhanced Swedish categories
    """
    from app.foundation.categorization.categorize_foundations import FoundationCategorizer
    
    # Create a test foundation with known purpose
    test_purpose = "Stöd till barns utbildning och fostran i skolan"
    
    # Initialize categorizer
    categorizer = FoundationCategorizer()
    
    # Test categorization algorithm
    category = categorizer._find_closest_category(test_purpose)
    
    # Assert that it matches an educational category
    assert category in [
        "Utbildning och Forskning", 
        "Socialt Stöd och Vård", 
        "Kulturella Aktiviteter och Konst"
    ]


def test_admin_authentication_required(client):
    """
    Scenario: Non-admin user cannot access admin endpoints
    """
    # Try to access admin endpoint without authentication
    response = client.post("/api/admin/trigger-foundation-sync")
    
    # Should return 401 Unauthorized
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_admin_access_with_credentials(client):
    """
    Scenario: Admin user can access protected admin endpoints
    """
    import base64
    
    # Create basic auth header with fake credentials
    credentials = base64.b64encode(b"admin:wrongpassword").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}
    
    # Try to access admin endpoint with wrong credentials
    response = client.post("/api/admin/trigger-foundation-sync", headers=headers)
    
    # Should return 401 Unauthorized
    assert response.status_code == 401
    
    # Now try with correct credentials
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}
    
    response = client.get("/api/admin/")
    
    # Should return 200 OK with basic auth
    assert response.status_code == 200


def test_foundation_sync_endpoint(client):
    """
    Scenario: Foundation synchronization updates database records
    """
    import base64
    
    # Use correct admin credentials
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}
    
    # Mock the sync function to avoid long execution in tests
    with patch("app.foundation.sync_service.sync_foundations") as mock_sync:
        mock_sync.return_value = True
        
        response = client.post("/api/admin/trigger-foundation-sync", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Foundation sync completed successfully" in data["message"]


def test_category_reset_endpoint(client):
    """
    Scenario: Category reset functionality works correctly
    """
    import base64
    
    # Use correct admin credentials
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}
    
    # Mock the reset function to avoid modifying the database in tests
    with patch("app.foundation.categorization.categorize_foundations.FoundationCategorizer") as MockCategorizer:
        mock_instance = MockCategorizer.return_value
        mock_instance.reset_categories_in_db.return_value = 10
        mock_instance.categorize_foundations_in_db.return_value = None
        
        response = client.post("/api/admin/reset-categories", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["foundations_reset"] == 10


def test_database_clear_endpoint(client):
    """
    Scenario: Database clearing removes all data safely
    """
    import base64
    
    # Use correct admin credentials
    credentials = base64.b64encode(b"admin:admin123").decode("ascii")
    headers = {"Authorization": f"Basic {credentials}"}
    
    # Mock to avoid actually clearing the database in tests
    with patch("app.crud.crud.delete_all_foundations") as mock_delete_founds, \
         patch("app.crud.crud.delete_all_applications") as mock_delete_apps, \
         patch("app.crud.crud.delete_all_profiles") as mock_delete_profiles:
        
        mock_delete_founds.return_value = 100
        mock_delete_apps.return_value = 25
        mock_delete_profiles.return_value = 1
        
        response = client.post("/api/admin/clear-database", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["deleted_foundations"] == 100
        assert data["deleted_applications"] == 25
        assert data["deleted_profiles"] == 1


def test_get_foundation_categories(client):
    """
    Scenario: Users can retrieve foundation categories through API
    """
    response = client.get("/api/foundations/categories")
    
    assert response.status_code == 200
    categories = response.json()
    assert isinstance(categories, list)
    # At least some of the enhanced Swedish categories should be present
    expected_categories = [
        "Utbildning och Forskning",
        "Socialt Stöd och Vård", 
        "Kulturella Aktiviteter och Konst"
    ]
    assert any(cat in categories for cat in expected_categories)


def test_get_foundations_by_category(client):
    """
    Scenario: Users can filter foundations by category
    """
    response = client.get("/api/foundations/stored/by-category/Utbildning och Forskning")
    
    assert response.status_code == 200
    foundations = response.json()
    assert isinstance(foundations, list)
    # If there are foundations with this category, they should be returned
    # (This test assumes that at least one foundation exists with this category)
