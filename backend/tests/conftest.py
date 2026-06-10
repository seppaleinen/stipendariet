"""
Pytest fixtures and configuration for backend tests.
"""
import sys
from unittest.mock import MagicMock

# Create a mock module for app.db.database
_mock_db = MagicMock()
_mock_db.create_engine_with_retry = MagicMock(return_value=MagicMock())
_mock_db.get_db = MagicMock()
_mock_db.SessionLocal = MagicMock()
_mock_db.create_tables = MagicMock()

# Replace the module in sys.modules before any imports happen
sys.modules['app.db.database'] = _mock_db
