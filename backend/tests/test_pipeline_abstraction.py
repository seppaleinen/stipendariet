"""
Tests for the Phase 9 Pipeline Service Abstraction.

Covers:
- _get_default_stages() returns the five expected stage instances
- Every stage class satisfies the PipelineStage interface
- run_foundation_pipeline_task accepts an injected `stages` kwarg and
  falls back to _get_default_stages() when none is provided
- Each stage class delegates to its module-level function
"""
import asyncio
from unittest.mock import patch

import pytest

from app.pipeline.base import PipelineContext, PipelineStage
from app.pipeline.crawler import CrawlStage
from app.pipeline.discovery import DiscoveryStage
from app.pipeline.extraction import ExtractedFoundationData, ExtractionStage
from app.pipeline.orchestrator import _get_default_stages, run_foundation_pipeline_task
from app.pipeline.service_area import ServiceAreaStage
from app.pipeline.validation import UrlValidationStage

STAGE_KEYS = ["service_area", "discovery", "validation", "crawl", "extraction"]


def _make_ctx(**overrides) -> PipelineContext:
    defaults = dict(foundation_id=1, foundation_name="Test Foundation", foundation_orgnr="123456")
    defaults.update(overrides)
    return PipelineContext(**defaults)


# =============================================================================
# Default stages wiring
# =============================================================================


def test_get_default_stages_returns_five_keys_with_matching_names():
    stages = _get_default_stages()

    assert set(stages.keys()) == set(STAGE_KEYS)
    assert len(stages) == 5
    for key, stage in stages.items():
        assert stage.name == key


# =============================================================================
# Interface compliance
# =============================================================================


@pytest.mark.parametrize(
    ("stage_cls", "expected_name"),
    [
        (ServiceAreaStage, "service_area"),
        (DiscoveryStage, "discovery"),
        (UrlValidationStage, "validation"),
        (CrawlStage, "crawl"),
        (ExtractionStage, "extraction"),
    ],
)
def test_stage_classes_instantiate_as_pipeline_stage(stage_cls, expected_name):
    stage = stage_cls()
    assert isinstance(stage, PipelineStage)
    assert stage.name == expected_name
    assert asyncio.iscoroutinefunction(stage.run)


# =============================================================================
# Stages injection into the orchestrator
# =============================================================================


def _make_stub_stages() -> dict:
    """Build the minimal stub stages (real PipelineStage subclasses) that drive
    the pipeline to a full success without touching the real module functions."""

    class StubStage(PipelineStage):
        name = "stub"

        def __init__(self, run_fn):
            self._run_fn = run_fn

        async def run(self, ctx: PipelineContext) -> None:
            await self._run_fn(ctx)

    async def run_service_area(ctx: PipelineContext) -> None:
        pass  # parsed_service_area stays None

    async def run_discovery(ctx: PipelineContext) -> None:
        ctx.candidate_urls = [{"url": "https://a.se", "title": "A", "snippet": "s"}]

    async def run_validation(ctx: PipelineContext) -> None:
        ctx.validated_sources = [
            {**cand, "is_match": True, "confidence": 1.0, "raw_llm_response": None}
            for cand in ctx.candidate_urls
        ]

    async def run_crawl(ctx: PipelineContext) -> None:
        ctx.crawled_pages = [{"url": ctx.active_source["url"], "content": "page text", "type": "homepage"}]

    async def run_extraction(ctx: PipelineContext) -> None:
        ctx.extracted_data = {"contact_email": "test@foundation.se"}

    return {
        "service_area": StubStage(run_service_area),
        "discovery": StubStage(run_discovery),
        "validation": StubStage(run_validation),
        "crawl": StubStage(run_crawl),
        "extraction": StubStage(run_extraction),
    }


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
@patch("app.pipeline.extraction.extract_data_from_content")
@patch("app.pipeline.crawler.crawl_foundation_site")
@patch("app.pipeline.validation.validate_candidate_url")
@patch("app.pipeline.discovery.discover_candidate_urls")
async def test_run_pipeline_uses_injected_stages(
    mock_discover, mock_validate, mock_crawl, mock_extract, mock_service_area
):
    """Injected stub stages drive the pipeline; real stage implementations are bypassed."""
    stages = _make_stub_stages()

    result = await run_foundation_pipeline_task({}, foundation_id=1, stages=stages)

    assert result["status"] == "success"
    assert result["data"] == {"contact_email": "test@foundation.se"}

    # Real module-level functions must never have been invoked
    for mock in (mock_discover, mock_validate, mock_crawl, mock_extract, mock_service_area):
        mock.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.pipeline.orchestrator._get_default_stages")
async def test_run_pipeline_falls_back_to_default_stages_when_omitted(mock_default_stages):
    """When the stages kwarg is omitted, _get_default_stages() is used."""
    mock_default_stages.return_value = _make_stub_stages()

    result = await run_foundation_pipeline_task({}, foundation_id=1)

    mock_default_stages.assert_called_once()
    assert result["status"] == "success"


