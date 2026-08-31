"""
Tests for the arq worker config and on_startup reset logic.
"""
from unittest.mock import MagicMock, patch

import pytest
from arq.connections import RedisSettings


def test_parse_redis_url_standard():
    """Parses host, port, password, and database from a full Redis URL."""
    from app.workers.enrichment_worker import parse_redis_url

    settings = parse_redis_url("redis://:secret@redis-host:6380/3")
    assert settings.host == "redis-host"
    assert settings.port == 6380
    assert settings.password == "secret"
    assert settings.database == 3


def test_parse_redis_url_defaults():
    """Uses default port 6379 and database 0 when omitted."""
    from app.workers.enrichment_worker import parse_redis_url

    settings = parse_redis_url("redis://localhost")
    assert settings.host == "localhost"
    assert settings.port == 6379
    assert settings.password is None
    assert settings.database == 0


def test_worker_settings_config():
    """WorkerSettings has expected configuration values."""
    from app.pipeline.orchestrator import run_foundation_pipeline_task
    from app.workers.enrichment_worker import WorkerSettings

    assert run_foundation_pipeline_task in WorkerSettings.functions
    assert len(WorkerSettings.functions) == 1
    assert WorkerSettings.max_tries == 3
    assert WorkerSettings.retry_delay == 60
    assert WorkerSettings.job_timeout == 300
    assert WorkerSettings.max_jobs == 5


@pytest.mark.asyncio
@patch('app.db.database.SessionLocal')
async def test_on_startup_resets_stalled_foundations(mock_session_local):
    """Resets stuck PROCESSING foundations to UNPROCESSED with error message."""
    mock_db = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_db
    mock_session_local.return_value.__exit__.return_value = False

    f1 = MagicMock()
    f2 = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [f1, f2]

    from app.workers.enrichment_worker import WorkerSettings

    await WorkerSettings.on_startup({})

    assert f1.enrichment_status == "UNPROCESSED"
    assert f1.enrichment_error == "Reset by worker startup: previous run stalled"
    assert f2.enrichment_status == "UNPROCESSED"
    assert f2.enrichment_error == "Reset by worker startup: previous run stalled"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
@patch('app.db.database.SessionLocal')
async def test_on_startup_no_stuck_foundations(mock_session_local):
    """Does not commit when no stuck foundations are found."""
    mock_db = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_db
    mock_session_local.return_value.__exit__.return_value = False

    mock_db.query.return_value.filter.return_value.all.return_value = []

    from app.workers.enrichment_worker import WorkerSettings

    await WorkerSettings.on_startup({})

    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
@patch('app.db.database.SessionLocal')
async def test_on_startup_handles_db_error_gracefully(mock_session_local):
    """on_startup wraps the entire body in try/except — never raises."""
    mock_session_local.return_value.__enter__.side_effect = Exception("DB error")

    from app.workers.enrichment_worker import WorkerSettings

    # Must not raise
    await WorkerSettings.on_startup({})


# =============================================================================
# WorkerSettings configuration
# =============================================================================


def test_worker_settings_redis_settings_is_redis_settings_instance():
    """redis_settings is a RedisSettings instance with host/port/database populated."""
    from app.workers.enrichment_worker import WorkerSettings

    assert isinstance(WorkerSettings.redis_settings, RedisSettings)
    assert WorkerSettings.redis_settings.host is not None
    assert WorkerSettings.redis_settings.port is not None
    assert isinstance(WorkerSettings.redis_settings.database, int)


@pytest.mark.asyncio
async def test_on_shutdown_runs_without_error():
    """on_shutdown completes without raising."""
    from app.workers.enrichment_worker import WorkerSettings

    # Must not raise
    await WorkerSettings.on_shutdown({})
