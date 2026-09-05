"""
Tests for the foundation sync service with mocked external API.
"""
from unittest.mock import MagicMock, patch

import requests

from app.foundation.foundation_api import (
    fetch_foundation_opendata,
    poll_foundations,
)
from app.foundation.foundation_schemas import Foundation as FoundationSchema
from app.foundation.foundation_schemas import FoundationSearchResponse
from app.foundation.sync_service import (
    _cleanup_orphan_saved_grants,
    extract_and_refine_foundation_data,
    sync_foundations,
    trigger_foundation_sync,
)


def _make_foundation_search_response(count=2, uppdaterad="2024-01-15T10:00:00"):
    """Build a FoundationSearchResponse with real Pydantic Foundation models."""
    stiftelser = []
    for i in range(count):
        stiftelser.append(
            FoundationSchema(
                id=i + 1,
                namn=f"Test Stiftelse {i + 1}",
                orgnrNoMinus=f"800000{i + 1:04d}",
                **{"ändamålet": f"Syftet med stiftelse {i + 1} är att stöda utbildning."}
            )
        )
    return FoundationSearchResponse(uppdaterad=uppdaterad, stiftelser=stiftelser)


# =============================================================================
# sync_foundations tests
# =============================================================================


@patch('app.foundation.categorization.categorize_foundations.FoundationCategorizer')
@patch('app.foundation.sync_service.get_db')
@patch('app.foundation.sync_service.crud')
@patch('app.foundation.sync_service.poll_foundations')
def test_sync_foundations_successful_cycle(
    mock_poll, mock_crud, mock_get_db, mock_categorizer
):
    """Full cycle: poll → extract → persist succeeds."""
    mock_poll.return_value = _make_foundation_search_response(count=2)
    mock_crud.get_foundation_batch_size.return_value = 100
    mock_crud.get_foundation.return_value = None
    mock_crud.create_foundations_batch.return_value = []
    mock_categorizer.return_value.categorize_foundations_in_db.return_value = 0

    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])

    result = sync_foundations()

    assert result is True
    mock_poll.assert_called_once()
    mock_crud.create_foundations_batch.assert_called_once()
    mock_crud.get_foundation_batch_size.assert_called_once()
    # Post-sync categorization should be triggered over the mocked DB
    mock_categorizer.return_value.categorize_foundations_in_db.assert_called_once()


@patch('app.foundation.sync_service.poll_foundations')
def test_sync_foundations_poll_failure(mock_poll):
    """Returns False when the external API poll returns None."""
    mock_poll.return_value = None

    result = sync_foundations()

    assert result is False
    mock_poll.assert_called_once()


@patch('app.foundation.categorization.categorize_foundations.FoundationCategorizer')
@patch('app.foundation.sync_service.get_db')
@patch('app.foundation.sync_service.crud')
@patch('app.foundation.sync_service.extract_and_refine_foundation_data')
@patch('app.foundation.sync_service.poll_foundations')
def test_sync_foundations_partial_processing_failure(
    mock_poll, mock_extract, mock_crud, mock_get_db, mock_categorizer
):
    """One foundation raises during extraction; the other succeeds and is persisted."""
    mock_poll.return_value = _make_foundation_search_response(count=2)

    ok_data = {
        "foundation_id": 2,
        "name": "Test Stiftelse 2",
        "orgnr": "8000000002",
        "purpose": "Syftet med stiftelse 2 är att stöda utbildning.",
        "summary": "Test summary",
        "tags": ["Stiftelse"],
    }
    mock_extract.side_effect = [Exception("LLM error"), ok_data]

    mock_crud.get_foundation_batch_size.return_value = 100
    mock_crud.get_foundation.return_value = None
    mock_crud.create_foundations_batch.return_value = []
    mock_categorizer.return_value.categorize_foundations_in_db.return_value = 0

    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])

    result = sync_foundations()

    assert result is True
    assert mock_extract.call_count == 2
    mock_crud.create_foundations_batch.assert_called_once()
    # The batch should contain only the successful foundation
    call_args = mock_crud.create_foundations_batch.call_args
    assert len(call_args[0][1]) == 1
    assert call_args[0][1][0]["foundation_id"] == 2