# =============================================================================
# Stage → module function delegation
# =============================================================================


@pytest.mark.asyncio
@patch("app.pipeline.discovery.discover_candidate_urls")
async def test_discovery_stage_delegates_to_discover_candidate_urls(mock_discover):
    mock_discover.return_value = [{"url": "https://x.se", "title": "X", "snippet": "s"}]
    ctx = _make_ctx()

    await DiscoveryStage().run(ctx)

    mock_discover.assert_awaited_once_with("Test Foundation", "123456")
    assert ctx.candidate_urls == [{"url": "https://x.se", "title": "X", "snippet": "s"}]


@pytest.mark.asyncio
@patch("app.pipeline.validation.validate_candidate_url")
async def test_validation_stage_delegates_to_validate_candidate_url(mock_validate):
    candidate = {"url": "https://x.se", "title": "X", "snippet": "s"}
    mock_validate.return_value = {"is_match": True, "confidence": 0.9, "raw_llm_response": "raw"}
    ctx = _make_ctx(candidate_urls=[candidate])

    await UrlValidationStage().run(ctx)

    mock_validate.assert_awaited_once_with(
        candidate,
        "Test Foundation",
        "123456",
        custom_system_prompt=None,
        custom_user_prompt=None,
    )
    assert ctx.validated_sources == [{**candidate, "is_match": True, "confidence": 0.9, "raw_llm_response": "raw"}]


@pytest.mark.asyncio
@patch("app.pipeline.crawler.crawl_foundation_site")
async def test_crawl_stage_delegates_to_crawl_foundation_site(mock_crawl):
    pages = [{"url": "https://x.se", "content": "text", "type": "homepage"}]
    mock_crawl.return_value = pages
    ctx = _make_ctx(active_source={"url": "https://x.se"})

    await CrawlStage().run(ctx)

    mock_crawl.assert_awaited_once_with("https://x.se")
    assert ctx.crawled_pages == pages


@pytest.mark.asyncio
@patch("app.pipeline.crawler.crawl_foundation_site")
async def test_crawl_stage_noop_without_active_source(mock_crawl):
    ctx = _make_ctx()

    await CrawlStage().run(ctx)

    mock_crawl.assert_not_awaited()
    assert ctx.crawled_pages == []


@pytest.mark.asyncio
@patch("app.pipeline.extraction.extract_data_from_content")
async def test_extraction_stage_delegates_to_extract_data_from_content(mock_extract):
    extracted = ExtractedFoundationData(contact_email="a@b.se")
    mock_extract.return_value = extracted
    ctx = _make_ctx(
        crawled_pages=[
            {"url": "https://x.se/home", "content": "home text", "type": "homepage"},
            {"url": "https://x.se/ansokan", "content": "subpage text", "type": "subpage"},
        ]
    )

    await ExtractionStage().run(ctx)

    (combined, foundation_name), kwargs = mock_extract.await_args
    assert foundation_name == "Test Foundation"
    assert kwargs == {"custom_system_prompt": None, "custom_user_prompt": None}
    # Subpages are prioritised in the combined content
    assert "subpage text" in combined and "home text" in combined
    assert combined.index("subpage text") < combined.index("home text")
    assert ctx.extracted_data == extracted.model_dump()


@pytest.mark.asyncio
@patch("app.pipeline.extraction.extract_data_from_content")
async def test_extraction_stage_noop_without_crawled_pages(mock_extract):
    ctx = _make_ctx()

    await ExtractionStage().run(ctx)

    mock_extract.assert_not_awaited()
    assert ctx.extracted_data is None


@pytest.mark.asyncio
@patch("app.pipeline.service_area.extract_service_area")
async def test_service_area_stage_delegates_to_extract_service_area(mock_extract_area):
    service_area = {
        "municipality_code": "0130000",
        "county_code": "0130",
        "municipality_name": "Uppsala",
        "county_name": "Uppsala län",
        "source_text": "Uppsala",
        "confidence": "high",
        "service_area_detail": None,
        "service_area_status": "CONFIRMED",
    }
    mock_extract_area.return_value = service_area
    ctx = _make_ctx(purpose="Uppsala stiftelse", registered_county_code="0130")

    await ServiceAreaStage().run(ctx)

    mock_extract_area.assert_awaited_once_with(
        "Test Foundation",
        purpose="Uppsala stiftelse",
        description=None,
        registered_county_code="0130",
        registered_municipality_code=None,
    )
    # Status is popped from the dict and stored on the context separately
    assert ctx.service_area_status == "CONFIRMED"
    assert "service_area_status" not in ctx.parsed_service_area
    assert ctx.parsed_service_area == {
        "municipality_code": "0130000",
        "county_code": "0130",
        "municipality_name": "Uppsala",
        "county_name": "Uppsala län",
        "source_text": "Uppsala",
        "confidence": "high",
        "service_area_detail": None,
    }
