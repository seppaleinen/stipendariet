"""
Smoke test: process exactly 5 foundations end-to-end through the enrichment pipeline.

Requires: live Postgres + Redis + browserless + LiteLLM.
Skips automatically if any of those services is unreachable.

IMPORTANT (CI unit tests): conftest.py mocks `app.db.database` at the sys.modules
level so every other test runs as a pure unit test with no real DB.  That mock
must NOT be replaced at module-import time — doing so (as this file historically
did with a module-level `sys.modules.pop`) silently breaks the dependency-mock
setup of test_routers.py / test_issue19_urls.py whenever this file is collected
in the same run (which is exactly what happens in CI).

So this module does NOT touch sys.modules at import time.  The real database
module is imported lazily, only after a runtime check confirms a real, migrated
`foundations` table is reachable.  If it isn't (CI unit runs, empty Postgres, or
no DB), the test skips.  The conftest mock is restored afterwards so sibling
unit tests are never affected.
"""
from __future__ import annotations

import asyncio
import logging

import pytest
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy, self-healing access to the real database module
# ---------------------------------------------------------------------------

def _load_real_db():
    """Temporarily swap the conftest sys.modules mock for the REAL database module.

    Returns (SessionLocal, Foundation, EnrichmentSource, run_foundation_pipeline_task)
    after importing the real modules, and restores the conftest mock so sibling
    unit tests keep their mocked DB.

    Callers must hold this in a try/finally so the mock is always restored.
    """
    import sys

    # conftest installs a MagicMock for app.db.database.  Snapshot it so we can
    # restore it after importing the real module.
    mock_db = sys.modules.get("app.db.database")

    sys.modules.pop("app.db.database", None)
    sys.modules.pop("app.db", None)

    try:
        from app.db.database import SessionLocal
        from app.db.models import EnrichmentSource, Foundation
        from app.pipeline.orchestrator import run_foundation_pipeline_task
        return SessionLocal, Foundation, EnrichmentSource, run_foundation_pipeline_task
    finally:
        # Drop any cached real module, then restore the conftest mock so we
        # never pollute sibling unit tests.
        sys.modules.pop("app.db.database", None)
        sys.modules.pop("app.db", None)
        if mock_db is not None:
            sys.modules["app.db.database"] = mock_db


def _real_db_ready() -> bool:
    """Return True iff a real `foundations` table is reachable for this test.

    Uses the same retry-based engine creation the app uses; returns False (-> skip)
    for any unreachable DB / missing table / missing columns (CI unit runs).
    """
    try:
        SessionLocal, Foundation, _, _ = _load_real_db()
        with SessionLocal() as db:
            # Select a full row (all mapped columns) so a missing column in a
            # partially-migrated DB also triggers a skip rather than an error.
            db.query(Foundation).limit(1).first()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def real_db_ready() -> bool:
    """Skip the whole module if no real, migrated Postgres `foundations` table."""
    if not _real_db_ready():
        pytest.skip(
            "No real Postgres `foundations` table reachable. "
            "This is an integration test and is skipped in CI unit runs."
        )
    return True

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
# Fixture: lazily load real DB modules once a real DB is confirmed
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def enrichment_db(real_db_ready):
    """Load the real database modules and hold them for this module's tests.

    `real_db_ready` guarantees a real `foundations` table exists (otherwise the
    module skips).  Imports are done lazily here so the conftest sys.modules
    mock is only swapped out for the short duration of this module's run.
    """
    loaded = _load_real_db()
    yield {
        "SessionLocal": loaded[0],
        "Foundation": loaded[1],
        "EnrichmentSource": loaded[2],
        "run_foundation_pipeline_task": loaded[3],
    }


# ---------------------------------------------------------------------------
# Fixture: 5 test foundations
# ---------------------------------------------------------------------------

@pytest.fixture
def test_foundations(enrichment_db) -> list[int]:
    """
    Pick 5 UNPROCESSED foundations that have a non-empty purpose text.

    Returns a list of foundation primary keys.
    After the test these rows are reset to UNPROCESSED so the test is repeatable.
    """
    SessionLocal = enrichment_db["SessionLocal"]
    Foundation = enrichment_db["Foundation"]
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
def reset_after(enrichment_db):
    """Reset test foundations to UNPROCESSED after the test runs."""
    SessionLocal = enrichment_db["SessionLocal"]
    Foundation = enrichment_db["Foundation"]
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
    enrichment_db,
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

    SessionLocal = enrichment_db["SessionLocal"]
    Foundation = enrichment_db["Foundation"]
    EnrichmentSource = enrichment_db["EnrichmentSource"]
    run_foundation_pipeline_task = enrichment_db["run_foundation_pipeline_task"]

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
