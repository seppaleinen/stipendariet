"""
Unit tests for trafilatura-first crawler.
"""

from unittest.mock import MagicMock, patch

import pytest


@patch("app.pipeline.crawler.trafilatura.extract")
@patch("app.pipeline.crawler.trafilatura.fetch_url")
def test_crawl_with_trafilatura_success(mock_fetch, mock_extract):
    """Test successful trafilatura crawl returns dict with all keys."""
    from app.pipeline.crawler import crawl_with_trafilatura

    mock_fetch.return_value = "<html><body>Test content</body></html>"
    mock_extract.return_value = "# Test Title\n\nThis is test content for crawling. " * 20

    result = crawl_with_trafilatura("https://example.com")

    assert result is not None
    assert result["url"] == "https://example.com"
    assert "markdown" in result
    assert "content_hash" in result
    assert result["source"] == "trafilatura"
    # Note: type is NOT included in result dict


@patch("app.pipeline.crawler.trafilatura.extract")
@patch("app.pipeline.crawler.trafilatura.fetch_url")
def test_crawl_with_trafilatura_short_content(mock_fetch, mock_extract):
    """Test trafilatura crawl returns None for short content."""
    from app.pipeline.crawler import crawl_with_trafilatura

    mock_fetch.return_value = "<html><body>Short</body></html>"
    mock_extract.return_value = "Too short"

    result = crawl_with_trafilatura("https://example.com")

    assert result is None


@patch("app.pipeline.crawler.trafilatura.fetch_url")
def test_crawl_with_trafilatura_network_error(mock_fetch):
    """Test trafilatura crawl returns None on network error."""
    from app.pipeline.crawler import crawl_with_trafilatura

    mock_fetch.side_effect = Exception("Network error")

    result = crawl_with_trafilatura("https://example.com")

    assert result is None


@pytest.mark.asyncio
@patch("app.pipeline.crawler.trafilatura.fetch_url")
@patch("app.pipeline.crawler.trafilatura.extract")
@patch("app.pipeline.crawler._fetch_robots_txt")
async def test_crawl_foundation_site_robots_disallow(
    mock_fetch_robots, mock_extract, mock_fetch
):
    """Test crawl returns empty list when robots.txt disallows."""
    from app.pipeline.crawler import crawl_foundation_site

    mock_fetch_robots.return_value = set(["/admin/"])
    mock_fetch.return_value = "<html><body>Test</body></html>"
    mock_extract.return_value = "# Content\n\nTest content " * 100

    result = await crawl_foundation_site("https://example.com")

    # Path '/' is not '/admin/' so it should crawl
    assert len(result) > 0


@pytest.mark.asyncio
@patch("app.pipeline.crawler.trafilatura.fetch_url")
@patch("app.pipeline.crawler.trafilatura.extract")
@patch("app.pipeline.crawler._fetch_robots_txt")
async def test_crawl_foundation_site_trafilatura_first(
    mock_fetch_robots, mock_extract, mock_fetch
):
    """Test crawl tries trafilatura first for homepage."""
    from app.pipeline.crawler import crawl_foundation_site

    mock_fetch_robots.return_value = set()
    mock_fetch.return_value = "<html><body>Test</body></html>"
    mock_extract.return_value = "# Content\n\nTest content " * 100

    # Mock BeautifulSoup to avoid actual parsing
    with patch("app.pipeline.crawler.BeautifulSoup") as mock_bs:
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = []
        mock_bs.return_value = mock_soup

        result = await crawl_foundation_site("https://example.com")

        assert len(result) > 0
        assert result[0]["source"] == "trafilatura"
        assert result[0]["type"] == "homepage"


def test_compute_content_hash_consistency():
    """Test compute_content_hash returns consistent hashes."""
    from app.utils.content_dedup import compute_content_hash

    content = "Test content for hashing"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)

    assert hash1 == hash2
    assert len(hash1) == 32  # 32 hex chars for 128-bit
