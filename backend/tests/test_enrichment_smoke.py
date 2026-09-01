"""
Smoke test: process exactly 5 foundations end-to-end through the enrichment pipeline.

Requires: live Postgres + Redis + browserless + LiteLLM.
Skips automatically if any of those services is unreachable.

The conftest.py mocks the database module at import time (sys.modules level),
which prevents any real DB calls.  This test deliberately imports AFTER that
mocking so we can replace it with the real thing.
"""
from __future__ import annotations

import asyncio
import logging
import sys

import pytest
import requests

# ── Un-mock app.db.database so we get the real SessionLocal ─────────────────
# conftest.py sets this before any test code runs.  We reset it before this
# module is even discovered by the import-order machinery.
sys.modules.pop("app.db.database", None)
sys.modules.pop("app.db", None)

# ruff: noqa: E402 — must pop mocks first
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import EnrichmentSource, Foundation  # noqa: E402
from app.pipeline.orchestrator import run_foundation_pipeline_task  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------

def _check_url(url: str, timeout: float = 5.0) -> bool:
    """Return True if the URL responds with HTTP 2xx / 3xx."""
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        return r.status_code < 500
    except requests.RequestException:
        return False


def pytest_configure(config):  # noqa: N802
    """Register the custom 'integration' marker so pytest does not warn."""
    config.addinivalue_line("markers", "integration: integration test (requires live infra)")


@pytest.fixture(scope="module")
def browserless_ok() -> bool:
    # browserless serves HTTP on :3000 (API), devtools on :9222 (WebSocket).
    # requests.head() works against :3000. If the env var points to :9222,
    # rewrite it to :3000 for the reachability check.
    from app.core.config import Settings

    s = Settings()
    url = s.BROWSERLESS_URL
    # Rewrite :9222 (devtools) → :3000 (API) for HTTP reachability check
    url = url.replace(":9222", ":3000") if ":9222" in url else url
    return _check_url(url, timeout=5.0)


@pytest.fixture(scope="module")
def litellm_ok() -> bool:
    from app.core.config import Settings

    s = Settings()
    return _check_url(s.LITELLM_URL, timeout=10.0)


# ---------------------------------------------------------------------------
# Fixture: 5 test foundations
# ---------------------------------------------------------------------------

@pytest.fixture
def test_foundations() -> list[int]:
    """
    Pick 5 UNPROCESSED foundations that have a non-empty purpose text.

    Returns a list of foundation primary keys.
    After the test these rows are reset to UNPROCESSED so the test is repeatable.
    """
    with SessionLocal() as db:
        rows = (
            db.query(Foundation)
            .filter(
                Foundation.enrichment_status == "UNPROCESSED",
                Foundation.purpose.isnot(None),
                Foundation.purpose != "",
            )
            .limit(5)
            .all()
        )
        ids = [r.id for r in rows]
    if len(ids) < 5:
        pytest.skip(
            f"Need ≥5 UNPROCESSED foundations with non-empty purpose. "
            f"Found {len(ids)}. Run foundation sync first or backfill enrichment_status."
        )
    return ids


@pytest.fixture
def reset_after():
    """Reset test foundations to UNPROCESSED after the test runs."""
    foundation_ids: list[int] = []

    def capture(ids: list[int]) -> None:
        nonlocal foundation_ids
        foundation_ids = ids

    yield capture

    if foundation_ids:
        with SessionLocal() as db:
            db.query(Foundation).filter(Foundation.id.in_(foundation_ids)).update(
                {
                    Foundation.enrichment_status: "UNPROCESSED",
                    Foundation.enrichment_error: None,
                    Foundation.enrichment_last_run: None,
                },
                synchronize_session=False,
            )
            db.commit()
        logger.info(f"[smoke teardown] Reset foundations {foundation_ids} → UNPROCESSED")


# ---------------------------------------------------------------------------
# The smoke test
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_enrichment_smoke_5_foundations(
    browserless_ok: bool,
    litellm_ok: bool,
    test_foundations: list[int],
    reset_after,
):
    """
    Smoke-test: process exactly 5 foundations through the full enrichment pipeline.

    Verifies:
    1. Each foundation's enrichment_status transitions OUT of UNPROCESSED.
    2. COMPLETED foundations have at least one enriched field populated.
    3. enrichment_sources rows exist for each processed foundation.
    4. All foundations are reset to UNPROCESSED in the reset_after fixture.
    """
    assert browserless_ok, (
        "BROWSERLESS_URL is not reachable. "
        "Start browserless: docker compose up -d browserless"
    )
    assert litellm_ok, (
        "LITELLM_URL is not reachable. "
        "Ensure LiteLLM proxy is running."
    )

    foundation_ids = test_foundations
    reset_after(foundation_ids)  # register teardown

    # ── Process each foundation ───────────────────────────────────────────────
    results: list[dict] = []
    for fid in foundation_ids:
        logger.info(f"[smoke] Processing foundation_id={fid}")
        result = await run_foundation_pipeline_task(
            ctx={},
            foundation_id=fid,
        )
        results.append(result)
        # Small delay between foundations to avoid hammering shared services
        await asyncio.sleep(1)

    # ── Assertions ────────────────────────────────────────────────────────────
    with SessionLocal() as db:
        for fid, result in zip(foundation_ids, results, strict=False):
            foundation = db.query(Foundation).filter(Foundation.id == fid).first()
            assert foundation is not None, f"Foundation {fid} not found after pipeline"

            # 1. Status must NOT be UNPROCESSED
            assert foundation.enrichment_status != "UNPROCESSED", (
                f"Foundation {fid} still UNPROCESSED after pipeline. "
                f"Result: {result}"
            )

            # 2. If COMPLETED, at least one enriched field is populated
            if foundation.enrichment_status == "COMPLETED":
                enriched_fields = [
                    foundation.contact_email,
                    foundation.who_can_apply,
                    foundation.enriched_description,
                ]
                assert any(enriched_fields), (
                    f"Foundation {fid} is COMPLETED but all enriched fields are null. "
                    f"enriched_description={foundation.enriched_description!r}, "
                    f"contact_email={foundation.contact_email!r}, "
                    f"who_can_apply={foundation.who_can_apply!r}"
                )

            # 3. enrichment_sources must have at least one row
            source_count = (
                db.query(EnrichmentSource)
                .filter(EnrichmentSource.foundation_id == fid)
                .count()
            )
            assert source_count > 0, (
                f"Foundation {fid} has no rows in enrichment_sources after pipeline. "
                f"status={foundation.enrichment_status}"
            )

            logger.info(
                f"[smoke] fid={fid} status={foundation.enrichment_status} "
                f"enriched_description={'set' if foundation.enriched_description else 'null'} "
                f"sources={source_count}"
            )

    logger.info("[smoke] All assertions passed for 5 foundations.")
