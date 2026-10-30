"""
Shared rate limiting primitive for API clients.

Extracted to avoid duplication between BolagsverketClient and SearXNGClient.
Both clients need identical rate limiting behavior.
"""

import asyncio
import time


class RateLimiter:
    """
    Async rate limiter using token-bucket style with minimum interval.

    Ensures at least `min_interval` seconds between successive acquisitions.
    Thread-safe via asyncio.Lock.
    """

    def __init__(self, rate_limit: float):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Requests per second. 1.0 = 1 req/sec, 0 = no limiting.
        """
        self._min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Wait until enough time has elapsed since last acquisition.

        Safe to call concurrently from multiple coroutines.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()
