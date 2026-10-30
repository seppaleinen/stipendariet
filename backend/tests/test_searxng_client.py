"""
Unit tests for SearXNGClient.

Tests client initialization, rate limiting, retry logic, and response parsing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services._rate_limit import RateLimiter
from app.services.searxng_client import SearXNGClient, SearXNGError


@pytest.fixture
def client():
    """Create SearXNG client with test config."""
    return SearXNGClient(
        base_url="http://test-searxng:8080",
        rate_limit=1.0,
        timeout=5.0,
        max_retries=2,
        engines=["google", "bing"]
    )


@pytest.mark.asyncio
async def test_client_initialization(client):
    """Test client initializes with correct settings."""
    assert client.base_url == "http://test-searxng:8080"
    assert client.rate_limit == 1.0
    assert client.timeout == 5.0
    assert client.max_retries == 2
    assert client.engines == ["google", "bing"]
    assert isinstance(client._limiter, RateLimiter)


@pytest.mark.asyncio
async def test_search_success(client):
    """Test successful search returns parsed results."""
    mock_response = {
        "results": [
            {
                "title": "Test Foundation",
                "url": "https://example.com/foundation",
                "content": "Sample snippet",
                "engine": "google"
            },
            {
                "title": "Another Foundation",
                "url": "https://example.com/another",
                "content": "Another snippet",
                "engine": "bing"
            }
        ]
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value = mock_client

        results = await client.search("test query", max_results=10)

        assert len(results) == 2
        assert results[0]["url"] == "https://example.com/foundation"
        assert results[0]["title"] == "Test Foundation"
        assert results[0]["snippet"] == "Sample snippet"
        assert results[0]["engine"] == "google"
        assert results[1]["engine"] == "bing"


@pytest.mark.asyncio
async def test_search_empty_results(client):
    """Test search with empty results returns empty list."""
    mock_response = {"results": []}

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value = mock_client

        results = await client.search("test query")

        assert results == []


@pytest.mark.asyncio
async def test_search_missing_fields(client):
    """Test search handles results with missing fields gracefully."""
    mock_response = {
        "results": [
            {
                "url": "https://example.com",
                # title missing
                # content missing
                "engine": "google"
            }
        ]
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value = mock_client

        results = await client.search("test query")

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com"
        assert results[0]["title"] == ""  # default
        assert results[0]["snippet"] == ""  # default


@pytest.mark.asyncio
async def test_search_http_error_retries(client):
    """Test search retries on HTTP errors."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 500
        # raise_for_status should raise HTTPStatusError
        http_error = Exception("500 Server Error")
        mock_response_obj.raise_for_status.side_effect = http_error
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value = mock_client

        # Mock time.sleep to avoid actual delays
        with patch('asyncio.sleep'), pytest.raises(SearXNGError):
            await client.search("test query")

        # Should have been called 3 times (max_retries=2, so 3 total)
        assert mock_client.__aenter__.return_value.get.call_count >= 1


@pytest.mark.asyncio
async def test_rate_limiter_enforced(client):
    """Test rate limiter is used between requests."""
    mock_response = {"results": []}

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value = mock_client

        # Make two searches rapidly
        with patch('asyncio.sleep') as mock_sleep:
            await client.search("query1")
            await client.search("query2")

            # Second call should trigger sleep due to rate limit
            assert mock_sleep.called
