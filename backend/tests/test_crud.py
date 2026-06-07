"""
Unit tests for CRUD operations — backend
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from app.crud.crud import (
    get_foundation_batch_size,
    get_foundations_with_category_filter,
    get_applications,
    get_application,
    create_application,
    update_application,
    get_profile,
    save_profile,
    get_foundations,
    get_foundation,
    get_foundations_by_county_code,
    get_foundations_by_municipality_code,
    get_foundation_by_db_id,
    create_or_update_foundation,
    create_foundations,
    create_foundations_batch,
    delete_all_foundations,
    delete_all_profiles,
    delete_all_applications,
    get_grants,
    get_grant,
    create_grant,
    update_grant,
    delete_grant,
)


# db_session fixture is provided by conftest.py — but we also need make_mock_session helper


def make_mock_session():
    """Create a properly configured mock Session for CRUD tests."""
    session = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    order_by_mock = MagicMock()
    all_mock = MagicMock()
    first_mock = MagicMock()
    delete_mock = MagicMock()
    count_mock = MagicMock()
    commit_mock = MagicMock()
    refresh_mock = MagicMock()
    add_mock = MagicMock()

    session.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    query_mock.order_by.return_value = order_by_mock
    query_mock.all.return_value = all_mock
    query_mock.first.return_value = first_mock
    query_mock.delete.return_value = delete_mock
    query_mock.count.return_value = count_mock
    session.commit = commit_mock
    session.refresh = refresh_mock
    session.add = add_mock

    return session


# --- get_foundation_batch_size ---

def test_get_foundation_batch_size_default():
    """Returns 500 when no settings override"""
    mock_settings = MagicMock()
    mock_settings.FOUNDATION_BATCH_SIZE = None
    with patch('app.crud.crud.settings', mock_settings):
        assert get_foundation_batch_size() == 500


def test_get_foundation_batch_size_custom():
    """Returns custom value from settings"""
    mock_settings = MagicMock()
    mock_settings.FOUNDATION_BATCH_SIZE = 200
    with patch('app.crud.crud.settings', mock_settings):
        assert get_foundation_batch_size() == 200


def test_get_foundation_batch_size_min():
    """Returns 50 (min) when setting is below 50"""
    mock_settings = MagicMock()
    mock_settings.FOUNDATION_BATCH_SIZE = 10
    with patch('app.crud.crud.settings', mock_settings):
        assert get_foundation_batch_size() == 50


def test_get_foundation_batch_size_exception():
    """Returns 500 when settings access raises exception"""
    with patch('app.crud.crud.settings', create=True) as mock_settings:
        mock_settings.__dict__.clear()
        type(mock_settings).FOUNDATION_BATCH_SIZE = PropertyMock(
            side_effect=Exception("config error")
        )
        assert get_foundation_batch_size() == 500


# --- Foundation CRUD ---

def test_get_foundations_empty():
    """Returns empty list when no foundations exist"""
    session = make_mock_session()
    session.query.return_value.all.return_value = []
    result = get_foundations(session)
    assert result == []


def test_get_foundations_with_data():
    """Returns list of foundations"""
    session = make_mock_session()
    mock_foundation = MagicMock()
    session.query.return_value.all.return_value = [mock_foundation]
    result = get_foundations(session)
    assert len(result) == 1
    assert result[0] == mock_foundation


def test_get_foundation_by_id_found():
    """Returns foundation when foundation_id matches"""
    session = make_mock_session()
    mock_foundation = MagicMock()
    mock_foundation.foundation_id = 123456
    session.query.return_value.filter.return_value.first.return_value = mock_foundation
    result = get_foundation(session, 123456)
    assert result == mock_foundation


def test_get_foundation_by_id_not_found():
    """Returns None when foundation_id doesn't match"""
    session = make_mock_session()
    session.query.return_value.filter.return_value.first.return_value = None
    result = get_foundation(session, 999999)
    assert result is None


def test_get_foundation_by_id_none():
    """Returns None when foundation_id is None"""
    session = make_mock_session()
    # Properly chain the mock so first() returns None
    session.query.return_value.filter.return_value.first.return_value = None
    result = get_foundation(session, 0)  # type: ignore - testing edge case
    assert result is None


def test_get_foundations_by_county_code():
    """Returns foundations filtered by county code"""
    session = make_mock_session()
    mock_foundation = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [mock_foundation]
    result = get_foundations_by_county_code(session, "180")
    assert len(result) == 1


def test_get_foundations_by_municipality_code():
    """Returns foundations filtered by municipality code"""
    session = make_mock_session()
    mock_foundation = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [mock_foundation]
    result = get_foundations_by_municipality_code(session, "180")
    assert len(result) == 1


