"""
Tests for BolagsverketClient.
"""
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.bolagsverket_client import BolagsverketClient


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.AsyncClient context manager."""
    with patch("httpx.AsyncClient") as mock:
        yield mock


def _make_mock_response(json_data, status_code=200, headers=None):
    """Create a mock response with proper sync json() method (httpx 0.28+)."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    mock_response.json.return_value = json_data  # sync method in httpx 0.28+

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error",
            request=MagicMock(),
            response=mock_response,
        )
    else:
        mock_response.raise_for_status = MagicMock()

    return mock_response


@pytest.mark.asyncio
async def test_lookup_by_orgnr_success(mock_httpx_client):
    """Successful lookup returns structured data with all expected fields."""
    # Setup mock response
    mock_response = _make_mock_response({
        "organisationer": [{
            "organisationsidentitet": {"identitetsbeteckning": "5560747551"},
            "organisationsnamn": {
                "organisationsnamnLista": [
                    {
                        "namn": "Test Foundation AB",
                        "organisationsnamntyp": {"kod": "FORETAGSNAMN"},
                    }
                ]
            },
            "organisationsform": {"klartext": "Aktiebolag"},
            "organisationsdatum": {"registreringsdatum": "2020-01-15"},
            "postadressOrganisation": {
                "postadress": {
                    "utdelningsadress": "Box 1",
                    "postnummer": "11122",
                    "postort": "STOCKHOLM",
                }
            },
            "verksamOrganisation": {"kod": "JA"},
            "naringsgrenOrganisation": {"sni": [{"kod": "94990"}]},
        }]
    })
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Create client with fast rate limit for testing
    client = BolagsverketClient(
        base_url="https://api.example.com",
        rate_limit=100,  # Fast for tests
        max_retries=0,   # No retries in this test
    )
    result = await client.lookup_by_orgnr("5560747551")

    # Assertions
    assert result is not None
    assert result["legal_name"] == "Test Foundation AB"
    assert result["address"] == "Box 1, 11122 STOCKHOLM"
    assert result["status"] == "ACTIVE"
    assert result["registration_date"] == "2020-01-15"
    assert result["legal_form"] == "Aktiebolag"
    assert result["sni_codes"] == ["94990"]
    assert result["website"] is None
    assert result["representatives"] == []
    assert "raw_response" in result


@pytest.mark.asyncio
async def test_lookup_by_orgnr_not_found(mock_httpx_client):
    """404 returns None (not an error)."""
    mock_response = _make_mock_response(
        {"error": "Organisation not found"},
        status_code=404,
    )
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response

    client = BolagsverketClient(base_url="https://api.example.com", rate_limit=100)
    result = await client.lookup_by_orgnr("0000000000")

    assert result is None


@pytest.mark.asyncio
async def test_lookup_by_orgnr_invalid_format():
    """Invalid orgnr format returns None without making HTTP call."""
    client = BolagsverketClient(rate_limit=100)

    # Too short
    result = await client.lookup_by_orgnr("123")
    assert result is None

    # Non-digits
    result = await client.lookup_by_orgnr("abcdefghij")
    assert result is None

    # None/empty
    result = await client.lookup_by_orgnr("")
    assert result is None


@pytest.mark.asyncio
async def test_rate_limiting_enforced():
    """Client enforces 1 req/sec rate limit between calls."""
    client = BolagsverketClient(rate_limit=1.0, max_retries=0)

    # Mock HTTP to return 404 quickly (we're testing rate limit, not HTTP)
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = _make_mock_response(
            {"error": "Not Found"},
            status_code=404,
        )
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        start = time.monotonic()
        await client.lookup_by_orgnr("5560747551")
        await client.lookup_by_orgnr("5560747551")
        elapsed = time.monotonic() - start

    # Should have waited ~1 second between calls (allow 0.1s tolerance)
    assert elapsed >= 0.9


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff(mock_httpx_client):
    """Retries on 5xx errors with exponential backoff (2^attempt seconds)."""
    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # First two calls: 500 error
            raise httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=_make_mock_response({"error": "Server Error"}, status_code=500),
            )
        # Third call: success
        return _make_mock_response({
            "organisationer": [{"organisationsidentitet": {"identitetsbeteckning": "1234567890"}}]
        })

    mock_httpx_client.return_value.__aenter__.return_value.get.side_effect = mock_get

    client = BolagsverketClient(max_retries=3, rate_limit=100)
    result = await client.lookup_by_orgnr("1234567890")

    assert call_count == 3  # 2 failures + 1 success
    assert result is not None


