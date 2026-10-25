"""Regression test for the graceful-skip path of migrations_check.py.

This test verifies that when no database driver (psycopg2/psycopg) is
available, `migrations_check.main()` returns 0 and prints a specific
message instead of crashing with a ModuleNotFoundError.

The test uses a custom sys.meta_path finder to block imports of the
driver modules, ensuring the script's try/except guard is exercised.
"""
import sys

import pytest

# The exact set of driver module names to block.
_BLOCKLIST = {"psycopg2", "psycopg", "psycopg2-binary", "psycopg2_binary"}


class _DriverBlocker:
    """A sys.meta_path finder that raises ModuleNotFoundError for blocked drivers."""

    def find_spec(self, fullname, path, target=None):
        # Check if the top-level package is in the blocklist.
        top_level = fullname.split(".")[0]
        if top_level in _BLOCKLIST:
            raise ModuleNotFoundError(f"Blocked import for testing: {fullname}")
        return None


@pytest.fixture
def block_db_drivers():
    """Install a meta_path finder that blocks psycopg2/psycopg imports.

    This fixture ensures that any attempt to import these modules within
    the test body will raise ModuleNotFoundError, allowing us to test
    the graceful fallback path in migrations_check.py.
    """
    # 1. Save current state of sys.modules for affected keys.
    saved_modules = {}
    for name in list(sys.modules.keys()):
        top_level = name.split(".")[0]
        if top_level in _BLOCKLIST:
            saved_modules[name] = sys.modules.pop(name)

    # 2. Install the blocker at index 0 of meta_path.
    blocker = _DriverBlocker()
    sys.meta_path.insert(0, blocker)

    yield

    # 3. Teardown: remove the blocker.
    sys.meta_path.remove(blocker)

    # 4. Restore saved modules.
    for name, mod in saved_modules.items():
        sys.modules[name] = mod

    # 5. Clean up any new entries created during the test for blocked names.
    for name in list(sys.modules.keys()):
        top_level = name.split(".")[0]
        if top_level in _BLOCKLIST and name not in saved_modules:
            del sys.modules[name]


def test_migrations_check_graceful_skip(block_db_drivers, capsys):
    """Verify migrations_check.main() returns 0 and prints skip message when drivers are missing."""
    # Import main inside the context where drivers are blocked.
    # We must import it here so that the module-level code doesn't trigger
    # the driver import before our block is active (though migrations_check.py
    # defers imports to main(), so this is safe).
    from migrations_check import main

    result = main()

    captured = capsys.readouterr()

    # Assertion 1: Returns 0
    assert result == 0, f"Expected return code 0, got {result}"

    # Assertion 2: Exact skip message in stdout
    expected_msg = "migrations_check: sqlalchemy/dbapi unavailable, skipping check"
    assert expected_msg in captured.out, (
        f"Expected '{expected_msg}' in stdout, got:\n{captured.out}"
    )

    # Assertion 3: No traceback in stdout or stderr
    assert "Traceback" not in captured.out, "Found 'Traceback' in stdout"
    assert "Traceback" not in captured.err, "Found 'Traceback' in stderr"
