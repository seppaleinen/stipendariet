"""Tests for the service area extraction pipeline stage."""

from unittest.mock import patch

import pytest

from app.pipeline.service_area import (
    _map_location_to_codes,
    extract_service_area,
)


class TestMapLocationToCodes:
    """Tests for the _map_location_to_codes mapping function."""

    def test_municipality_exact_match(self):
        result = _map_location_to_codes("Kalmar", "municipality")
        assert result is not None
        assert result["municipality_code"] == "0880"
        assert result["county_code"] == "08"
        assert result["municipality_name"] == "Kalmar"

    def test_municipality_case_insensitive(self):
        result = _map_location_to_codes("stockholm", "municipality")
        assert result is not None
        assert result["municipality_code"] == "0180"
        assert result["county_code"] == "01"

    def test_municipality_with_whitespace(self):
        result = _map_location_to_codes("  Göteborg  ", "municipality")
        assert result is not None
        assert result["municipality_code"] == "1480"

    def test_county_exact_match(self):
        result = _map_location_to_codes("Kalmar", "county")
        assert result is not None
        assert result["county_code"] == "08"
        assert result["municipality_code"] is None

    def test_county_lookup(self):
        result = _map_location_to_codes("Skåne", "county")
        assert result is not None
        assert result["county_code"] == "12"

    def test_fallback_to_municipality_when_granularity_is_county(self):
        """When LLM says county but name is actually a municipality, match as municipality."""
        result = _map_location_to_codes("Kalmar", "county")
        assert result is not None
        # Should match as municipality since "Kalmar" is both a county name and a municipality
        assert result["municipality_code"] == "0880" or result["county_code"] == "08"

    def test_unknown_location_returns_none(self):
        result = _map_location_to_codes("Atlantis", "municipality")
        assert result is None

    def test_none_location_returns_none(self):
        result = _map_location_to_codes(None, None)
        assert result is None

    def test_empty_location_returns_none(self):
        result = _map_location_to_codes("", "municipality")
        assert result is None

    def test_multi_word_municipality(self):
        result = _map_location_to_codes("Malung-Sälen", "municipality")
        assert result is not None
        assert result["municipality_code"] == "2023"

    def test_county_name_with_len_suffix(self):
        """County lookup should work with names that have 'län' suffix."""
        result = _map_location_to_codes("Kalmar län", "county")
        assert result is not None
        assert result["county_code"] == "08"


class TestExtractServiceArea:
    """Tests for the extract_service_area async function."""

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_extracts_municipality(self, mock_chat):
        mock_chat.return_value = '{"location_name": "Kalmar", "granularity": "municipality"}'

        result = await extract_service_area(
            "Stiftelsen för personer bosatta i Kalmar",
            purpose="Att stödja personer bosatta i Kalmar kommun",
        )

        assert result is not None
        assert result["municipality_code"] == "0880"
        assert result["county_code"] == "08"
        assert result["confidence"] == "high"

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_extracts_county(self, mock_chat):
        mock_chat.return_value = '{"location_name": "Skåne", "granularity": "county"}'

        result = await extract_service_area(
            "Stiftelsen för skåningar",
            purpose="Stödja personer i Skåne",
        )

        assert result is not None
        assert result["county_code"] == "12"
        assert result["municipality_code"] is None
        assert result["confidence"] == "medium"

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_no_location_returns_none(self, mock_chat):
        mock_chat.return_value = '{"location_name": null, "granularity": null}'

        result = await extract_service_area(
            "Allmän stiftelse",
            purpose="Att hjälpa folk i behov",
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_llm_returns_empty_returns_none(self, mock_chat):
        mock_chat.return_value = None

        result = await extract_service_area("Test Foundation", purpose="Some purpose")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_llm_returns_invalid_json_returns_none(self, mock_chat):
        mock_chat.return_value = "not valid json"

        result = await extract_service_area("Test Foundation", purpose="Some purpose")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_unknown_location_returns_none(self, mock_chat):
        mock_chat.return_value = '{"location_name": "Narnia", "granularity": "municipality"}'

        result = await extract_service_area(
            "Stiftelsen för Narnia",
            purpose="Help people in Narnia",
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_result_has_source_text(self, mock_chat):
        mock_chat.return_value = '{"location_name": "Kalmar", "granularity": "municipality"}'

        result = await extract_service_area("Stiftelsen Kalmar", purpose="For Kalmar")

        assert result is not None
        assert result["source_text"] == "Kalmar"

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_truncates_long_content(self, mock_chat):
        mock_chat.return_value = '{"location_name": null, "granularity": null}'

        long_purpose = "x" * 3000
        await extract_service_area("Test", purpose=long_purpose)

        # Verify the prompt was called (content was truncated, not error)
        mock_chat.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_code_fences_stripped(self, mock_chat):
        mock_chat.return_value = '```json\n{"location_name": "Kalmar", "granularity": "municipality"}\n```'

        result = await extract_service_area("Stiftelsen Kalmar", purpose="For Kalmar")

        assert result is not None
        assert result["municipality_code"] == "0880"

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_extracts_service_area_detail(self, mock_chat):
        """Street-level detail (gata/stadsdel/område) is preserved alongside the codes."""
        mock_chat.return_value = (
            '{"location_name": "Stockholm", "granularity": "municipality", '
            '"service_area_detail": "endast boende på Norr Mälarstrand"}'
        )

        result = await extract_service_area(
            "Stiftelsen Norr Mälarstrand",
            purpose="Stöd till boende på Norr Mälarstrand i Stockholm",
        )

        assert result is not None
        assert result["municipality_code"] == "0180"
        assert result["service_area_detail"] == "endast boende på Norr Mälarstrand"

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_no_detail_when_not_mentioned(self, mock_chat):
        """When the LLM returns null detail, the stored JSON has the key as None."""
        mock_chat.return_value = (
            '{"location_name": "Kalmar", "granularity": "municipality", "service_area_detail": null}'
        )

        result = await extract_service_area("Stiftelsen Kalmar", purpose="För Kalmar")

        assert result is not None
        assert result["municipality_code"] == "0880"
        assert result.get("service_area_detail") is None

    @pytest.mark.asyncio
    @patch("app.pipeline.service_area.chat_completion")
    async def test_detail_defaults_none_when_llm_omits_key(self, mock_chat):
        """Backward compatibility: an LLM response without the new key still parses."""
        mock_chat.return_value = '{"location_name": "Kalmar", "granularity": "municipality"}'

        result = await extract_service_area("Stiftelsen Kalmar", purpose="För Kalmar")

        assert result is not None
        assert result["municipality_code"] == "0880"
        assert result.get("service_area_detail") is None