@pytest.mark.asyncio
async def test_rate_limit_429_respects_retry_after(mock_httpx_client):
    """429 rate limit respects Retry-After header."""
    call_count = 0
    sleep_delays = []

    async def mock_sleep(delay):
        sleep_delays.append(delay)

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: 429 with Retry-After: 5
            raise httpx.HTTPStatusError(
                "Rate Limited",
                request=MagicMock(),
                response=_make_mock_response(
                    {"error": "Rate Limited"},
                    status_code=429,
                    headers={"Retry-After": "5"},
                ),
            )
        # Second call: success
        return _make_mock_response({
            "organisationer": [{"organisationsidentitet": {"identitetsbeteckning": "1234567890"}}]
        })

    mock_httpx_client.return_value.__aenter__.return_value.get.side_effect = mock_get

    with patch("asyncio.sleep", mock_sleep):
        client = BolagsverketClient(max_retries=3, rate_limit=100)
        result = await client.lookup_by_orgnr("1234567890")

    assert call_count == 2
    assert len(sleep_delays) == 1
    assert sleep_delays[0] == 5.0  # Respected Retry-After header
    assert result is not None


@pytest.mark.asyncio
async def test_auth_header_sent_when_api_key_set(mock_httpx_client):
    """Bearer token sent in Authorization header when api_key is configured."""
    mock_response = _make_mock_response({"organisationer": []})
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response

    client = BolagsverketClient(api_key="test-secret-key", rate_limit=100)
    await client.lookup_by_orgnr("5560747551")

    # Verify headers included Bearer token
    call_args = mock_httpx_client.return_value.__aenter__.return_value.get.call_args
    headers = call_args.kwargs.get("headers", {})
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-secret-key"


@pytest.mark.asyncio
async def test_no_auth_header_when_api_key_empty(mock_httpx_client):
    """No Authorization header when api_key is empty."""
    mock_response = _make_mock_response({"organisationer": []})
    mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response

    client = BolagsverketClient(api_key="", rate_limit=100)
    await client.lookup_by_orgnr("5560747551")

    # Verify headers do NOT include Authorization
    call_args = mock_httpx_client.return_value.__aenter__.return_value.get.call_args
    headers = call_args.kwargs.get("headers", {})
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_timeout_config_applied():
    """Custom timeout is applied to httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = _make_mock_response(
            {"error": "Not Found"},
            status_code=404,
        )
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        client = BolagsverketClient(timeout=5.0, rate_limit=100)
        await client.lookup_by_orgnr("5560747551")

        # Verify timeout passed to AsyncClient
        mock_client.assert_called_once_with(timeout=5.0)


def test_extract_structured_handles_missing_fields():
    """_extract_structured handles missing/None fields gracefully."""
    client = BolagsverketClient(rate_limit=100)

    # Minimal response with many missing fields
    org_data = {
        "organisationsnamn": {"organisationsnamnLista": []},
        "postadressOrganisation": {},
        "verksamOrganisation": {},
        "organisationsdatum": {},
        "organisationsform": {},
        "naringsgrenOrganisation": {"sni": [{"kod": ""}, {"kod": "   "}]},
    }

    result = client._extract_structured(org_data)

    assert result["legal_name"] is None
    assert result["address"] is None
    assert result["status"] == "INACTIVE"  # Default when verksamOrganisation.kod missing
    assert result["registration_date"] is None
    assert result["legal_form"] is None
    assert result["sni_codes"] == []  # Empty strings filtered out
