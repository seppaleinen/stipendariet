"""
Tests for BolagsverketStage (pipeline integration).
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.base import PipelineContext
from app.pipeline.bolagsverket import (
    BolagsverketStage,
    _construct_probable_website,
    _slugify,
)

# =============================================================================
# Helper function tests
# =============================================================================


def test_slugify():
    """_slugify converts names to URL-friendly slugs."""
    assert _slugify("Stiftelsen Test") == "stiftelsen-test"
    assert _slugify("Älmhults Stiftelse") == "almhults-stiftelse"
    assert _slugify("Test@#$%Foundation") == "test-foundation"
    assert _slugify("  Leading and trailing  ") == "leading-and-trailing"
    assert _slugify("Örebro") == "orebro"


def test_construct_probable_website():
    """_construct_probable_website builds probable URL from legal name."""
    url = _construct_probable_website("Test Foundation AB")
    assert url == "https://test-foundation-ab.se"

    url = _construct_probable_website("Stiftelsen")
    assert url == "https://stiftelsen.se"

    # Empty/None inputs
    assert _construct_probable_website("") is None
    assert _construct_probable_website(None) is None


# =============================================================================
# Stage execution tests
# =============================================================================


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_success():
    """Stage sets bolagsverket_data and official_website on success."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
        "registration_date": "2020-01-15",
        "legal_form": "Aktiebolag",
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)  # Fast for tests
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    assert ctx.bolagsverket_data is not None
    assert ctx.bolagsverket_data["legal_name"] == "Test Foundation AB"
    assert ctx.official_website == "https://test-foundation-ab.se"
    assert ctx.trace["bolagsverket"]["found"] is True
    assert ctx.trace["bolagsverket"]["official_website"] == "https://test-foundation-ab.se"
    assert ctx.trace["bolagsverket"]["legal_name"] == "Test Foundation AB"
    assert ctx.trace["bolagsverket"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_no_orgnr():
    """Stage handles missing orgnr gracefully (no API call)."""
    stage = BolagsverketStage(rate_limit=100)
    ctx = PipelineContext(
        foundation_id=1,
        foundation_name="Test Foundation",
        foundation_orgnr=None,
    )

    await stage.run(ctx)

    assert ctx.bolagsverket_data is None
    assert ctx.official_website is None
    assert ctx.trace["bolagsverket"]["found"] is False
    assert ctx.trace["bolagsverket"]["reason"] == "no_orgnr"


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_not_found():
    """Stage handles Bolagsverket returning no data (404 or empty)."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = None

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="0000000000",
        )

        await stage.run(ctx)

    assert ctx.bolagsverket_data is None
    assert ctx.official_website is None
    assert ctx.trace["bolagsverket"]["found"] is False


@pytest.mark.asyncio
async def test_bolagsverket_stage_sets_trace():
    """Stage populates trace dict with all expected fields."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
        "registration_date": "2020-01-15",
        "legal_form": "Aktiebolag",
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    trace = ctx.trace["bolagsverket"]
    assert "orgnr" in trace
    assert "found" in trace
    assert "legal_name" in trace
    assert "status" in trace
    assert "official_website" in trace
    assert "address" in trace
    assert "registration_date" in trace
    assert "legal_form" in trace

    assert trace["orgnr"] == "5560747551"
    assert trace["found"] is True
    assert trace["legal_name"] == "Test Foundation AB"
    assert trace["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_bolagsverket_stage_skips_discovery_when_website_found():
    """
    Integration test: when official_website is set, orchestrator skips Discovery.

    This test verifies the stage sets the fields that orchestrator uses
    to make the skip decision.
    """
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    # Verify the fields that orchestrator uses to skip discovery
    assert ctx.official_website is not None
    assert ctx.official_website.startswith("https://")
    assert ctx.bolagsverket_data is not None


@pytest.mark.asyncio
async def test_bolagsverket_stage_injection_into_orchestrator():
    """BolagsverketStage is included in _get_default_stages()."""
    from app.pipeline.orchestrator import _get_default_stages

    stages = _get_default_stages()

    assert "bolagsverket" in stages
    assert isinstance(stages["bolagsverket"], BolagsverketStage)
    assert stages["bolagsverket"].name == "bolagsverket"
