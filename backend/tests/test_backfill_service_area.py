"""Tests for the service area backfill admin endpoint."""

from unittest.mock import patch

import pytest

from app.api.admin.enrichment import backfill_service_area_endpoint


class _FakeFoundation:
    def __init__(self, foundation_id: int, name: str, purpose=None, summary=None):
        self.id = foundation_id
        self.name = name
        self.purpose = purpose
        self.summary = summary


class _FakeQuery:
    """Chainable query stub: filter/order_by/limit return self; all returns rows."""

    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.query_stub = _FakeQuery(rows)

    def query(self, *args, **kwargs):
        return self.query_stub

    def close(self):
        pass


def _patched_get_db(rows):
    """Return a get_db replacement yielding a session backed by the given rows."""

    def _get_db():
        yield _FakeSession(rows)

    return _get_db


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
@patch("app.pipeline.orchestrator._db_save_parsed_service_area")
async def test_backfill_processes_null_rows(mock_save, mock_extract):
    """Foundations with parsed_service_area IS NULL get extracted and saved."""
    rows = [
        _FakeFoundation(1, "Stiftelsen Kalmar", purpose="För Kalmar"),
        _FakeFoundation(2, "Stiftelsen Skåne", purpose="För Skåne"),
    ]
    mock_extract.side_effect = [
        {"municipality_code": "0880", "county_code": "08", "confidence": "high"},
        {"municipality_code": None, "county_code": "12", "confidence": "medium"},
    ]

    with patch("app.db.database.get_db", _patched_get_db(rows)):
        result = await backfill_service_area_endpoint(limit=20, delay_seconds=0)

    assert result["status"] == "success"
    assert result["processed"] == 2
    assert result["failed"] == 0
    assert result["failures"] == []

    # Extract called per foundation with name + purpose + summary (extract-only, no scraping)
    assert mock_extract.call_count == 2
    mock_extract.assert_any_call("Stiftelsen Kalmar", purpose="För Kalmar", description=None)
    mock_extract.assert_any_call("Stiftelsen Skåne", purpose="För Skåne", description=None)

    # Each result saved (overwrite semantics via the shared orchestrator helper)
    mock_save.assert_any_call(1, {"municipality_code": "0880", "county_code": "08", "confidence": "high"})
    mock_save.assert_any_call(2, {"municipality_code": None, "county_code": "12", "confidence": "medium"})
    assert mock_save.call_count == 2


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
@patch("app.pipeline.orchestrator._db_save_parsed_service_area")
async def test_backfill_skips_non_geographic_foundations(mock_save, mock_extract):
    """A NULL extraction result (no geographic restriction) is not saved but still counts as processed."""
    rows = [_FakeFoundation(3, "Allmän stiftelse", purpose="Hjälpa behövande")]
    mock_extract.return_value = None

    with patch("app.db.database.get_db", _patched_get_db(rows)):
        result = await backfill_service_area_endpoint(limit=20, delay_seconds=0)

    assert result["processed"] == 1
    assert result["failed"] == 0
    mock_save.assert_not_called()


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
@patch("app.pipeline.orchestrator._db_save_parsed_service_area")
async def test_backfill_reports_failures(mock_save, mock_extract):
    """Extraction exceptions are collected and reported without aborting the batch."""
    rows = [
        _FakeFoundation(4, "Bra stiftelse"),
        _FakeFoundation(5, "Felande stiftelse"),
    ]
    mock_extract.side_effect = [
        {"municipality_code": "0180", "county_code": "01", "confidence": "high"},
        RuntimeError("LLM timeout"),
    ]

    with patch("app.db.database.get_db", _patched_get_db(rows)):
        result = await backfill_service_area_endpoint(limit=20, delay_seconds=0)

    assert result["processed"] == 1
    assert result["failed"] == 1
    assert result["failures"][0]["id"] == 5
    assert result["failures"][0]["error"] == "LLM timeout"
    mock_save.assert_called_once_with(4, {"municipality_code": "0180", "county_code": "01", "confidence": "high"})


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
async def test_backfill_no_work_when_no_null_rows(mock_extract):
    """Idempotency: re-running when nothing has NULL parsed_service_area is a no-op."""
    with patch("app.db.database.get_db", _patched_get_db([])):
        result = await backfill_service_area_endpoint(limit=20, delay_seconds=0)

    assert result["status"] == "no_work"
    assert result["processed"] == 0
    mock_extract.assert_not_called()