def test_get_foundation_by_db_id():
    """Returns foundation by database id"""
    session = make_mock_session()
    mock_foundation = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = mock_foundation
    result = get_foundation_by_db_id(session, 42)
    assert result == mock_foundation


def test_create_or_update_foundation_new():
    """Creates a new foundation"""
    session = make_mock_session()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()

    result = create_or_update_foundation(session, {"foundation_id": 123, "name": "Test"})

    session.add.assert_called_once()
    session.commit.assert_called_once()
    assert result is not None


def test_create_or_update_foundation_existing():
    """Updates an existing foundation, preserving translated_purpose"""
    session = make_mock_session()
    existing = MagicMock()
    existing.translated_purpose = "existing translation"
    existing.purpose_embedding = [0.1, 0.2]
    session.query.return_value.filter.return_value.first.return_value = existing
    session.commit = MagicMock()
    session.refresh = MagicMock()

    result = create_or_update_foundation(session, {
        "foundation_id": 123,
        "name": "Updated Name",
        "translated_purpose": "new translation",
        "purpose_embedding": [0.3, 0.4],
    })

    # Should NOT overwrite preserved fields
    assert existing.translated_purpose == "existing translation"
    assert existing.purpose_embedding == [0.1, 0.2]
    # But should update other fields
    assert existing.name == "Updated Name"
    session.commit.assert_called_once()


def test_create_foundations():
    """Creates/updates multiple foundations"""
    session = make_mock_session()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()

    data = [
        {"foundation_id": 1, "name": "First"},
        {"foundation_id": 2, "name": "Second"},
    ]
    result = create_foundations(session, data)
    assert len(result) == 2


def test_create_foundations_batch():
    """Creates/updates multiple foundations in one transaction"""
    session = make_mock_session()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()

    data = [
        {"foundation_id": 1, "name": "First"},
        {"foundation_id": 2, "name": "Second"},
    ]
    result = create_foundations_batch(session, data)
    assert len(result) == 2


def test_delete_all_foundations():
    """Deletes all foundations and returns count"""
    session = make_mock_session()
    session.query.return_value.delete.return_value = 42
    session.commit = MagicMock()
    result = delete_all_foundations(session)
    assert result == 42


def test_delete_all_profiles():
    """Deletes all profiles and returns count"""
    session = make_mock_session()
    session.query.return_value.delete.return_value = 1
    session.commit = MagicMock()
    result = delete_all_profiles(session)
    assert result == 1


def test_delete_all_applications():
    """Deletes all applications and returns count"""
    session = make_mock_session()
    session.query.return_value.delete.return_value = 25
    session.commit = MagicMock()
    result = delete_all_applications(session)
    assert result == 25


# --- Application CRUD ---

def test_get_applications_empty(db_session):
    """Returns empty list when no applications exist"""
    db_session.query.return_value.all.return_value = []
    result = get_applications(db_session)
    assert result == []


def test_get_application_found(db_session):
    """Returns application when found"""
    mock_app = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = mock_app
    result = get_application(db_session, 1)
    assert result == mock_app


def test_get_application_not_found(db_session):
    """Returns None when application not found"""
    db_session.query.return_value.filter.return_value.first.return_value = None
    result = get_application(db_session, 999)
    assert result is None


def test_create_application(db_session):
    """Creates a new application"""
    mock_app = MagicMock()
    db_session.add = MagicMock()
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    # Mock pydantic model with correct Application fields
    application = MagicMock()
    application.dict.return_value = {
        "user_id": "12345678-1234-5678-1234-567890123456",
        "foundation_id": 123,
        "status": "draft",
        "notes": "Test notes",
        "content": "Test content",
    }

    result = create_application(db_session, application)
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()


def test_update_application(db_session):
    """Updates an existing application"""
    mock_app = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = mock_app
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    update = MagicMock()
    update.dict.return_value = {"name": "Updated"}

    result = update_application(db_session, 1, update)
    assert result == mock_app
    db_session.commit.assert_called_once()


def test_update_application_not_found(db_session):
    """Returns None when application to update doesn't exist"""
    db_session.query.return_value.filter.return_value.first.return_value = None
    update = MagicMock()
    update.dict.return_value = {"name": "Updated"}
    result = update_application(db_session, 999, update)
    assert result is None


# --- Profile CRUD ---

def test_get_profile_found(db_session):
    """Returns profile when found"""
    mock_profile = MagicMock()
    db_session.query.return_value.first.return_value = mock_profile
    result = get_profile(db_session)
    assert result == mock_profile


def test_get_profile_not_found(db_session):
    """Returns None when no profile exists"""
    db_session.query.return_value.first.return_value = None
    result = get_profile(db_session)
    assert result is None


