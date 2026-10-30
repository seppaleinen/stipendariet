"""
Sanity tests for Phase 4 — per-source extraction with confidence scoring.

Covers:
- _parse_extraction_response: flat vs nested JSON detection
- extract_from_source: URL tracking via source_per_field
- merge_extractions: highest-confidence-wins per field
"""
from unittest.mock import patch

import pytest

from app.pipeline.extraction import (
    ExtractedFoundationData,
    extract_data_from_content,
    extract_from_source,
    merge_extractions,
)


# =============================================================================
# Format detection
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_flat_format_backward_compat(mock_chat):
    """Flat JSON (legacy) parses without confidence scores."""
    mock_chat.return_value = '{"contact_email": "a@b.se", "application_deadline": "31 mars"}'

    res = await extract_data_from_content("content", "Test Foundation")

    assert res is not None
    assert res.contact_email == "a@b.se"
    assert res.application_deadline == "31 mars"
    assert res.confidence == 0.0  # flat format → no confidence
    assert res.per_field_confidence == {}
    assert res.source_per_field == {}


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_nested_format_parses_confidence(mock_chat):
    """Nested JSON (new) populates per-field and overall confidence."""
    mock_chat.return_value = (
        '{"contact_email": {"value": "a@b.se", "confidence": 0.9},'
        ' "application_deadline": {"value": "31 mars", "confidence": 0.8},'
        ' "contact_phone": {"value": null, "confidence": 0.0}}'
    )

    res = await extract_data_from_content("content", "Test Foundation")

    assert res is not None
    assert res.contact_email == "a@b.se"
    assert res.application_deadline == "31 mars"
    assert res.contact_phone is None
    # average of non-null field confidences: (0.9 + 0.8) / 2 = 0.85
    assert abs(res.confidence - 0.85) < 1e-9
    assert res.per_field_confidence == {"contact_email": 0.9, "application_deadline": 0.8}


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_nested_format_invalid_confidence_clamped(mock_chat):
    """Out-of-range or non-numeric confidence is clamped to 0.0."""
    mock_chat.return_value = (
        '{"contact_email": {"value": "a@b.se", "confidence": "high"},'
        ' "notes": {"value": "x", "confidence": 5.0}}'
    )

    res = await extract_data_from_content("content", "Test Foundation")

    assert res is not None
    assert res.per_field_confidence == {"contact_email": 0.0, "notes": 0.0}
    assert res.confidence == 0.0


# =============================================================================
# extract_from_source
# =============================================================================


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extract_from_source_tracks_source_url(mock_chat):
    """extract_from_source stamps source_per_field with the source URL."""
    mock_chat.return_value = '{"contact_email": {"value": "a@b.se", "confidence": 0.9}}'

    res = await extract_from_source("content", "https://example.se", "Test Foundation")

    assert res is not None
    assert res.contact_email == "a@b.se"
    assert res.source_per_field == {"contact_email": "https://example.se"}
    assert res.confidence == 0.9


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extract_from_source_passes_url_in_prompt(mock_chat):
    """The URL is included in the prompt sent to the LLM."""
    mock_chat.return_value = '{"notes": {"value": "x", "confidence": 0.5}}'

    await extract_from_source("content", "https://example.se", "Test Foundation")

    (prompt,) = mock_chat.call_args.args
    assert "https://example.se" in prompt


@pytest.mark.asyncio
@patch('app.pipeline.extraction.chat_completion')
async def test_extract_from_source_truncates_long_content(mock_chat):
    """Content beyond 6000 chars is truncated (cost/size control)."""
    mock_chat.return_value = '{"notes": {"value": "truncated", "confidence": 0.5}}'
    long_content = "z" * 7000  # 'z' does not appear in the Swedish system/user prompt

    await extract_from_source(long_content, "https://example.se", "Test Foundation")

    (prompt,) = mock_chat.call_args.args
    # 6000 chars of z + "..."
    assert prompt.count("z") == 6000
    assert "..." in prompt


