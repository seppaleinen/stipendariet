"""
Pytest fixtures and configuration for backend tests.

All tests run as pure unit tests with mocked DB and scheduler.
The database module and scheduler are always mocked at the sys.modules
level so that no real DB connection or APScheduler threads are created.
"""
import sys
from unittest.mock import MagicMock

import pytest


def _mock_get_db():
    """Mock get_db that yields a MagicMock session (FastAPI-compatible generator)."""
    yield MagicMock()


# Always mock the database module — all existing tests are unit tests
# that expect mocked behaviour (no real DB required).
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
