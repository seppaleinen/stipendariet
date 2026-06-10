"""
Hybrid scraper service using trafilatura for static pages
and browserless container for JavaScript-heavy pages.
"""
import logging

import httpx
import trafilatura

from app.core.config import settings

logger = logging.getLogger(__name__)

# Keywords indicating JavaScript is required (Swedish and English)
JS_REQUIRED_INDICATORS = [
    "enable javascript",
    "aktivera javascript",
    "javascript krävs",
    "loading...",
    "laddar...",
    "please wait",
    "vänta",
]

# Minimum content length to consider valid
MIN_CONTENT_LENGTH = 500


async def smart_scrape(url: str, timeout: int = 30) -> str | None:
    """
    Hybrid scraper that tries trafilatura first, falls back to browserless.

    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds

    Returns:
        Extracted text content, or None on failure
    """
    logger.info(f"Scraping URL: {url}")

    # Attempt 1: Try trafilatura (fast, no JS)
    try:
        content = await _scrape_with_trafilatura(url, timeout)
        if _is_valid_content(content):
            logger.info(f"Trafilatura succeeded for {url}")
            return content
        logger.info(f"Trafilatura content invalid, falling back to browserless for {url}")
    except Exception as e:
        logger.warning(f"Trafilatura failed for {url}: {e}")

    # Attempt 2: Fallback to browserless container
    try:
        content = await _scrape_with_browserless(url, timeout)
        if content:
            logger.info(f"Browserless succeeded for {url}")
            return content
    except Exception as e:
        logger.error(f"Browserless also failed for {url}: {e}")

    return None


async def _scrape_with_trafilatura(url: str, timeout: int) -> str | None:
    """Fetch and extract content using trafilatura."""
    # trafilatura.fetch_url is synchronous, run in thread
    import asyncio
    loop = asyncio.get_event_loop()
    downloaded = await loop.run_in_executor(
        None,
        lambda: trafilatura.fetch_url(url)
    )

    if not downloaded:
        return None

    # Extract main content
    content = await loop.run_in_executor(
        None,
        lambda: trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    )

    return content


async def _scrape_with_browserless(url: str, timeout: int) -> str | None:
    """
    Scrape URL using browserless container's /content endpoint.

    Browserless renders the page with JavaScript and returns the HTML,
    which we then extract text from using trafilatura.
    """
    browserless_url = getattr(settings, 'BROWSERLESS_URL', 'http://browserless:3000')

    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        response = await client.post(
            f"{browserless_url}/content",
            json={
                "url": url,
                "waitFor": 3000,  # Wait 3s for JS to load
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            logger.error(f"Browserless returned {response.status_code}: {response.text}")
            return None

        html = response.text

        # Extract text from the rendered HTML using trafilatura
        import asyncio
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            lambda: trafilatura.extract(html, include_comments=False, include_tables=True)
        )

        return content


def _is_valid_content(content: str | None) -> bool:
    """
    Validate that scraped content is usable.

    Returns False if:
    - Content is None or empty
    - Content is too short (< MIN_CONTENT_LENGTH chars)
    - Content contains JavaScript-required indicators
    """
    if not content:
        return False

    if len(content) < MIN_CONTENT_LENGTH:
        logger.debug(f"Content too short: {len(content)} chars")
        return False

    content_lower = content.lower()
    for indicator in JS_REQUIRED_INDICATORS:
        if indicator in content_lower:
            logger.debug(f"JS indicator found: {indicator}")
            return False

    return True