# =============================================================================
# merge_extractions
# =============================================================================


def test_merge_picks_highest_confidence_per_field():
    """Per field, the value with the highest confidence wins."""
    own_site = ExtractedFoundationData(
        contact_email="own@site.se",
        application_deadline="31 mars",
        per_field_confidence={"contact_email": 0.7, "application_deadline": 0.8},
        confidence=0.75,
        source_per_field={"contact_email": "https://own.se", "application_deadline": "https://own.se"},
    )
    aggregator = ExtractedFoundationData(
        contact_email="agg@stiftelse.se",
        application_deadline="1 april",
        per_field_confidence={"contact_email": 0.95, "application_deadline": 0.5},
        confidence=0.725,
        source_per_field={"contact_email": "https://stiftelsemedel.se", "application_deadline": "https://stiftelsemedel.se"},
    )

    merged = merge_extractions([
        (own_site, "https://own.se"),
        (aggregator, "https://stiftelsemedel.se"),
    ])

    # Aggregator's email has higher confidence → wins
    assert merged.contact_email == "agg@stiftelse.se"
    assert merged.source_per_field["contact_email"] == "https://stiftelsemedel.se"
    assert merged.per_field_confidence["contact_email"] == 0.95

    # Own-site's deadline has higher confidence → wins
    assert merged.application_deadline == "31 mars"
    assert merged.source_per_field["application_deadline"] == "https://own.se"
    assert merged.per_field_confidence["application_deadline"] == 0.8

    # Overall confidence = average of winning per-field confidences
    assert merged.confidence == (0.95 + 0.8) / 2


def test_merge_ignores_null_fields():
    """Fields that are null in every extraction stay null in the merge."""
    e1 = ExtractedFoundationData(
        contact_email="a@b.se",
        per_field_confidence={"contact_email": 0.9},
        confidence=0.9,
    )
    e2 = ExtractedFoundationData(
        contact_phone=None,  # null — must not appear in per_field_confidence
        per_field_confidence={},  # null fields should not be in per_field_confidence
        confidence=0.0,
    )

    merged = merge_extractions([
        (e1, "https://s1.se"),
        (e2, "https://s2.se"),
    ])

    assert merged.contact_email == "a@b.se"
    assert merged.contact_phone is None
    assert "contact_phone" not in merged.per_field_confidence
    assert "contact_phone" not in merged.source_per_field
    assert merged.confidence == 0.9  # only email field counted


def test_merge_empty_list_returns_empty():
    """An empty extraction list yields an empty (all-null) result."""
    merged = merge_extractions([])
    assert merged.confidence == 0.0
    assert merged.per_field_confidence == {}
    assert merged.contact_email is None


def test_merge_flat_format_extractions_uses_zero_confidence():
    """Extractions from the legacy flat format (confidence 0.0) still merge —
    first non-null value wins since all confidences tie at 0.0."""
    e1 = ExtractedFoundationData(contact_email="first@se.se", confidence=0.0)
    e2 = ExtractedFoundationData(contact_email="second@se.se", confidence=0.0)

    merged = merge_extractions([
        (e1, "https://s1.se"),
        (e2, "https://s2.se"),
    ])

    # Tie at 0.0 → first extraction wins (stable)
    assert merged.contact_email == "first@se.se"
    assert merged.source_per_field["contact_email"] == "https://s1.se"


def test_merge_skips_fields_not_in_content_schema():
    """Metadata fields (confidence, per_field_confidence, source_per_field) are
    never merged as content fields."""
    e1 = ExtractedFoundationData(
        notes="hello",
        confidence=0.5,
        per_field_confidence={"notes": 0.5},
        source_per_field={"notes": "https://s1.se"},
    )

    merged = merge_extractions([(e1, "https://s1.se")])

    assert merged.notes == "hello"
    assert set(merged.per_field_confidence.keys()) == {"notes"}
    assert set(merged.source_per_field.keys()) == {"notes"}
