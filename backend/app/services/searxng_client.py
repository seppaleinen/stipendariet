"""
SearXNG Client — Meta search engine for multi-engine web search.

SearXNG is a free internet metasearch engine which aggregates results from
various search services and databases. Users are neither tracked nor profiled.

Default engines: google, bing, duckduckgo, brave
Rate limit: 1 req/sec (configurable)
"""

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services._rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class SearXNGError(Exception):
    """Custom exception for SearXNG client errors."""
    pass


class SearXNGClient:
    """
    Client for querying SearXNG meta search engine.

    Features:
    - Rate limiting: 1 request/second (configurable via SEARXNG_RATE_LIMIT)
    - Retry with exponential backoff (3 attempts by default)
    - Multi-engine support (configurable engine list)
    - Returns structured dict for pipeline consumption
    - Timeout handling (10s default)
    """

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        engines: list[str] | None = None,
    ):
        """
        Initialize SearXNG client.

        Args:
            base_url: SearXNG instance URL (default: from settings.SEARXNG_URL)
            rate_limit: Requests per second (default: from settings.SEARXNG_RATE_LIMIT)
            timeout: HTTP request timeout in seconds (default: from settings.SEARXNG_TIMEOUT)
            max_retries: Number of retry attempts (default: from settings.SEARXNG_MAX_RETRIES)
            engines: List of search engines to use (default: from settings.SEARXNG_ENGINES)
        """
        self.base_url = (base_url or settings.SEARXNG_URL).rstrip("/")
        # Validate base URL
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid SEARXNG_URL: {self.base_url}")
        self.rate_limit = rate_limit or settings.SEARXNG_RATE_LIMIT
        self.timeout = timeout or settings.SEARXNG_TIMEOUT
        self.max_retries = max_retries or settings.SEARXNG_MAX_RETRIES
        self.engines = engines or settings.SEARXNG_ENGINES

        # Rate limiting
        self._limiter = RateLimiter(self.rate_limit)

    async def _respect_rate_limit(self) -> None:
        """
        Enforce minimum interval between requests to respect rate limit.

        Uses shared RateLimiter for consistency with other clients.
        """
        await self._limiter.acquire()

    def _extract_result(self, result: dict[str, Any], strategy: str = "") -> dict:
        """
        Extract pipeline-friendly fields from SearXNG result.

        Args:
            result: Single result dict from SearXNG response
            strategy: Search strategy that produced this result

        Returns:
            Structured dict with: url, title, snippet, engine, strategy
        """
        return {
            "url": result.get("url", ""),
            "title": result.get("title", ""),
            "snippet": result.get("content", ""),
            "engine": result.get("engine", "unknown"),
            "strategy": strategy,
        }

    async def search(
        self,
        query: str,
        engines: list[str] | None = None,
        max_results: int = 10,
        strategy: str = "",
    ) -> list[dict]:
        """
        Perform a search query against SearXNG.

        Args:
            query: Search query string
            engines: Optional list of engines to use (overrides default)
            max_results: Maximum number of results to return
            strategy: Search strategy identifier for metadata

        Returns:
            List of structured result dicts (url, title, snippet, engine, strategy)
            or empty list on error/failure

        Raises:
            SearXNGError: On persistent failures after all retries
        """
        url = f"{self.base_url}/search"

        # Build request parameters
        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }

        # Add engines if specified
        if engines:
            params["engines"] = ",".join(engines)
        elif self.engines:
            params["engines"] = ",".join(self.engines)

        # Enforce rate limit before making request
        await self._respect_rate_limit()

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                results = data.get("results", [])
                if not results:
                    logger.info(f"No results from SearXNG for query: {query}")
                    return []

                # Extract and limit results
                extracted = []
                for result in results[:max_results]:
                    extracted.append(self._extract_result(result, strategy))

                logger.info(
                    f"SearXNG search successful for query: {query} "
                    f"({len(extracted)} results from engines: {params.get('engines', 'default')})"
                )
                return extracted

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 429:
                    # Rate limited — use exponential backoff
                    delay = 2.0 ** attempt
                    logger.warning(
                        f"Rate limited (429) by SearXNG, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Other HTTP errors — log and retry
                logger.error(
                    f"SearXNG API error {e.response.status_code} for query '{query}': {e}"
                )
                delay = 2.0 ** attempt
                await asyncio.sleep(delay)

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                delay = 2.0 ** attempt
                logger.warning(
                    f"Request failed ({type(e).__name__}) for query '{query}', "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                logger.exception(
                    f"Unexpected error during SearXNG search for query '{query}': {e}"
                )
                raise SearXNGError(f"Unexpected error: {e}")

        # All retries exhausted
        logger.error(
            f"All {self.max_retries + 1} attempts failed for query: {query}"
        )
        if last_exception is not None:
            raise SearXNGError(f"Search failed after {self.max_retries + 1} attempts: {last_exception}")
        return []
