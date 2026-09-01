from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.discovery import discover_candidate_urls
from app.pipeline.extraction import extract_data_from_content
from app.pipeline.orchestrator import _db_update_foundation_status
from app.pipeline.validation import validate_candidate_url


# Mock DDGS for Discovery
@pytest.mark.asyncio
@patch('app.pipeline.discovery.DDGS')
async def test_discovery(mock_ddgs):
    mock_instance = MagicMock()
    # Return fake search results
    mock_instance.text.return_value = [
        {"href": "https://www.test-foundation.se", "title": "Test Foundation", "body": "Welcome"}
    ]
    mock_ddgs.return_value.__enter__.return_value = mock_instance

    candidates = await discover_candidate_urls("Test Foundation", "123456")
    assert len(candidates) == 1
    assert candidates[0]["url"] == "https://www.test-foundation.se"


# Mock LLM client for Validation (LiteLLM)
@pytest.mark.asyncio
@patch('app.pipeline.validation.chat_completion')
async def test_validation(mock_chat):
    mock_chat.return_value = '{"is_match": true, "confidence": 0.98}'

    candidate = {"url": "https://www.test.se", "title": "Test", "snippet": "..."}
    res = await validate_candidate_url(candidate, "Test", "123")

    assert res["is_match"] is True
    assert res["confidence"] == 0.98


# Mock LLM client for Extraction (LiteLLM)
@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction(mock_chat):
    mock_chat.return_value = '{"application_deadline": "31 mars 2024", "application_open": "1 januari"}'

    res = await extract_data_from_content("Deadline is 31 mars 2024", "Test Foundation")
    assert res is not None
    assert res.application_deadline == "31 mars 2024"
    assert res.application_open == "1 januari"


# GEO Flaw #1 — verify the LLM-returned enriched_description is parsed and persists
# to the foundations row via _db_update_foundation_status (issue #2).
@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extraction_parses_enriched_description(mock_chat):
    mock_chat.return_value = (
        '{"application_deadline": "31 mars 2026", '
        '"enriched_description": "Detta stipendium stödjer universitetsstuderande i Uppsala. '
        'Behöriga är studenter vid Uppsala universitet som är i behov av ekonomiskt stöd för '
        'att kunna genomföra sina studier. Bidraget kan användas för att täcka kurslitteratur, '
        'resor till och från universitetet samt levnadskostnader under studieperioden. '
        'Sökande bör bifoga studieintyg, motivering samt en beskrivning av hur bidraget ska '
        'användas. Tänk på att vara tydlig i din ansökan och visa på konkreta behov. '
        'Uppsala Stiftelsen för Högre Studier delar årligen ut stipendier till motiverade '
        'studenter som uppvisar både goda akademiska resultat och ekonomiskt behov. '
        'Stipendiet kan sökas av alla som är antagna till Uppsala universitet och som kan '
        'redogöra för faktiska kostnader som inte täcks av andra bidrag eller studiemedel. '
        'Tidigare stipendiater har använt medlen för att finansiera utbytesstudier, '
        'språkkurser, sommarkurser utomlands samt dyrare kurslitteratur som inte täcks av '
        'CSN. Vi rekommenderar att du i din ansökan tydligt beskriver din studiesituation, '
        'dina planer för den kommande terminen och hur ett stipendium skulle göra konkret '
        'skillnad för din möjlighet att slutföra studierna. Bifoga gärna ett personligt brev '
        'där du motiverar ditt behov. Lycka till med din ansökan till Uppsala Stiftelsen för '
        'Högre Studier."}'
    )

    res = await extract_data_from_content("Some foundation content", "Test Foundation")
    assert res is not None
    assert res.enriched_description is not None
    # 150+ word Swedish description — sanity-check it parses cleanly
    assert len(res.enriched_description.split()) >= 150
    assert "Uppsala" in res.enriched_description


def test_db_update_foundation_status_persists_enriched_description():
    """When the orchestrator passes enriched_description, the foundation row receives it."""

    class FakeFoundation:
        enriched_description = None
        enrichment_status = None
        enrichment_last_run = None
        enrichment_error = None
        website_url = None
        application_deadline = None
        application_start = None
        application_method = None
        contact_email = None
        contact_phone = None
        who_can_apply = None
        enrichment_notes = None

    fake_foundation = FakeFoundation()

    # Mock SessionLocal() context manager so we can capture the assigned attributes
    fake_session = MagicMock()
    fake_session.query.return_value.filter.return_value.first.return_value = fake_foundation

    with patch("app.pipeline.orchestrator.SessionLocal") as mock_session_local:
        mock_session_local.return_value.__enter__.return_value = fake_session
        mock_session_local.return_value.__exit__.return_value = False

        _db_update_foundation_status(
            42,
            "COMPLETED",
            enriched_description="Substantiv svensk beskrivning om vad stiftelsen finansierar.",
        )

    assert fake_foundation.enrichment_status == "COMPLETED"
    assert fake_foundation.enriched_description == (
        "Substantiv svensk beskrivning om vad stiftelsen finansierar."
    )
    fake_session.commit.assert_called_once()