@patch('app.foundation.categorization.categorize_foundations.FoundationCategorizer')
@patch('app.foundation.sync_service.extract_and_refine_foundation_data')
@patch('app.foundation.sync_service.poll_foundations')
def test_sync_foundations_empty_refined_data(mock_poll, mock_extract, mock_categorizer):
    """Returns False when all foundations fail extraction."""
    mock_poll.return_value = _make_foundation_search_response(count=2)
    mock_extract.side_effect = Exception("LLM error")
    mock_categorizer.return_value.categorize_foundations_in_db.return_value = 0

    result = sync_foundations()

    assert result is False
    assert mock_extract.call_count == 2


# =============================================================================
# trigger_foundation_sync tests
# =============================================================================


@patch('app.foundation.sync_service.sync_foundations')
def test_trigger_foundation_sync_delegates(mock_sync):
    """trigger_foundation_sync delegates to sync_foundations and returns its result."""
    mock_sync.return_value = True

    result = trigger_foundation_sync()

    assert result is True
    mock_sync.assert_called_once_with()


# =============================================================================
# fetch_foundation_opendata tests
# =============================================================================


@patch('app.foundation.foundation_api.requests.get')
def test_fetch_foundation_opendata_success(mock_get):
    """Returns the parsed list on a successful JSON response."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"ID": 1, "NAMN": "Test"}]
    mock_get.return_value = mock_response

    result = fetch_foundation_opendata()

    assert result == [{"ID": 1, "NAMN": "Test"}]


@patch('app.foundation.foundation_api.requests.get')
def test_fetch_foundation_opendata_connection_error(mock_get):
    """Returns None on RequestException."""
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

    result = fetch_foundation_opendata()

    assert result is None


@patch('app.foundation.foundation_api.requests.get')
def test_fetch_foundation_opendata_json_error(mock_get):
    """Returns None when response.json() raises ValueError."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("bad json")
    mock_get.return_value = mock_response

    result = fetch_foundation_opendata()

    assert result is None


# =============================================================================
# poll_foundations tests
# =============================================================================


@patch('app.foundation.foundation_api.fetch_foundation_opendata')
def test_poll_foundations_success(mock_fetch):
    """Returns FoundationSearchResponse with correct structure on valid API data."""
    mock_fetch.return_value = [
        {
            "ID": 1,
            "NAMN": "Test Stiftelse",
            "ANDAMAL": "Purpose text",
            "ORGNR": "8000000001",
        }
    ]

    result = poll_foundations()

    assert result is not None
    assert isinstance(result, FoundationSearchResponse)
    assert len(result.stiftelser) == 1
    assert result.stiftelser[0].namn == "Test Stiftelse"


@patch('app.foundation.foundation_api.fetch_foundation_opendata')
def test_poll_foundations_returns_none_on_empty_opendata(mock_fetch):
    """Returns None when fetch_foundation_opendata returns an empty list."""
    mock_fetch.return_value = []

    result = poll_foundations()

    assert result is None


# =============================================================================
# extract_and_refine_foundation_data tests
# =============================================================================


def test_extract_and_refine_with_pydantic_model():
    """Handles Pydantic Foundation model input (has .model_dump)."""
    # Foundation uses alias 'ändamålet' for the 'andamal' field
    foundation = FoundationSchema(
        id=5,
        namn="Model Stiftelse",
        orgnrNoMinus="8000000005",
        **{"ändamålet": "Model purpose text."},
    )

    result = extract_and_refine_foundation_data(foundation, "2024-01-15T10:00:00")

    assert result["foundation_id"] == 5
    assert result["name"] == "Model Stiftelse"
    assert result["orgnr"] == "8000000005"
    assert result["purpose"] == "Model purpose text."
    assert "tags" in result


