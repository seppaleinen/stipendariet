"""
Tests for Phase 6 — Targeted Re-Search for Missing Fields.

Covers:
- generate_targeted_query: Swedish query templates per field
- merge_missing_only: fills only None fields, never overwrites
- Gap analysis in orchestrator (integration test with mocked stages)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.discovery import REQUIRED_FIELDS, generate_targeted_query
from app.pipeline.extraction import ExtractedFoundationData, merge_missing_only


# =============================================================================
# generate_targeted_query
# =============================================================================


def test_generate_targeted_query_contact_email():
    """Contact email → Swedish 'kontakt e-post' query."""
    query = generate_targeted_query("contact_email", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" kontakt e-post'


def test_generate_targeted_query_contact_phone():
    """Contact phone → Swedish 'telefon kontakt' query."""
    query = generate_targeted_query("contact_phone", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" telefon kontakt'


def test_generate_targeted_query_application_open():
    """Application open → Swedish 'ansökan öppnar' query."""
    query = generate_targeted_query("application_open", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" ansökan öppnar'


def test_generate_targeted_query_application_deadline():
    """Application deadline → Swedish 'sista ansökningsdag' query."""
    query = generate_targeted_query("application_deadline", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" sista ansökningsdag'


def test_generate_targeted_query_who_can_apply():
    """Who can apply → Swedish 'vem kan söka' query."""
    query = generate_targeted_query("who_can_apply", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" vem kan söka'


def test_generate_targeted_query_how_to_apply():
    """How to apply → Swedish 'hur ansöker' query."""
    query = generate_targeted_query("how_to_apply", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" hur ansöker'


def test_generate_targeted_query_notes():
    """Notes → Swedish 'bidrag information' query."""
    query = generate_targeted_query("notes", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" bidrag information'


def test_generate_targeted_query_enriched_description():
    """Enriched description → Swedish 'stiftelse ändamål' query."""
    query = generate_targeted_query("enriched_description", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" stiftelse ändamål'


def test_generate_targeted_query_unknown_field():
    """Unknown field → fallback query with field name."""
    query = generate_targeted_query("unknown_field", "Test Stiftelsen")
    assert query == '"Test Stiftelsen" unknown_field'


# =============================================================================
# merge_missing_only
# =============================================================================


def test_merge_missing_only_fills_none_fields():
    """Fields that are None on current get filled from new extractions."""
    current = ExtractedFoundationData(
        contact_email="existing@example.se",
        contact_phone=None,
        application_deadline=None,
        per_field_confidence={"contact_email": 0.9},
        source_per_field={"contact_email": "https://existing.se"},
        confidence=0.9,
    )

    new_extraction = ExtractedFoundationData(
        contact_phone="08-123456",
        application_deadline="31 mars",
        contact_email="should_not_overwrite@example.se",  # Should NOT overwrite
        per_field_confidence={
            "contact_phone": 0.85,
            "application_deadline": 0.8,
            "contact_email": 0.95,
        },
        source_per_field={
            "contact_phone": "https://new.se",
            "application_deadline": "https://new.se",
            "contact_email": "https://new.se",
        },
        confidence=0.85,
    )

    merged = merge_missing_only(
        current,
        [(new_extraction, "https://new.se")],
        target_fields=["contact_phone", "application_deadline", "contact_email"],
    )

    # Existing fields preserved
    assert merged.contact_email == "existing@example.se"
    assert merged.source_per_field["contact_email"] == "https://existing.se"

    # Missing fields filled
    assert merged.contact_phone == "08-123456"
    assert merged.source_per_field["contact_phone"] == "https://new.se"
    assert merged.per_field_confidence["contact_phone"] == 0.85

    assert merged.application_deadline == "31 mars"
    assert merged.source_per_field["application_deadline"] == "https://new.se"
    assert merged.per_field_confidence["application_deadline"] == 0.8


def test_merge_missing_only_multiple_extractions_picks_best():
    """When multiple new extractions provide the same missing field, highest confidence wins."""
    current = ExtractedFoundationData(
        contact_email=None,
        contact_phone=None,
    )

    ext1 = ExtractedFoundationData(
        contact_email="low@conf.se",
        contact_phone="555-111",
        per_field_confidence={"contact_email": 0.5, "contact_phone": 0.6},
        source_per_field={"contact_email": "https://s1.se", "contact_phone": "https://s1.se"},
    )

    ext2 = ExtractedFoundationData(
        contact_email="high@conf.se",
        contact_phone="555-222",
        per_field_confidence={"contact_email": 0.9, "contact_phone": 0.4},
        source_per_field={"contact_email": "https://s2.se", "contact_phone": "https://s2.se"},
    )

    merged = merge_missing_only(
        current,
        [(ext1, "https://s1.se"), (ext2, "https://s2.se")],
        target_fields=["contact_email", "contact_phone"],
    )

    # Email: ext2 has higher confidence → wins
    assert merged.contact_email == "high@conf.se"
    assert merged.source_per_field["contact_email"] == "https://s2.se"
    assert merged.per_field_confidence["contact_email"] == 0.9

    # Phone: ext1 has higher confidence → wins
    assert merged.contact_phone == "555-111"
    assert merged.source_per_field["contact_phone"] == "https://s1.se"
    assert merged.per_field_confidence["contact_phone"] == 0.6


def test_merge_missing_only_no_new_extractions_returns_current():
    """Empty new extractions list returns current unchanged."""
    current = ExtractedFoundationData(
        contact_email="test@example.se",
        confidence=0.9,
    )

    merged = merge_missing_only(current, [], target_fields=["contact_phone"])

    assert merged.contact_email == "test@example.se"
    assert merged.confidence == 0.9
    assert merged is not current  # Should be a copy, not same object


def test_merge_missing_only_no_missing_fields_returns_current():
    """When all target fields already have values, returns current unchanged."""
    current = ExtractedFoundationData(
        contact_email="existing@example.se",
        contact_phone="08-123456",
        per_field_confidence={"contact_email": 0.9, "contact_phone": 0.8},
        confidence=0.85,
    )

    new = ExtractedFoundationData(
        contact_email="new@example.se",
        contact_phone="555-000",
        per_field_confidence={"contact_email": 0.95, "contact_phone": 0.95},
    )

    merged = merge_missing_only(
        current,
        [(new, "https://new.se")],
        target_fields=["contact_email", "contact_phone"],
    )

    # Nothing filled — all fields already had values
    assert merged.contact_email == "existing@example.se"
    assert merged.contact_phone == "08-123456"
    assert merged.per_field_confidence == {"contact_email": 0.9, "contact_phone": 0.8}


def test_merge_missing_only_respects_target_fields():
    """Only fields in target_fields are considered for filling."""
    current = ExtractedFoundationData(
        contact_email=None,
        contact_phone=None,
        notes=None,
    )

    new = ExtractedFoundationData(
        contact_email="email@example.se",
        contact_phone="555-1234",
        notes="some notes",
        per_field_confidence={
            "contact_email": 0.9,
            "contact_phone": 0.8,
            "notes": 0.7,
        },
    )

    # Only target contact_email and contact_phone — notes should NOT be filled
    merged = merge_missing_only(
        current,
        [(new, "https://new.se")],
        target_fields=["contact_email", "contact_phone"],
    )

    assert merged.contact_email == "email@example.se"
    assert merged.contact_phone == "555-1234"
    assert merged.notes is None  # Not in target_fields


# =============================================================================
# Integration test: gap analysis + re-search loop (orchestrator)
# =============================================================================


@pytest.mark.asyncio
async def test_orchestrator_gap_analysis_identifies_missing_fields():
    """
    Gap analysis correctly identifies which REQUIRED_FIELDS are missing
    after the initial merge.
    """
    from app.pipeline.base import PipelineContext

    # Simulate a merged extraction with only 3 of 8 fields
    merged = ExtractedFoundationData(
        contact_email="test@example.se",
        application_deadline="31 mars",
        who_can_apply="Students",
        per_field_confidence={
            "contact_email": 0.9,
            "application_deadline": 0.8,
            "who_can_apply": 0.7,
        },
        confidence=0.8,
    )

    # Gap analysis (as done in orchestrator)
    missing = [f for f in REQUIRED_FIELDS if not getattr(merged, f, None)]

    assert len(missing) == 5
    assert "contact_phone" in missing
    assert "application_open" in missing
    assert "how_to_apply" in missing
    assert "notes" in missing
    assert "enriched_description" in missing


@pytest.mark.asyncio
@patch('app.pipeline.orchestrator._db_save_extraction')
@patch('app.pipeline.orchestrator._db_update_foundation_status')
async def test_orchestrator_re_search_loop_max_iterations(
    mock_db_update,
    mock_db_save,
):
    """
    Re-search loop runs at most MAX_RESEARCH_ITERATIONS times.
    """
    from app.pipeline.orchestrator import (
        MAX_RESEARCH_ITERATIONS,
        run_foundation_pipeline_task,
    )

    # Mock foundation
    mock_foundation = MagicMock()
    mock_foundation.name = "Test Foundation"
    mock_foundation.orgnr = "123456-7890"
    mock_foundation.purpose = "Test purpose"
    mock_foundation.summary = "Test summary"
    mock_foundation.county_code = None
    mock_foundation.municipality_code = None

    # Mock stages that populate PipelineContext
    async def mock_discovery_run(ctx):
        ctx.candidate_urls = [{"url": "https://test.se", "title": "Test", "snippet": "..."}]

    async def mock_validation_run(ctx):
        ctx.validated_sources = [
            {
                "url": "https://test.se",
                "is_match": True,
                "confidence": 0.9,
                "source_id": 1,
            }
        ]

    async def mock_crawl_run(ctx):
        ctx.crawled_pages = [
            {"url": "https://test.se", "type": "page", "markdown": "Test content"}
        ]

    async def mock_extraction_run(ctx):
        ctx.extracted_data = {
            "contact_email": "test@example.se",
            "confidence": 0.9,
            "per_field_confidence": {"contact_email": 0.9},
        }

    mock_stage = AsyncMock()
    mock_stage.run = AsyncMock()

    with patch('app.pipeline.orchestrator._db_fetch_foundation', return_value=mock_foundation):
        with patch('app.pipeline.orchestrator._get_default_stages', return_value={
            "bolagsverket": mock_stage,
            "service_area": mock_stage,
            "discovery": type("MockStage", (), {"run": staticmethod(mock_discovery_run)})(),
            "validation": type("MockStage", (), {"run": staticmethod(mock_validation_run)})(),
            "crawl": type("MockStage", (), {"run": staticmethod(mock_crawl_run)})(),
            "extraction": type("MockStage", (), {"run": staticmethod(mock_extraction_run)})(),
        }):
            # Mock merge_extractions to return partial data (missing fields)
            with patch('app.pipeline.orchestrator.merge_extractions') as mock_merge:
                mock_merge.return_value = ExtractedFoundationData(
                    contact_email="test@example.se",
                    confidence=0.9,
                )

                # Mock merge_missing_only to keep returning partial data
                # (so loop continues until max iterations)
                with patch('app.pipeline.orchestrator.merge_missing_only') as mock_merge_missing:
                    mock_merge_missing.side_effect = lambda current, new, target_fields: (
                        ExtractedFoundationData(
                            contact_email="test@example.se",
                            confidence=0.9,
                        )
                    )

                    # Mock _searxng_search to return candidates
                    with patch('app.pipeline.orchestrator._searxng_search') as mock_searxng:
                        mock_searxng.return_value = [
                            {"url": "https://targeted.se", "title": "Test", "snippet": "..."}
                        ]

                        # Mock validate_candidate_url
                        with patch('app.pipeline.orchestrator.validate_candidate_url') as mock_validate:
                            mock_validate.return_value = {
                                "is_match": True,
                                "confidence": 0.8,
                            }

                            # Run pipeline
                            result = await run_foundation_pipeline_task(
                                {},
                                foundation_id=1,
                            )

                            # Verify re-search ran max iterations
                            # (merge_missing_only called once per iteration after initial merge)
                            assert mock_merge_missing.call_count == MAX_RESEARCH_ITERATIONS


@pytest.mark.asyncio
async def test_required_fields_list_complete():
    """REQUIRED_FIELDS contains all 8 content fields from the research brief."""
    assert len(REQUIRED_FIELDS) == 8
    assert set(REQUIRED_FIELDS) == {
        "contact_email",
        "contact_phone",
        "application_open",
        "application_deadline",
        "who_can_apply",
        "how_to_apply",
        "notes",
        "enriched_description",
    }
