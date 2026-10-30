"""
Bolagsverket Client — Swedish Companies Registration Office lookup.

Official API: https://data.bolagsverket.se/api/
(Värdefulla datamängder / High-Value Datasets initiative)

Free tier: 60 req/min (1 req/sec). Requires OAuth 2.0 for production;
optional Bearer token support for flexibility.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services._rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class BolagsverketClient:
    """
    Client for looking up Swedish organizations by organisationsnummer (orgnr).

    Features:
    - Rate limiting: 1 request/second (configurable via BOLAGSVERKET_RATE_LIMIT)
    - Retry with exponential backoff (3 attempts by default)
    - Optional Bearer token auth (via BOLAGSVERKET_API_KEY)
    - Returns structured dict for pipeline consumption
    - Graceful handling of 404 (returns None, not error)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        rate_limit: float | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
    ):
        """
        Initialize Bolagsverket client.

        Args:
            base_url: API base URL (default: from settings.BOLAGSVERKET_URL)
            api_key: OAuth 2.0 Bearer token (default: from settings.BOLAGSVERKET_API_KEY)
            rate_limit: Requests per second (default: from settings.BOLAGSVERKET_RATE_LIMIT)
            max_retries: Number of retry attempts (default: from settings.BOLAGSVERKET_MAX_RETRIES)
            timeout: HTTP request timeout in seconds (default: from settings.BOLAGSVERKET_TIMEOUT)
        """
        self.base_url = (base_url or settings.BOLAGSVERKET_URL).rstrip("/")
        self.api_key = api_key or settings.BOLAGSVERKET_API_KEY
        self.rate_limit = rate_limit or settings.BOLAGSVERKET_RATE_LIMIT
        self.max_retries = max_retries or settings.BOLAGSVERKET_MAX_RETRIES
        self.timeout = timeout or settings.BOLAGSVERKET_TIMEOUT

        # Rate limiting
        self._limiter = RateLimiter(self.rate_limit)

    async def _respect_rate_limit(self) -> None:
        """
        Enforce minimum interval between requests to respect rate limit.

        Uses shared RateLimiter for consistency with other clients.
        """
        await self._limiter.acquire()

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP request headers, including auth if API key is configured."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _extract_structured(self, org: dict[str, Any]) -> dict:
        """
        Extract pipeline-friendly fields from raw Bolagsverket response.

        Args:
            org: Single organisation dict from API response

        Returns:
            Structured dict with: legal_name, address, status, representatives,
            website, registration_date, legal_form, sni_codes, raw_response
        """
        # Legal name: first FORETAGSNAMN (company name) from organisationsnamnLista
        legal_name = None
        namn_data = org.get("organisationsnamn", {})
        for namn in namn_data.get("organisationsnamnLista", []):
            namn_typ = namn.get("organisationsnamntyp", {})
            if namn_typ.get("kod") == "FORETAGSNAMN":
                legal_name = namn.get("namn")
                break
        # Fallback: use first name if no FORETAGSNAMN found
        if not legal_name and namn_data.get("organisationsnamnLista"):
            legal_name = namn_data["organisationsnamnLista"][0].get("namn")

        # Address: combine utdelningsadress, postnummer, postort
        postadress = org.get("postadressOrganisation", {}).get("postadress", {})
        address_parts = []
        if postadress.get("utdelningsadress"):
            address_parts.append(postadress["utdelningsadress"])
        if postadress.get("postnummer") and postadress.get("postort"):
            address_parts.append(f"{postadress['postnummer']} {postadress['postort']}")
        elif postadress.get("postort"):
            address_parts.append(postadress["postort"])
        address = ", ".join(address_parts) if address_parts else None

        # Status: ACTIVE if verksamOrganisation.kod == "JA", else INACTIVE
        verksam = org.get("verksamOrganisation", {}).get("kod")
        status = "ACTIVE" if verksam == "JA" else "INACTIVE"

        # Registration date
        reg_date = org.get("organisationsdatum", {}).get("registreringsdatum")

        # Legal form (e.g., "Aktiebolag", "Stiftelse")
        legal_form = org.get("organisationsform", {}).get("klartext")

        # SNI codes (industry classification) — filter out empty strings
        sni_codes = []
        for sni in org.get("naringsgrenOrganisation", {}).get("sni", []):
            kod = sni.get("kod", "").strip()
            if kod:  # Only include non-empty codes
                sni_codes.append(kod)

        return {
            "legal_name": legal_name,
            "address": address,
            "status": status,
            "representatives": [],  # Not available in free API tier (requires paid + mTLS)
            "website": None,        # NOT in Bolagsverket register — always None
            "registration_date": reg_date,
            "legal_form": legal_form,
            "sni_codes": sni_codes,
            "raw_response": org,    # Include full response for debugging/audit
        }

    async def lookup_by_orgnr(self, orgnr: str) -> dict | None:
        """
        Look up an organization by Swedish organisationsnummer (10 digits, no hyphen).

        Args:
            orgnr: 10-digit Swedish organisation number (e.g., "5560747551")

        Returns:
            Structured dict (see _extract_structured) or None if:
            - orgnr format is invalid
            - Organisation not found (404)
            - Network error after all retries exhausted

        Raises:
            httpx.HTTPStatusError: For non-404 HTTP errors after all retries
            httpx.RequestError: For network errors after all retries
        """
        # Validate orgnr format: must be exactly 10 digits
        if not orgnr or not orgnr.isdigit() or len(orgnr) != 10:
            logger.warning(f"Invalid orgnr format: {orgnr} (expected 10 digits)")
            return None

        url = f"{self.base_url}/organisationer/{orgnr}"
        headers = self._build_headers()

        # Enforce rate limit before making request
        await self._respect_rate_limit()

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                organisations = data.get("organisationer", [])
                if not organisations:
                    logger.info(f"No organisation found for orgnr: {orgnr}")
                    return None

                org = organisations[0]
                logger.info(f"Bolagsverket lookup successful for orgnr: {orgnr}")
                return self._extract_structured(org)

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 404:
                    logger.info(f"Organisation not found in Bolagsverket: {orgnr}")
                    return None  # 404 is not an error — just means not found

                if e.response.status_code == 429:
                    # Rate limited — respect Retry-After header or use exponential backoff
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = float(retry_after)
                        except (ValueError, TypeError):
                            delay = 2.0 ** attempt
                    else:
                        delay = 2.0 ** attempt

                    logger.warning(
                        f"Rate limited (429) by Bolagsverket, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Other HTTP errors (5xx, etc.) — log and retry
                logger.error(
                    f"Bolagsverket API error {e.response.status_code} for {orgnr}: {e}"
                )
                # Fall through to retry logic

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                delay = 2.0 ** attempt
                logger.warning(
                    f"Request failed ({type(e).__name__}) for {orgnr}, "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                logger.exception(
                    f"Unexpected error during Bolagsverket lookup for {orgnr}: {e}"
                )
                raise  # Re-raise unexpected exceptions immediately

        # All retries exhausted
        logger.error(
            f"All {self.max_retries + 1} attempts failed for orgnr: {orgnr}"
        )
        if last_exception is not None:
            raise last_exception
        return None