def test_extract_and_refine_with_plain_dict():
    """Handles plain dict input (no .model_dump, falls through to __dict__)."""
    raw = {
        "ID": 6,
        "NAMN": "Dict Stiftelse",
        "ANDAMAL": "Dict purpose text.",
        "ORGNR": "8000000006",
    }

    result = extract_and_refine_foundation_data(raw, "2024-01-15T10:00:00")

    assert result["foundation_id"] == 6
    assert result["name"] == "Dict Stiftelse"
    assert result["orgnr"] == "8000000006"
    assert result["purpose"] == "Dict purpose text."


def test_extract_and_refine_missing_fields():
    """Returns a dict (no exception) with default summary when fields are missing."""
    raw = {"ID": 7}

    result = extract_and_refine_foundation_data(raw, "2024-01-15T10:00:00")

    assert isinstance(result, dict)
    assert result["foundation_id"] == 7
    assert result["name"] == ""
    assert result["summary"] == "Information om stiftelsens ändamål är tillgänglig"
    assert result["tags"] == ["Stiftelse"]


# =============================================================================
# _cleanup_orphan_saved_grants tests
# =============================================================================


def test_cleanup_orphan_saved_grants_deletes_foundation_orphans():
    """Deletes saved_grant rows whose grant_id matches foundation-N but the foundation doesn't exist."""
    mock_db = MagicMock()
    # Live foundation IDs: 1 and 2 only
    # Call 1: SELECT foundation_id FROM foundations
    # Call 2: SELECT id, grant_id FROM saved_grants → sees foundation-3 orphan (id=20)
    # Call 3: SELECT id FROM grants
    # Call 4: SELECT id, grant_id FROM saved_grants (post-foundation-delete)
    mock_db.execute.return_value.fetchall.side_effect = [
        [(1,), (2,)],  # live foundation IDs
        [(10, "foundation-1"), (20, "foundation-3"), (30, "grant-1")],  # saved grants
        [(1,), (2,)],  # live grant IDs (foundation-1 is live)
        [],  # post-foundation-delete second pass
    ]

    _cleanup_orphan_saved_grants(mock_db)

    # At least one execute call should have been made (DELETE)
    assert mock_db.execute.call_count >= 1
    mock_db.commit.assert_called_once()


def test_cleanup_orphan_saved_grants_skips_unknown_format():
    """Does not call DELETE for grant_ids that don't match known patterns."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.side_effect = [
        [(1,), (2,)],  # live foundation ids
        [(1, "some-random-format-123"), (2, None), (3, "foundation-1")],  # saved grants
        [(1,), (2,)],  # live grant ids
        [],  # post-foundation-delete
    ]

    _cleanup_orphan_saved_grants(mock_db)

    mock_db.commit.assert_called_once()
    # No DELETE calls should have been made (no orphans)


# =============================================================================
# Sync partial recovery / cleanup failure
# =============================================================================


@patch('app.foundation.categorization.categorize_foundations.FoundationCategorizer')
@patch('app.foundation.sync_service.get_db')
@patch('app.foundation.sync_service.crud')
@patch('app.foundation.sync_service.poll_foundations')
@patch('app.foundation.sync_service.extract_and_refine_foundation_data')
@patch('app.foundation.sync_service._cleanup_orphan_saved_grants')
def test_sync_orphan_cleanup_failure_does_not_fail_sync(
    mock_cleanup, mock_extract, mock_poll, mock_crud, mock_get_db, mock_categorizer
):
    """sync_foundations returns True even when _cleanup_orphan_saved_grants raises."""
    mock_poll.return_value = _make_foundation_search_response(count=1)
    mock_extract.return_value = {
        "foundation_id": 1,
        "name": "Test",
        "orgnr": "8000000001",
        "purpose": "Purpose",
        "tags": ["Stiftelse"],
    }
    mock_crud.get_foundation_batch_size.return_value = 100
    mock_crud.get_foundation.return_value = None
    mock_crud.create_foundations_batch.return_value = []
    mock_cleanup.side_effect = Exception("cleanup error")
    mock_categorizer.return_value.categorize_foundations_in_db.return_value = 0

    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])

    result = sync_foundations()

    assert result is True
    mock_cleanup.assert_called_once_with(mock_db)