def test_save_profile_create_new(db_session):
    """Creates a new profile"""
    db_session.query.return_value.first.return_value = None
    db_session.add = MagicMock()
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    profile = MagicMock()
    if hasattr(profile, 'model_dump'):
        profile.model_dump.return_value = {"name": "Test"}
    else:
        profile.dict.return_value = {"name": "Test"}

    result = save_profile(db_session, profile)
    db_session.add.assert_called_once()


def test_save_profile_update_existing(db_session):
    """Updates an existing profile"""
    existing = MagicMock()
    db_session.query.return_value.first.return_value = existing
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    profile = MagicMock()
    if hasattr(profile, 'model_dump'):
        profile.model_dump.return_value = {"name": "Updated"}
    else:
        profile.dict.return_value = {"name": "Updated"}

    result = save_profile(db_session, profile)
    assert existing.name == "Updated"
    db_session.commit.assert_called_once()


# --- Grant CRUD ---

def test_get_grants_empty(db_session):
    """Returns empty list when no grants exist"""
    db_session.query.return_value.all.return_value = []
    result = get_grants(db_session)
    assert result == []


def test_get_grant_found(db_session):
    """Returns grant when found"""
    mock_grant = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = mock_grant
    result = get_grant(db_session, 1)
    assert result == mock_grant


def test_get_grant_not_found(db_session):
    """Returns None when grant not found"""
    db_session.query.return_value.filter.return_value.first.return_value = None
    result = get_grant(db_session, 999)
    assert result is None


def test_create_grant(db_session):
    """Creates a new grant"""
    mock_grant = MagicMock()
    db_session.add = MagicMock()
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    grant = MagicMock()
    grant.dict.return_value = {"name": "Test"}

    result = create_grant(db_session, grant)
    db_session.add.assert_called_once()


def test_update_grant(db_session):
    """Updates an existing grant"""
    mock_grant = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = mock_grant
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    update = MagicMock()
    update.dict.return_value = {"name": "Updated"}

    result = update_grant(db_session, 1, update)
    assert result == mock_grant


def test_update_grant_not_found(db_session):
    """Returns None when grant to update doesn't exist"""
    db_session.query.return_value.filter.return_value.first.return_value = None
    update = MagicMock()
    update.dict.return_value = {"name": "Updated"}
    result = update_grant(db_session, 999, update)
    assert result is None


def test_delete_grant_found(db_session):
    """Deletes a grant when found"""
    mock_grant = MagicMock()
    db_session.query.return_value.filter.return_value.first.return_value = mock_grant
    db_session.delete = MagicMock()
    db_session.commit = MagicMock()

    result = delete_grant(db_session, 1)
    assert result is True
    db_session.delete.assert_called_once_with(mock_grant)


def test_delete_grant_not_found(db_session):
    """Returns False when grant to delete doesn't exist"""
    db_session.query.return_value.filter.return_value.first.return_value = None
    result = delete_grant(db_session, 999)
    assert result is False


# --- get_foundations_with_category_filter ---

def test_get_foundations_with_category_filter_no_filters(db_session):
    """Returns all foundations when no filters"""
    mock_foundation = MagicMock()
    db_session.query.return_value.all.return_value = [mock_foundation]
    result = get_foundations_with_category_filter(db_session)
    assert len(result) == 1


def test_get_foundations_with_category_filter_q_filter(db_session):
    """Filters by search query"""
    mock_foundation = MagicMock()
    db_session.query.return_value.filter.return_value.all.return_value = [mock_foundation]
    db_session.query.return_value.all.return_value = []
    result = get_foundations_with_category_filter(db_session, q="test")
    assert len(result) == 1


def test_get_foundations_with_category_filter_category_filter(db_session):
    """Filters by category"""
    mock_foundation = MagicMock()
    db_session.query.return_value.filter.return_value.all.return_value = [mock_foundation]
    db_session.query.return_value.all.return_value = []
    result = get_foundations_with_category_filter(db_session, category="Utbildning")
    assert len(result) == 1


def test_get_foundations_with_category_filter_sort_by_name(db_session):
    """Sorts by name"""
    mock_foundation = MagicMock()
    db_session.query.return_value.order_by.return_value.all.return_value = [mock_foundation]
    db_session.query.return_value.filter.return_value.all.return_value = []
    db_session.query.return_value.all.return_value = []
    result = get_foundations_with_category_filter(db_session, sort="name")
    assert len(result) == 1


def test_get_foundations_with_category_filter_sort_by_location(db_session):
    """Sorts by location"""
    mock_foundation = MagicMock()
    db_session.query.return_value.order_by.return_value.all.return_value = [mock_foundation]
    db_session.query.return_value.filter.return_value.all.return_value = []
    db_session.query.return_value.all.return_value = []
    result = get_foundations_with_category_filter(db_session, sort="location")
    assert len(result) == 1
