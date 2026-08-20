"""
Pytest fixtures and configuration for backend tests.

When TEST_DATABASE_URL is set (CI with a real Postgres service), the real
app.db.database module is used. Otherwise, mock it out so tests can be
collected and run without a database.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest


def _mock_get_db():
    """Mock get_db that yields a MagicMock session (FastAPI-compatible generator)."""
    yield MagicMock()


# Only mock the database module if TEST_DATABASE_URL is not set.
# In CI, TEST_DATABASE_URL is set by the workflow env block.
use_real_db = os.getenv("TEST_DATABASE_URL") is not None

if not use_real_db:
    _mock = MagicMock()
    _mock.create_engine_with_retry = MagicMock(return_value=MagicMock())
    _mock.get_db = _mock_get_db
    _mock.SessionLocal = MagicMock()
    _mock.create_tables = MagicMock()
    sys.modules["app.db.database"] = _mock

    # Also mock the scheduler to prevent APScheduler background threads from
    # hanging pytest.  The startup event calls init_scheduler() which starts
    # real BackgroundScheduler threads that block process exit.
    _mock_scheduler = MagicMock()
    _mock_scheduler.init_scheduler = MagicMock()
    _mock_scheduler.get_scheduler = MagicMock()
    sys.modules["app.foundation.scheduler"] = _mock_scheduler


@pytest.fixture
def db_session():
    """Provide a mock database session for CRUD tests."""
    return MagicMock()
