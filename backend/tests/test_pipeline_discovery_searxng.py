"""
Integration tests for DiscoveryStage with SearXNG.

Tests the SearXNG integration and DDG fallback.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.discovery import _searxng_search, discover_candidate_urls


@pytest.mark.asyncio
async def test_discover_candidate_urls_searxng_success():
    """Test discovery uses SearXNG successfully."""
    mock_results = [
        {"url": "https://example.com/foundation", "title": "Test", "snippet": "...", "engine": "google"},
        {"url": "https://example.com/about", "title": "About", "snippet": "...", "engine": "bing"},
    ]

    with patch('app.pipeline.discovery._searxng_search', new_callable=AsyncMock) as mock_search, \
         patch('app.pipeline.discovery._get_redis', return_value=None):
        mock_search.side_effect = [
            mock_results,  # site_se
            mock_results,  # bidrag_ansokan
            [],  # stipendium
            [],  # kontakt
        ]
        candidates = await discover_candidate_urls("Test Foundation", "123456", max_urls=7)

    # Should have candidates from SearXNG
    assert len(candidates) >= 2
    assert any(c["engine"] in ["google", "bing", "searxng"] for c in candidates)
    assert any(c["strategy"] in ["site_se", "bidrag_ansokan"] for c in candidates)


@pytest.mark.asyncio
async def test_discover_candidate_urls_searxng_fails_fallback_to_ddg():
    """Test discovery falls back to DDG when SearXNG fails."""
    with patch('app.pipeline.discovery._searxng_search', new_callable=AsyncMock) as mock_search, \
         patch('app.pipeline.discovery._ddgs_search') as mock_ddg:
        mock_search.return_value = []  # SearXNG returns nothing
        mock_ddg.return_value = [
            {"href": "https://fallback.com", "title": "Fallback", "body": "Snippet"}
        ]
        candidates = await discover_candidate_urls("Test Foundation", "123456", max_urls=7)

    # Should fall back to DDG
    assert len(candidates) >= 1
    assert any(c["engine"] == "ddg" for c in candidates)


@pytest.mark.asyncio
async def test_searxng_search_caching():
    """Test SearXNG search caching works."""
    mock_results = [{"url": "https://example.com", "title": "Test", "snippet": "...", "engine": "google"}]

    with patch('app.pipeline.discovery._get_redis') as mock_get_redis:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis.set = AsyncMock()
        mock_get_redis.return_value = mock_redis

        with patch('app.pipeline.discovery.SearXNGClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            # First call - cache miss, should call client
            results1 = await _searxng_search("test query")
            assert len(results1) == 1
            assert mock_client.search.called

            # Second call - cache hit
            mock_redis.get = AsyncMock(return_value='[{"url": "https://cached.com", "title": "Cached", "snippet": "", "engine": "google"}]')
            results2 = await _searxng_search("test query")
            assert len(results2) == 1
            assert results2[0]["url"] == "https://cached.com"
            # Client should not be called again
            assert mock_client.search.call_count == 1


@pytest.mark.asyncio
async def test_discover_candidate_urls_respects_max_urls():
    """Test discovery respects max_urls limit."""
    mock_results = [
        {"url": f"https://example{i}.com", "title": f"Test{i}", "snippet": "...", "engine": "google"}
        for i in range(20)
    ]

    with patch('app.pipeline.discovery._searxng_search', new_callable=AsyncMock) as mock_search, \
         patch('app.pipeline.discovery._get_redis', return_value=None):
        mock_search.return_value = mock_results
        candidates = await discover_candidate_urls("Test Foundation", "123456", max_urls=5)

    assert len(candidates) <= 5


@pytest.mark.asyncio
async def test_discover_candidate_urls_excludes_domains():
    """Test discovery excludes blocked domains."""
    mock_results = [
        {"url": "https://www.allabolag.se/foundation", "title": "Allabolag", "snippet": "...", "engine": "google"},
        {"url": "https://example.com/foundation", "title": "Valid", "snippet": "...", "engine": "google"},
    ]

    with patch('app.pipeline.discovery._searxng_search', new_callable=AsyncMock) as mock_search, \
         patch('app.pipeline.discovery._get_redis', return_value=None):
        mock_search.return_value = mock_results
        candidates = await discover_candidate_urls("Test Foundation", "123456", max_urls=7)

    # Allabolag should be excluded
    urls = [c["url"] for c in candidates]
    assert "https://www.allabolag.se/foundation" not in urls
    assert "https://example.com/foundation" in urls


@pytest.mark.asyncio
async def test_discover_candidate_urls_with_orgnr_in_query():
    """Test orgnr is included in site:se query."""
    captured_queries = []

    async def mock_searxng_search(query, max_results=10):
        captured_queries.append(query)
        return []

    with patch('app.pipeline.discovery._searxng_search', side_effect=mock_searxng_search), \
         patch('app.pipeline.discovery._get_redis', return_value=None):
        await discover_candidate_urls("Test Foundation", "1234567890", max_urls=7)

    # First SearXNG query should include orgnr and site:se
    site_se_query = captured_queries[0]
    assert "1234567890" in site_se_query
    assert "site:se" in site_se_query
    assert "Test Foundation" in site_se_query


@pytest.mark.asyncio
async def test_discover_candidate_urls_without_orgnr():
    """Test discovery works without orgnr."""
    captured_queries = []

    async def mock_searxng_search(query, max_results=10):
        captured_queries.append(query)
        return []

    with patch('app.pipeline.discovery._searxng_search', side_effect=mock_searxng_search), \
         patch('app.pipeline.discovery._get_redis', return_value=None):
        await discover_candidate_urls("Test Foundation", "", max_urls=7)

    # First query should not have empty orgnr
    site_se_query = captured_queries[0]
    assert "Test Foundation" in site_se_query
    assert "site:se" in site_se_query
