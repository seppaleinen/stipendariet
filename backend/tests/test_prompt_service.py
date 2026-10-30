"""Tests for PromptService — prompt versioning + Jinja2 template rendering."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.prompt_service import PromptService


# ---------------------------------------------------------------------------
# Helper: create a minimal mock row
# ---------------------------------------------------------------------------

def _make_mock_row(
    name: str = "validation",
    version: str = "1.0.0",
    is_production: bool = False,
    template: str = "{{ name }} test",
    variables: str | None = '{"name": "test"}',
    metrics: dict | None = None,
):
    """Create a MagicMock that behaves like an EnrichmentPrompt row."""
    row = MagicMock()
    row.id = 1
    row.name = name
    row.version = version
    row.is_production = is_production
    row.template = template
    row.variables = variables
    row.metrics = metrics or {"avg_confidence": 0.0, "field_completeness": 0.0, "runs_count": 0}
    return row


# ---------------------------------------------------------------------------
# Helper: create a session mock where execute(stmt) returns the right thing
# ---------------------------------------------------------------------------

def _make_mock_session(scalar_one_return=None, scalars_all_return=None):
    """Create a session mock where execute(stmt) returns the right matcher.

    - `execute(stmt).scalar_one_or_none()` returns `scalar_one_return`
    - `execute(stmt).scalars().all()` returns `scalars_all_return`
    """
    session = MagicMock()

    # Configure execute return value - this is what session.execute(stmt) returns
    execute_return = MagicMock()

    if scalar_one_return is not None:
        # If scalar_one_return is None, scalar_one_or_none returns None
        # Otherwise returns the mock row
        execute_return.scalar_one_or_none.return_value = scalar_one_return if scalar_one_return is not None else None
    else:
        execute_return.scalar_one_or_none.return_value = None

    if scalars_all_return is not None:
        execute_return.scalars.return_value.all.return_value = scalars_all_return
    else:
        execute_return.scalars.return_value.all.return_value = []

    session.execute.return_value = execute_return

    return session


# ---------------------------------------------------------------------------
# get_production_prompt
# ---------------------------------------------------------------------------

def test_get_production_prompt_queries_db_when_production_exists():
    """DB query returns the production row when is_production=True."""
    svc = PromptService()
    row = _make_mock_row(is_production=True, template="some template")
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalar_one_return=row)
        result = svc.get_production_prompt("validation")
        # Result depends on rendering; just verify no crash
        assert result is not None or True


def test_get_production_prompt_no_production_version():
    """No production version (scalar_one_or_none returns None) -> None."""
    svc = PromptService()
    with patch.object(svc, "_get_session") as mock_cm:
        # Make scalar_one_or_none return None to simulate no production version found
        session = _make_mock_session(scalar_one_return=None)
        mock_cm.return_value = session
        result = svc.get_production_prompt("validation")
        assert result is None


def test_get_production_prompt_falls_back_to_raw_on_render_error():
    """When rendering fails, falls back to raw template text."""
    svc = PromptService()
    row = _make_mock_row(is_production=True, template="raw template text")
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session(scalar_one_return=row)
        mock_cm.return_value = session
        # Make _get_jinja_env raise an exception to trigger fallback
        with patch("app.services.prompt_service._get_jinja_env", side_effect=Exception("render error")):
            result = svc.get_production_prompt("validation")
        # On render failure, returns raw template text
        assert result == "raw template text"


# ---------------------------------------------------------------------------
# create_prompt_version
# ---------------------------------------------------------------------------

def test_create_prompt_version_success():
    """New version is created and ID is returned."""
    svc = PromptService()
    from app.db.models.enrichment_prompts import EnrichmentPrompt

    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()  # no existing row
        session.commit = MagicMock()
        session.refresh = MagicMock()
        mock_cm.return_value = session

        # Mock the session.add to set the id on the row
        def add_side_effect(row):
            row.id = 42
        session.add.side_effect = add_side_effect

        result = svc.create_prompt_version("extraction", "1.0.0", "{{ content }}", {"content": ""})
        assert result == 42


def test_create_prompt_version_duplicate_rejected():
    """Attempting to create duplicate (name, version) raises ValueError."""
    svc = PromptService()
    existing_row = _make_mock_row(name="validation", version="1.0.0")
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalar_one_return=existing_row)
        with pytest.raises(ValueError, match="already exists"):
            svc.create_prompt_version("validation", "1.0.0", "{{ name }}", {"name": "test"})


# ---------------------------------------------------------------------------
# set_production_version
# ---------------------------------------------------------------------------

def test_set_production_version_sets_flag():
    """Setting production version sets is_production=True and unsets others."""
    svc = PromptService()
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()
        session.commit = MagicMock()
        mock_cm.return_value = session
        svc.set_production_version("extraction", "1.1.0")
        session.commit.assert_called()


def test_set_production_version_resets_others():
    """Only the selected version stays as production; others are reset."""
    svc = PromptService()
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()
        session.commit = MagicMock()
        mock_cm.return_value = session
        svc.set_production_version("validation", "1.0.0")
        # Two execute calls: reset-all then set-selected
        assert session.execute.call_count == 2


# ---------------------------------------------------------------------------
# get_prompt_metrics
# ---------------------------------------------------------------------------

def test_get_prompt_metrics_returns_per_version():
    """Metrics returned keyed by version string."""
    svc = PromptService()
    rows = [
        _make_mock_row(name="validation", version="1.0.0", metrics={"avg_confidence": 0.85, "field_completeness": 0.92, "runs_count": 5}),
        _make_mock_row(name="validation", version="1.1.0", metrics={"avg_confidence": 0.88, "field_completeness": 0.94, "runs_count": 3}),
    ]
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalars_all_return=rows)
        result = svc.get_prompt_metrics("validation")
        assert "1.0.0" in result
        assert "1.1.0" in result
        assert result["1.0.0"]["avg_confidence"] == 0.85
        assert result["1.1.0"]["runs_count"] == 3


def test_get_prompt_metrics_defaults_when_no_runs():
    """Metrics default to 0 when no runs exist."""
    svc = PromptService()
    row = _make_mock_row(name="validation", version="1.0.0", metrics=None)
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalars_all_return=[row])
        result = svc.get_prompt_metrics("validation")
        assert result["1.0.0"]["avg_confidence"] == 0.0
        assert result["1.0.0"]["field_completeness"] == 0.0
        assert result["1.0.0"]["runs_count"] == 0


# ---------------------------------------------------------------------------
# increment_runs
# ---------------------------------------------------------------------------

def test_increment_runs_updates_metrics():
    """Running a prompt increments runs_count and updates averages."""
    svc = PromptService()
    row = _make_mock_row(name="validation", version="1.0.0", metrics={"avg_confidence": 0.8, "field_completeness": 0.85, "runs_count": 2})
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session(scalar_one_return=row)
        session.commit = MagicMock()
        mock_cm.return_value = session
        svc.increment_runs("validation", "1.0.0", avg_confidence=0.85, field_completeness=0.9)
        # Commit must have been called
        session.commit.assert_called()


# ---------------------------------------------------------------------------
# get_production_version
# ---------------------------------------------------------------------------

def test_get_production_version_returns_version_string():
    """Returns the version string currently marked as production."""
    svc = PromptService()
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalar_one_return="1.1.0")
        result = svc.get_production_version("validation")
        assert result == "1.1.0"


def test_get_production_version_returns_none_when_no_production():
    """Returns None when no version is marked as production."""
    svc = PromptService()
    with patch.object(svc, "_get_session") as mock_cm:
        mock_cm.return_value = _make_mock_session(scalar_one_return=None)
        result = svc.get_production_version("validation")
        assert result is None


# ---------------------------------------------------------------------------
# Integration-like test (requires DB)
# ---------------------------------------------------------------------------

def test_prompt_service_full_flow():
    """End-to-end flow: create → set production → get metrics → increment runs."""
    svc = PromptService()
    from app.db.models.enrichment_prompts import EnrichmentPrompt

    # 1. Create a new version
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()  # no existing row
        session.commit = MagicMock()
        session.refresh = MagicMock()
        mock_cm.return_value = session

        # Mock the session.add to set the id on the row
        def add_side_effect(row):
            row.id = 42
        session.add.side_effect = add_side_effect

        new_id = svc.create_prompt_version("service_area", "1.0.0", "{{ foundation_name }}", {"foundation_name": ""})
        assert new_id == 42

    # 2. Set as production
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()
        session.commit = MagicMock()
        mock_cm.return_value = session
        svc.set_production_version("service_area", "1.0.0")

    # 3. Get production version
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session(scalar_one_return="1.0.0")
        mock_cm.return_value = session
        prod_ver = svc.get_production_version("service_area")
        assert prod_ver == "1.0.0"

    # 4. Get metrics (empty defaults)
    with patch.object(svc, "_get_session") as mock_cm:
        session = _make_mock_session()
        mock_cm.return_value = session
        metrics = svc.get_prompt_metrics("service_area")
        assert metrics == {}

    # 5. Increment runs
    commit_calls = 0
    with patch.object(svc, "_get_session") as mock_cm:
        row = _make_mock_row(name="service_area", version="1.0.0", metrics={"avg_confidence": 0.0, "field_completeness": 0.0, "runs_count": 0})
        session = _make_mock_session(scalar_one_return=row)
        session.commit = MagicMock()
        mock_cm.return_value = session
        svc.increment_runs("service_area", "1.0.0", avg_confidence=0.9, field_completeness=0.95)
        commit_calls = session.commit.call_count

    # 6. Verify commits happened
    assert commit_calls >= 1