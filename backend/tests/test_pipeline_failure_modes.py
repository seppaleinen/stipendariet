"""
Tests for graceful degradation of the pipeline when downstream services fail.
Covers extraction, validation, discovery, crawler, and orchestrator failure modes.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.crawler import crawl_foundation_site
from app.pipeline.discovery import discover_candidate_urls
from app.pipeline.extraction import extract_data_from_content
from app.pipeline.orchestrator import run_foundation_pipeline_task
from app.pipeline.validation import validate_candidate_url

# =============================================================================
# Extraction failure modes
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction_returns_none_on_malformed_json(mock_chat):
    """Returns None when LLM returns non-JSON content."""
    mock_chat.return_value = "This is not JSON at all"

    result = await extract_data_from_content("Some content", "Test Foundation")
    assert result is None


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction_returns_none_on_llm_connection_timeout(mock_chat):
    """Returns None when LLM returns None (timeout/connection failure)."""
    mock_chat.return_value = None

    result = await extract_data_from_content("Some content", "Test Foundation")
    assert result is None


# =============================================================================
# Validation failure modes
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.validation.chat_completion')
async def test_validation_returns_is_match_false_on_llm_timeout(mock_chat):
    """Returns is_match=False when LLM returns None; no 'error' key present."""
    mock_chat.return_value = None

    candidate = {"url": "https://www.test.se", "title": "Test", "snippet": "..."}
    result = await validate_candidate_url(candidate, "Test Foundation", "123456")

    assert result["is_match"] is False
    assert result["confidence"] == 0.0
    assert result["raw_llm_response"] is None
    assert "error" not in result


# =============================================================================
# Discovery failure modes
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.discovery._ddgs_search', return_value=[])
@patch('app.pipeline.discovery._probe_url', return_value=False)
async def test_discovery_returns_empty_on_ddg_empty_results(mock_probe, mock_ddgs):
    """Returns empty list when direct probe fails and both DDG searches return []."""
    candidates = await discover_candidate_urls("Test Foundation", "123456")

    assert candidates == []
    assert mock_ddgs.call_count == 2


# =============================================================================
# Crawler failure modes
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.crawler.async_playwright')
async def test_crawl_returns_empty_on_browserless_connection_failure(mock_pw):
    """Returns [] when both CDP connect and headless launch fail."""
    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.connect_over_cdp = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    mock_pw_instance.chromium.launch = AsyncMock(
        side_effect=Exception("Launch failed")
    )

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw_instance)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_pw.return_value = mock_cm

    result = await crawl_foundation_site("https://www.test.se")
    assert result == []


# =============================================================================
# Orchestrator — full pipeline with all downstream failures
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.orchestrator.validate_candidate_url')
@patch('app.pipeline.orchestrator.discover_candidate_urls')
@patch('app.pipeline.orchestrator.extract_service_area')
async def test_orchestrator_full_pipeline_all_downstream_failures(
    mock_extract_area, mock_discover, mock_validate
):
    """Pipeline returns no_valid_site when service area is None and no URL matches."""
    mock_extract_area.return_value = None
    mock_discover.return_value = [
        {"url": "https://a.com", "title": "A", "snippet": "s1"},
        {"url": "https://b.com", "title": "B", "snippet": "s2"},
    ]
    mock_validate.return_value = {
        "is_match": False,
        "confidence": 0.0,
        "raw_llm_response": None,
    }

    result = await run_foundation_pipeline_task({}, foundation_id=1)

    assert result["status"] == "no_valid_site"
    assert "trace" in result
    assert len(result["trace"]["discovery"]) == 2
    assert len(result["trace"]["validation"]) == 2
    assert result["trace"]["service_area"] is None


# =============================================================================
# Extraction failure modes — malformed / wrong-shape JSON
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction_returns_none_on_json_with_wrong_fields(mock_chat):
    """Returns None when LLM returns valid JSON but no fields match the schema."""
    # All keys are unknown; filtered_data will be empty → all-null → None
    mock_chat.return_value = '{"name": "Test", "foo": "bar", "unknown_field": 42}'

    result = await extract_data_from_content("Some content", "Test Foundation")
    assert result is None


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction_returns_none_on_pydantic_validation_error(mock_chat):
    """Returns None when LLM returns JSON that fails Pydantic validation."""
    # application_deadline must be str | None, not int
    mock_chat.return_value = '{"application_deadline": 12345, "contact_email": null}'

    result = await extract_data_from_content("Some content", "Test Foundation")
    assert result is None


# =============================================================================
# Validation failure modes — malformed / wrong-shape JSON
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.validation.chat_completion')
async def test_validation_returns_error_dict_on_json_decode_error(mock_chat):
    """Returns error dict with 'error' key when LLM returns unparseable text."""
    mock_chat.return_value = '{"incomplete json'

    candidate = {"url": "https://www.test.se", "title": "Test", "snippet": "..."}
    result = await validate_candidate_url(candidate, "Test Foundation", "123456")

    assert result["is_match"] is False
    assert result["confidence"] == 0.0
    assert result["raw_llm_response"] is None
    assert "error" in result


@pytest.mark.asyncio
@patch('app.pipeline.validation.chat_completion')
async def test_validation_returns_error_dict_on_wrong_field_types(mock_chat):
    """Returns error dict when JSON parses but float(confidence) raises ValueError."""
    # float("high") raises ValueError → caught by the except block
    mock_chat.return_value = '{"is_match": "yes", "confidence": "high"}'

    candidate = {"url": "https://www.test.se", "title": "Test", "snippet": "..."}
    result = await validate_candidate_url(candidate, "Test Foundation", "123456")

    assert result["is_match"] is False
    assert result["confidence"] == 0.0
    assert result["raw_llm_response"] is None
    assert "error" in result


# =============================================================================
# Discovery failure modes — exceptions
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.discovery._ddgs_search', side_effect=Exception("DDG network error"))
@patch('app.pipeline.discovery._probe_url', return_value=False)
async def test_discovery_returns_empty_on_ddg_exception(mock_probe, mock_ddgs):
    """Returns [] when DDG raises; direct probe failure means no candidates."""
    candidates = await discover_candidate_urls("Test Foundation", "123456")

    assert candidates == []
    assert mock_ddgs.call_count == 2


@pytest.mark.asyncio
@patch('app.pipeline.discovery._ddgs_search')
@patch('app.pipeline.discovery._probe_url')
async def test_discovery_still_returns_results_when_direct_probe_fails(mock_probe, mock_ddgs):
    """DDG results are returned even when the direct slug probe raises."""
    mock_probe.side_effect = Exception("Network error on direct probe")
    mock_ddgs.return_value = [
        {"href": "https://www.example.se", "title": "Example", "body": "snippet"}
    ]

    candidates = await discover_candidate_urls("Test Foundation", "123456")

    assert len(candidates) == 1
    assert candidates[0]["url"] == "https://www.example.se"


# =============================================================================
# Crawler failure modes — fallback to headless launch
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.crawler.async_playwright')
async def test_crawl_returns_pages_on_cdp_fallback_to_headless(mock_pw):
    """Returns pages when CDP fails but headless launch succeeds."""
    # CDP fails; headless launch succeeds
    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.connect_over_cdp = AsyncMock(
        side_effect=Exception("CDP connection refused")
    )

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.evaluate = AsyncMock(
        return_value="Homepage text content"
    )
    mock_page.query_selector_all = MagicMock(return_value=[])

    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw_instance)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_pw.return_value = mock_cm

    result = await crawl_foundation_site("https://www.test.se")

    assert len(result) == 1
    assert result[0]["url"] == "https://www.test.se"
    assert result[0]["content"] == "Homepage text content"
    assert result[0]["type"] == "homepage"
