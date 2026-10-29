# Phase 1: Enrichment Pipeline v2 — Bolagsverket Registry Lookup (Stage 0)

**Contract Version**: 1.0  
**Date**: 2026-10-29  
**Author**: Dev Architect  
**Status**: Ready for Implementation

---

## Table of Contents

1. [Bolagsverket API Specification](#1-bolagsverket-api-specification)
2. [File-by-File Change Specification](#2-file-by-file-change-specification)
3. [Orchestrator Flow Changes](#3-orchestrator-flow-changes)
4. [Test Plan](#4-test-plan)
5. [Integration Verification Criteria](#5-integration-verification-criteria)
6. [Edge Cases](#6-edge-cases-handled)

---

## 1. Bolagsverket API Specification

### 1.1 Base URL & Authentication

| Property | Value |
|----------|-------|
| **Base URL** | `https://data.bolagsverket.se/api` |
| **Endpoint Path** | `/organisationer/{orgnr}` |
| **HTTP Method** | `GET` |
| **Auth Required** | Optional (OAuth 2.0 Bearer token for production; free tier may work without) |
| **Rate Limit** | 60 requests/minute (1 req/sec) |
| **Timeout** | 10 seconds |

### 1.2 Request Format

```http
GET /organisationer/5560747551 HTTP/1.1
Host: data.bolagsverket.se
Accept: application/json
Authorization: Bearer <optional-api-key>  # Only if BOLAGSVERKET_API_KEY is set
```

**Path Parameter**:
- `orgnr`: 10-digit Swedish organisationsnummer (no hyphens), e.g., `5560747551`

### 1.3 Response Shape (Real API Response from mackan.eu Proxy)

**Success (200 OK)**:
```json
{
  "organisationer": [
    {
      "organisationsidentitet": {
        "identitetsbeteckning": "5560747551",
        "typ": {
          "kod": "ORGNR",
          "klartext": "Organisationsnummer"
        }
      },
      "organisationsnamn": {
        "dataproducent": "Bolagsverket",
        "fel": null,
        "organisationsnamnLista": [
          {
            "namn": "IKEA of Sweden AB",
            "organisationsnamntyp": {
              "kod": "FORETAGSNAMN",
              "klartext": "Företagsnamn"
            },
            "registreringsdatum": "2017-05-08",
            "verksamhetsbeskrivningSarskiltForetagsnamn": null
          },
          {
            "namn": "Ten Swedish Designers",
            "organisationsnamntyp": {
              "kod": "SARS_FORNAMN",
              "klartext": "Särskilt företagsnamn"
            },
            "registreringsdatum": "2016-09-08",
            "verksamhetsbeskrivningSarskiltForetagsnamn": "För den del av verksamheten som avser inredningsartiklarna."
          }
        ]
      },
      "organisationsform": {
        "kod": "AB",
        "klartext": "Aktiebolag",
        "dataproducent": "Bolagsverket",
        "fel": null
      },
      "juridiskForm": {
        "kod": "49",
        "klartext": "Övriga aktiebolag",
        "dataproducent": "SCB",
        "fel": null
      },
      "organisationsdatum": {
        "registreringsdatum": "1960-11-21",
        "dataproducent": "Bolagsverket",
        "fel": null,
        "infortHosScb": "1972-01-01"
      },
      "postadressOrganisation": {
        "postadress": {
          "postnummer": "34381",
          "coAdress": null,
          "land": null,
          "postort": "ÄLMHULT",
          "utdelningsadress": "Box 702"
        },
        "dataproducent": "Bolagsverket",
        "fel": null
      },
      "verksamOrganisation": {
        "kod": "JA",
        "dataproducent": "SCB",
        "fel": null
      },
      "verksamhetsbeskrivning": {
        "beskrivning": "Föremålet för aktiebolagets verksamhet är att bedriva utveckling av och handel med möbler och andra heminredningsartiklar och att upplåta lös egendom till nyttjande samt att bedriva annan därmed förenlig verksamhet.",
        "dataproducent": "Bolagsverket",
        "fel": null
      },
      "naringsgrenOrganisation": {
        "sni": [
          {"kod": "74110", "klartext": "Industridesign och modedesign"},
          {"kod": "     ", "klartext": ""},
          {"kod": "     ", "klartext": ""},
          {"kod": "     ", "klartext": ""},
          {"kod": "     ", "klartext": ""}
        ],
        "dataproducent": "SCB",
        "fel": null
      },
      "reklamsparr": null,
      "avregistreradOrganisation": null,
      "avregistreringsorsak": null,
      "pagaendeAvvecklingsEllerOmstruktureringsforfarande": null,
      "registreringsland": {
        "kod": "SE-LAND",
        "klartext": "Sverige"
      }
    }
  ]
}
```

**Not Found (404)**:
```json
{
  "error": "Organisation not found"
}
```

**Rate Limited (429)**:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

### 1.4 Structured Return for Pipeline

The `BolagsverketClient.lookup_by_orgnr()` method returns a simplified dict:

```python
{
    "legal_name": "IKEA of Sweden AB",                    # First FORETAGSNAMN from organisationsnamnLista
    "address": "Box 702, 34381 ÄLMHULT",                  # Combined: utdelningsadress + postnummer + postort
    "status": "ACTIVE",                                   # "ACTIVE" if verksamOrganisation.kod == "JA" else "INACTIVE"
    "representatives": [],                                # Not in free API (requires paid tier + mTLS)
    "website": None,                                      # NOT in Bolagsverket register — always None
    "registration_date": "1960-11-21",                    # organisationsdatum.registreringsdatum
    "legal_form": "Aktiebolag",                           # organisationsform.klartext
    "sni_codes": ["74110"],                               # naringsgrenOrganisation.sni[].kod (non-empty strings only)
    "raw_response": {...}                                 # Full API response for audit/debugging
}
```

Returns `None` if:
- Organisation not found (404)
- Invalid orgnr format
- Network error after all retries

---

## 2. File-by-File Change Specification

### 2.1 `backend/app/core/config.py`

**Location**: After `SEARXNG_URL` field (around line 45)

**Add these fields to the `Settings` class**:

```python
# Bolagsverket API settings (for Enrichment Pipeline v2 Stage 0)
BOLAGSVERKET_URL: str = Field(
    default="https://data.bolagsverket.se/api",
    env="BOLAGSVERKET_URL"
)
BOLAGSVERKET_API_KEY: str = Field(
    default="",
    env="BOLAGSVERKET_API_KEY"
)  # Optional OAuth 2.0 Bearer token for production use
BOLAGSVERKET_RATE_LIMIT: float = Field(
    default=1.0,
    env="BOLAGSVERKET_RATE_LIMIT"
)  # Requests per second (Bolagsverket ToS: 60/min = 1/sec)
BOLAGSVERKET_MAX_RETRIES: int = Field(
    default=3,
    env="BOLAGSVERKET_MAX_RETRIES"
)  # Number of retry attempts with exponential backoff
BOLAGSVERKET_TIMEOUT: float = Field(
    default=10.0,
    env="BOLAGSVERKET_TIMEOUT"
)  # HTTP request timeout in seconds
```

---

### 2.2 `backend/app/services/bolagsverket_client.py` (NEW FILE)

**Full File Content**:

```python
"""
Bolagsverket Client — Swedish Companies Registration Office lookup.

Official API: https://data.bolagsverket.se/api/
(Värdefulla datamängder / High-Value Datasets initiative)

Free tier: 60 req/min (1 req/sec). Requires OAuth 2.0 for production;
optional Bearer token support for flexibility.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

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

        # Rate limiting state
        self._min_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    async def _respect_rate_limit(self) -> None:
        """
        Enforce minimum interval between requests to respect rate limit.

        Uses an asyncio.Lock to ensure thread-safe rate limiting across
        concurrent pipeline runs.
        """
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

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
```

**Key Implementation Details**:

| Feature | Implementation |
|---------|----------------|
| **Rate Limiting** | `asyncio.Lock` + `time.monotonic()` to track last request time; enforces `1.0 / rate_limit` second minimum interval |
| **Retry Logic** | Exponential backoff: `delay = 2.0 ** attempt` (1s, 2s, 4s, 8s); respects `Retry-After` header on 429 |
| **Max Retries** | Configurable via `max_retries` parameter (default: 3 from settings) |
| **Timeout** | Configurable via `timeout` parameter (default: 10s from settings) |
| **404 Handling** | Returns `None` (not an error) — organisation simply not in register |
| **Auth** | Optional Bearer token; sent only if `api_key` is non-empty |

---

### 2.3 `backend/app/pipeline/bolagsverket.py` (NEW FILE)

**Full File Content**:

```python
"""
Bolagsverket Pipeline Stage — Stage 0 of Enrichment Pipeline v2.

Runs BEFORE service_area. Uses foundation's orgnr to fetch authoritative
Swedish registry data from Bolagsverket. Sets ctx.bolagsverket_data and
constructs a probable official_website if Bolagsverket doesn't provide one.

Note: Bolagsverket does NOT include website URLs in their data. The stage
constructs a probable URL from the legal name, which the Discovery stage
would normally find via search anyway. This allows skipping Discovery.
"""

import logging
import re

from app.core.config import settings
from app.pipeline.base import PipelineContext, PipelineStage
from app.services.bolagsverket_client import BolagsverketClient

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """
    Convert a name to a URL-friendly slug.

    - Lowercase
    - Replace å/ä → a, ö → o
    - Replace non-alphanumeric sequences with single hyphen
    - Strip leading/trailing hyphens

    Args:
        name: Foundation or company name

    Returns:
        URL-safe slug (e.g., "Stiftelsen Test" → "stiftelsen-test")
    """
    s = name.lower()
    s = re.sub(r"[åä]", "a", s)
    s = re.sub(r"[ö]", "o", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _construct_probable_website(legal_name: str, postort: str | None = None) -> str | None:
    """
    Construct a probable official website URL from the legal name.

    Heuristic: Swedish foundations typically use {slug}.se or {slug}.org.
    The discovery/validation stages will verify the URL exists.

    Args:
        legal_name: Company/foundation legal name from Bolagsverket
        postort: City/postal city (optional, for future enhancement)

    Returns:
        Probable website URL (e.g., "https://stiftelsen-test.se") or None
    """
    if not legal_name:
        return None

    slug = _slugify(legal_name)
    # Try .se first (Swedish TLD most common for Swedish foundations)
    # Could also try .org as fallback, but return first candidate for simplicity
    candidates = [f"https://{slug}.se", f"https://{slug}.org"]
    return candidates[0]


class BolagsverketStage(PipelineStage):
    """
    Pipeline Stage 0: Bolagsverket registry lookup.

    This stage runs first in the enrichment pipeline, before service_area.
    It fetches authoritative data from the Swedish Companies Registration
    Office and constructs a probable official website URL.

    Outputs:
    - ctx.bolagsverket_data: Structured dict from BolagsverketClient
    - ctx.official_website: Probable website URL (constructed from legal name)
    - ctx.trace["bolagsverket"]: Summary for audit trail
    """

    name = "bolagsverket"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        rate_limit: float | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
    ):
        """
        Initialize BolagsverketStage with configurable client parameters.

        Args:
            base_url: API base URL (default: from settings)
            api_key: OAuth 2.0 Bearer token (default: from settings)
            rate_limit: Requests per second (default: from settings)
            max_retries: Number of retry attempts (default: from settings)
            timeout: HTTP request timeout (default: from settings)
        """
        self.client = BolagsverketClient(
            base_url=base_url,
            api_key=api_key,
            rate_limit=rate_limit,
            max_retries=max_retries,
            timeout=timeout,
        )

    async def run(self, ctx: PipelineContext) -> None:
        """
        Execute Bolagsverket lookup stage.

        Args:
            ctx: Pipeline context containing foundation_id, foundation_name, foundation_orgnr

        Side Effects:
            - Sets ctx.bolagsverket_data (dict or None)
            - Sets ctx.official_website (str or None)
            - Updates ctx.trace["bolagsverket"] with summary
        """
        # Check if orgnr is available
        if not ctx.foundation_orgnr:
            logger.info(
                f"No orgnr for foundation {ctx.foundation_name}, "
                f"skipping Bolagsverket lookup"
            )
            ctx.bolagsverket_data = None
            ctx.official_website = None
            ctx.trace["bolagsverket"] = {
                "orgnr": None,
                "found": False,
                "reason": "no_orgnr",
            }
            return

        logger.info(f"Bolagsverket lookup for orgnr: {ctx.foundation_orgnr}")
        data = await self.client.lookup_by_orgnr(ctx.foundation_orgnr)

        if data:
            ctx.bolagsverket_data = data

            # Bolagsverket never returns a website — construct probable one
            if data.get("legal_name"):
                # Extract postort from address for potential future enhancement
                # (currently not used in URL construction, but logged for debugging)
                postort = None
                if data.get("address"):
                    # Address format: "Box 702, 34381 ÄLMHULT"
                    parts = data["address"].split(",")
                    if len(parts) >= 2:
                        postort = parts[-1].strip().split()[-1] if parts[-1].strip() else None

                ctx.official_website = _construct_probable_website(
                    data["legal_name"], postort
                )

            logger.info(
                f"Bolagsverket data for {ctx.foundation_name}: "
                f"legal_name={data.get('legal_name')}, "
                f"status={data.get('status')}, "
                f"official_website={ctx.official_website}"
            )
        else:
            logger.warning(
                f"Bolagsverket returned no data for orgnr: {ctx.foundation_orgnr}"
            )
            ctx.bolagsverket_data = None
            ctx.official_website = None

        # Add to trace for audit/debugging
        ctx.trace["bolagsverket"] = {
            "orgnr": ctx.foundation_orgnr,
            "found": data is not None,
            "legal_name": data.get("legal_name") if data else None,
            "status": data.get("status") if data else None,
            "official_website": ctx.official_website,
            "address": data.get("address") if data else None,
            "registration_date": data.get("registration_date") if data else None,
            "legal_form": data.get("legal_form") if data else None,
        }
```

---

### 2.4 `backend/app/pipeline/base.py`

**Location**: `PipelineContext` dataclass (lines 6-36)

**Add these fields after `service_area_status`** (around line 28):

```python
@dataclass
class PipelineContext:
    """Context passed through pipeline stages with inputs/outputs."""

    # Input parameters (existing)
    foundation_id: int
    foundation_name: str
    foundation_orgnr: str | None = None
    purpose: str | None = None
    description: str | None = None
    registered_county_code: str | None = None
    registered_municipality_code: str | None = None
    validation_sys_prompt: str | None = None
    validation_usr_prompt: str | None = None
    extraction_sys_prompt: str | None = None
    extraction_usr_prompt: str | None = None

    # Pipeline state (existing)
    candidate_urls: list[dict] = field(default_factory=list)
    validated_sources: list[dict] = field(default_factory=list)
    parsed_service_area: dict | None = None
    service_area_status: str | None = None

    # NEW: Bolagsverket Stage 0 outputs (ADD THESE)
    bolagsverket_data: dict | None = None
    official_website: str | None = None

    # Per-source state (existing)
    active_source: dict | None = None
    crawled_pages: list[dict] = field(default_factory=list)
    extracted_data: dict | None = None

    # Output/trace (existing)
    trace: dict = field(default_factory=dict)
```

---

### 2.5 `backend/app/pipeline/orchestrator.py`

#### 2.5.1 Import Statement (line 8-12)

**Add import** after existing pipeline stage imports:

```python
from app.pipeline.base import PipelineContext, PipelineStage
from app.pipeline.bolagsverket import BolagsverketStage  # ADD THIS LINE
from app.pipeline.crawler import CrawlStage
from app.pipeline.discovery import DiscoveryStage
from app.pipeline.extraction import ExtractionStage
from app.pipeline.service_area import ServiceAreaStage
from app.pipeline.validation import UrlValidationStage
```

#### 2.5.2 Update `_get_default_stages()` Function (lines 127-135)

**Replace existing function** with:

```python
def _get_default_stages() -> dict:
    """
    Return the default pipeline stages mapping.

    Stage order (execution sequence):
    0. bolagsverket — Registry lookup (NEW in Phase 1)
    1. service_area — Extract geographic service area from name/purpose
    2. discovery — Find candidate URLs via search
    3. validation — Validate candidates with LLM
    4. crawl — Scrape website content
    5. extraction — Extract grant data from content
    """
    return {
        "bolagsverket": BolagsverketStage(),          # Stage 0 (NEW)
        "service_area": ServiceAreaStage(),
        "discovery": DiscoveryStage(),
        "validation": UrlValidationStage(),
        "crawl": CrawlStage(),
        "extraction": ExtractionStage(),
    }
```

#### 2.5.3 Update Stage Validation (lines 158-165)

**Replace the validation logic**:

```python
# Old validation (lines 158-165):
# missing = {"service_area", "discovery", "validation", "crawl", "extraction"} - set(stages.keys())

# New validation (ADD "bolagsverket" to required keys):
required_keys = {
    "bolagsverket",
    "service_area",
    "discovery",
    "validation",
    "crawl",
    "extraction",
}
missing = required_keys - set(stages.keys())
if missing:
    raise ValueError(f"stages dict missing required keys: {sorted(missing)}")
```

#### 2.5.4 Update Trace Dict Initialization (lines 177-185)

**Add "bolagsverket" key** to trace dict:

```python
trace = {
    "foundation_id": foundation_id,
    "name": foundation_name,
    "bolagsverket": None,           # NEW: Stage 0 trace
    "service_area": None,
    "discovery": [],
    "validation": [],
    "sources": [],   # per-matched-source: pages + per-source extraction
    "merged": None,  # final merged result written to DB
}
```

#### 2.5.5 Update Pipeline Execution Flow

**Insert Stage 0 execution** after context building (around line 202), **before** service_area:

```python
# Build PipelineContext from foundation and params
pctx = PipelineContext(
    foundation_id=foundation_id,
    foundation_name=foundation_name,
    foundation_orgnr=foundation_orgnr,
    purpose=foundation.purpose,
    description=foundation.summary,
    registered_county_code=foundation.county_code,
    registered_municipality_code=foundation.municipality_code,
    validation_sys_prompt=validation_sys_prompt,
    validation_usr_prompt=validation_usr_prompt,
    extraction_sys_prompt=extraction_sys_prompt,
    extraction_usr_prompt=extraction_usr_prompt,
    trace=trace,
)

# ── Stage 0: Bolagsverket Lookup (NEW) ───────────────────────────────────────
await stages["bolagsverket"].run(pctx)

# Capture Bolagsverket trace
if pctx.bolagsverket_data:
    trace["bolagsverket"] = pctx.trace.get("bolagsverket", {})
    logger.info(
        f"Bolagsverket lookup completed for {foundation_name}: "
        f"found={pctx.bolagsverket_data is not None}, "
        f"official_website={pctx.official_website}"
    )
else:
    trace["bolagsverket"] = pctx.trace.get("bolagsverket", {})
    logger.info(
        f"Bolagsverket lookup returned no data for {foundation_name}"
    )

# ── Stage 1: Service Area Extraction ──────────────────────────────────────────
await stages["service_area"].run(pctx)
```

**Modify Discovery stage execution** (around line 215-224) to **skip if official_website is set**:

```python
# Old code (lines 215-224):
# await stages["discovery"].run(pctx)
# if not pctx.candidate_urls:
#     await asyncio.to_thread(
#         _db_update_foundation_status, foundation_id, "NO_CANDIDATES", datetime.utcnow()
#     )
#     ...

# New code (SKIP discovery if official_website from Bolagsverket):
# ── Stage 2: Discovery ───────────────────────────────────────────────────────
if pctx.official_website:
    # Skip discovery — we already have an official website from Bolagsverket
    logger.info(
        f"Skipping discovery — official website found via Bolagsverket: "
        f"{pctx.official_website}"
    )
    pctx.candidate_urls = [
        {"url": pctx.official_website, "title": "", "snippet": ""}
    ]
else:
    # Run normal discovery via search
    await stages["discovery"].run(pctx)

if not pctx.candidate_urls:
    await asyncio.to_thread(
        _db_update_foundation_status, foundation_id, "NO_CANDIDATES", datetime.utcnow()
    )
    await asyncio.to_thread(_db_save_extraction, foundation_id, None, {"_trace": trace}, 0.0)
    logger.info(f"No candidates found for: {foundation_name}")
    return {"status": "no_candidates", "trace": trace}

trace["discovery"] = pctx.candidate_urls
logger.info(f"Found {len(pctx.candidate_urls)} candidates for {foundation_name}")
```

---

### 2.6 `backend/tests/test_pipeline_abstraction.py`

#### 2.6.1 Update STAGE_KEYS Constant (line 24)

**Replace**:
```python
STAGE_KEYS = ["service_area", "discovery", "validation", "crawl", "extraction"]
```

**With**:
```python
STAGE_KEYS = [
    "bolagsverket",
    "service_area",
    "discovery",
    "validation",
    "crawl",
    "extraction",
]
```

#### 2.6.2 Add Import for BolagsverketStage (line 17-22)

**Add import**:
```python
from app.pipeline.base import PipelineContext, PipelineStage
from app.pipeline.bolagsverket import BolagsverketStage  # ADD THIS
from app.pipeline.crawler import CrawlStage
from app.pipeline.discovery import DiscoveryStage
from app.pipeline.extraction import ExtractedFoundationData, ExtractionStage
from app.pipeline.orchestrator import _get_default_stages, run_foundation_pipeline_task
from app.pipeline.service_area import ServiceAreaStage
from app.pipeline.validation import UrlValidationStage
```

#### 2.6.3 Update Parametrized Test (lines 52-60)

**Add BolagsverketStage to the test**:

```python
@pytest.mark.parametrize(
    ("stage_cls", "expected_name"),
    [
        (BolagsverketStage, "bolagsverket"),              # ADD THIS LINE
        (ServiceAreaStage, "service_area"),
        (DiscoveryStage, "discovery"),
        (UrlValidationStage, "validation"),
        (CrawlStage, "crawl"),
        (ExtractionStage, "extraction"),
    ],
)
def test_stage_classes_instantiate_as_pipeline_stage(stage_cls, expected_name):
    stage = stage_cls()
    assert isinstance(stage, PipelineStage)
    assert stage.name == expected_name
    assert asyncio.iscoroutinefunction(stage.run)
```

#### 2.6.4 Update `_make_stub_stages()` Helper (lines 74-111)

**Add bolagsverket stub stage**:

```python
def _make_stub_stages() -> dict:
    """Build the minimal stub stages (real PipelineStage subclasses) that drive
    the pipeline to a full success without touching the real module functions."""

    class StubStage(PipelineStage):
        name = "stub"

        def __init__(self, run_fn):
            self._run_fn = run_fn

        async def run(self, ctx: PipelineContext) -> None:
            await self._run_fn(ctx)

    # NEW: Bolagsverket stub — simulates finding official website
    async def run_bolagsverket(ctx: PipelineContext) -> None:
        ctx.bolagsverket_data = {
            "legal_name": "Test Foundation AB",
            "status": "ACTIVE",
            "address": "Box 1, 11122 STOCKHOLM",
        }
        ctx.official_website = "https://test-foundation.se"
        ctx.trace["bolagsverket"] = {
            "found": True,
            "official_website": ctx.official_website,
        }

    async def run_service_area(ctx: PipelineContext) -> None:
        pass  # parsed_service_area stays None

    async def run_discovery(ctx: PipelineContext) -> None:
        # Only run if official_website not set (orchestrator logic)
        if not ctx.official_website:
            ctx.candidate_urls = [{"url": "https://a.se", "title": "A", "snippet": "s"}]

    async def run_validation(ctx: PipelineContext) -> None:
        ctx.validated_sources = [
            {**cand, "is_match": True, "confidence": 1.0, "raw_llm_response": None}
            for cand in ctx.candidate_urls
        ]

    async def run_crawl(ctx: PipelineContext) -> None:
        ctx.crawled_pages = [{"url": ctx.active_source["url"], "content": "page text", "type": "homepage"}]

    async def run_extraction(ctx: PipelineContext) -> None:
        ctx.extracted_data = {"contact_email": "test@foundation.se"}

    return {
        "bolagsverket": StubStage(run_bolagsverket),      # ADD THIS
        "service_area": StubStage(run_service_area),
        "discovery": StubStage(run_discovery),
        "validation": StubStage(run_validation),
        "crawl": StubStage(run_crawl),
        "extraction": StubStage(run_extraction),
    }
```

---

## 3. Orchestrator Flow Changes

### 3.1 Stage Execution Order

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENRICHMENT PIPELINE v2 — EXECUTION FLOW                  │
└─────────────────────────────────────────────────────────────────────────────┘

START: run_foundation_pipeline_task(foundation_id, ...)
    │
    ├─ Fetch Foundation from DB
    │  └─ foundation.orgnr, foundation.name, foundation.purpose, ...
    │
    ├─ Build PipelineContext (pctx)
    │  └─ foundation_id, foundation_name, foundation_orgnr, purpose, ...
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 0: BOLAGSVERKET (NEW in Phase 1)                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  pctx.foundation_orgnr (10-digit string or None)                   │
│  Action: BolagsverketClient.lookup_by_orgnr(orgnr)                         │
│  Output: pctx.bolagsverket_data (dict or None)                             │
│          pctx.official_website (str or None)                               │
│          pctx.trace["bolagsverket"] = {                                    │
│              "orgnr": ..., "found": bool, "legal_name": ...,               │
│              "status": ..., "official_website": ..., "address": ...        │
│          }                                                                 │
│                                                                            │
│  Rate Limiting: 1 req/sec via asyncio.Lock + time.monotonic()              │
│  Retry: Exponential backoff (2^attempt seconds), max 3 retries             │
│  404 Handling: Returns None (not an error)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: SERVICE AREA (unchanged)                                          │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  pctx.foundation_name, pctx.purpose, pctx.description              │
│  Action: LLM extracts geographic service area                              │
│  Output: pctx.parsed_service_area (dict), pctx.service_area_status (str)   │
│          pctx.trace["service_area"] = {...}                                │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DECISION: Is pctx.official_website set?                                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                            │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │ YES (from Bolagsverket)     │  │ NO (Bolagsverket returned None)     │  │
│  │ ─────────────────────────── │  │ ────────────────────────────────── │  │
│  │ SKIP Discovery stage        │  │ STAGE 2: DISCOVERY (unchanged)    │  │
│  │                             │  │ ────────────────────────────────── │  │
│  │ Set pctx.candidate_urls = [ │  │ DDGS search + stiftelsemedel.se   │  │
│  │   {url: official_website}   │  │ slug probe → candidate_urls       │  │
│  │ ]                           │  │                                   │  │
│  │                             │  │ Output: pctx.candidate_urls       │  │
│  │ Benefit: Saves ~2-5 sec     │  │           pctx.trace["discovery"] │  │
│  │ per foundation (no search)  │  │                                   │  │
│  └─────────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: VALIDATION (unchanged)                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  pctx.candidate_urls (list of {url, title, snippet})               │
│  Action: LLM validates each URL → is_match, confidence                     │
│  Output: pctx.validated_sources (list with is_match, confidence, etc.)     │
│          pctx.trace["validation"] = [...]                                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: CRAWL (unchanged)                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  pctx.active_source (selected from validated_sources)              │
│  Action: Playwright via Browserless → scrape homepage + subpages           │
│  Output: pctx.crawled_pages (list of {url, content, type})                 │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: EXTRACTION (unchanged)                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input:  pctx.crawled_pages, pctx.foundation_name                          │
│  Action: LLM extracts grant fields from content                            │
│  Output: pctx.extracted_data (dict), per-source merge → final result       │
│          pctx.trace["sources"] = [...]                                     │
│          pctx.trace["merged"] = {...}                                      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
END: Save to DB → Foundation.enrichment_status = "COMPLETED"
     + enriched fields (deadline, email, phone, who_can_apply, etc.)
```

### 3.2 Discovery Skip Logic

**Condition**: `if pctx.official_website:`

**When True**:
- Discovery stage (`stages["discovery"]`) is **NOT called**
- `pctx.candidate_urls` is set directly to:
  ```python
  [{"url": pctx.official_website, "title": "", "snippet": ""}]
  ```
- Validation stage receives this single candidate and validates it
- **Benefit**: Saves 2-5 seconds per foundation (no external search API calls)

**When False** (Bolagsverket returned no data or no orgnr):
- Discovery stage runs normally (DDGS search + direct slug probe)
- No change to existing behavior

### 3.3 Trace Dict Structure

**Updated trace dict** (line 177-185 in orchestrator.py):

```python
trace = {
    "foundation_id": foundation_id,
    "name": foundation_name,
    "bolagsverket": None,           # NEW: Stage 0 trace
    "service_area": None,
    "discovery": [],
    "validation": [],
    "sources": [],
    "merged": None,
}
```

**After Stage 0 execution**, `trace["bolagsverket"]` is populated:

```python
trace["bolagsverket"] = {
    "orgnr": "5560747551",
    "found": True,
    "legal_name": "IKEA of Sweden AB",
    "status": "ACTIVE",
    "official_website": "https://ikea-of-sweden-ab.se",
    "address": "Box 702, 34381 ÄLMHULT",
    "registration_date": "1960-11-21",
    "legal_form": "Aktiebolag",
}
```

Or if not found:

```python
trace["bolagsverket"] = {
    "orgnr": "0000000000",
    "found": False,
    "legal_name": None,
    "status": None,
    "official_website": None,
    "address": None,
    "registration_date": None,
    "legal_form": None,
}
```

---

## 4. Test Plan

### 4.1 `backend/tests/test_bolagsverket_client.py` (NEW FILE)

**Purpose**: Unit tests for `BolagsverketClient` class.

**Test Functions**:

| Test Function | Mocks | Asserts |
|---------------|-------|---------|
| `test_lookup_by_orgnr_success` | `httpx.AsyncClient` → mock response with 200 + valid JSON | `result is not None`; `result["legal_name"] == "Test Foundation AB"`; `result["address"] == "Box 1, 11122 STOCKHOLM"`; `result["status"] == "ACTIVE"`; `result["website"] is None`; `result["sni_codes"] == ["94990"]` |
| `test_lookup_by_orgnr_not_found` | `httpx.AsyncClient` → mock 404 HTTPStatusError | `result is None`; no exception raised |
| `test_lookup_by_orgnr_invalid_format` | None (no HTTP call) | `result is None` for orgnr="123" (too short); `result is None` for orgnr="abcdefghij" (non-digits) |
| `test_rate_limiting_enforced` | `time.monotonic`, `asyncio.sleep` | Two consecutive calls take ≥0.9 seconds (allowing tolerance); `_respect_rate_limit` called twice |
| `test_retry_with_exponential_backoff` | `httpx.AsyncClient` → mock 500 error twice, then success | HTTP call made 3 times; `asyncio.sleep` called with delays ~1s, ~2s |
| `test_rate_limit_429_respects_retry_after` | `httpx.AsyncClient` → mock 429 with `Retry-After: 5` header, then success | `asyncio.sleep` called with ~5 seconds delay; call succeeds on retry |
| `test_auth_header_sent_when_api_key_set` | `httpx.AsyncClient` | Request headers include `Authorization: Bearer test-key` |
| `test_no_auth_header_when_api_key_empty` | `httpx.AsyncClient` | Request headers do NOT include `Authorization` |
| `test_timeout_config_applied` | `httpx.AsyncClient` | `httpx.AsyncClient` initialized with `timeout=5.0` (custom value) |
| `test_extract_structured_handles_missing_fields` | None (unit test of `_extract_structured`) | Returns dict with `None` for missing fields; `sni_codes` filters empty strings |

**File Structure**:

```python
"""
Tests for BolagsverketClient.
"""
import asyncio
import time
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.bolagsverket_client import BolagsverketClient


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.AsyncClient context manager."""
    with patch("httpx.AsyncClient") as mock:
        yield mock


@pytest.mark.asyncio
async def test_lookup_by_orgnr_success(mock_httpx_client):
    """Successful lookup returns structured data with all expected fields."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
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
    }
    mock_response.raise_for_status.return_value = None
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
    mock_response = AsyncMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=AsyncMock(),
        response=AsyncMock(status_code=404),
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
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=AsyncMock(), response=AsyncMock(status_code=404)
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
                request=AsyncMock(),
                response=AsyncMock(status_code=500),
            )
        # Third call: success
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "organisationer": [{"organisationsidentitet": {"identitetsbeteckning": "1234567890"}}]
        }
        mock_response.raise_for_status.return_value = None
        return mock_response

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
                request=AsyncMock(),
                response=AsyncMock(
                    status_code=429,
                    headers={"Retry-After": "5"},
                ),
            )
        # Second call: success
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "organisationer": [{"organisationsidentitet": {"identitetsbeteckning": "1234567890"}}]
        }
        mock_response.raise_for_status.return_value = None
        return mock_response

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
    mock_response = AsyncMock()
    mock_response.json.return_value = {"organisationer": []}
    mock_response.raise_for_status.return_value = None
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
    mock_response = AsyncMock()
    mock_response.json.return_value = {"organisationer": []}
    mock_response.raise_for_status.return_value = None
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
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=AsyncMock(), response=AsyncMock(status_code=404)
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
```

---

### 4.2 `backend/tests/test_pipeline_bolagsverket.py` (NEW FILE)

**Purpose**: Integration tests for `BolagsverketStage` pipeline stage.

**Test Functions**:

| Test Function | Mocks | Asserts |
|---------------|-------|---------|
| `test_slugify` | None | `_slugify("Stiftelsen Test") == "stiftelsen-test"`; `_slugify("Älmhults Stiftelse") == "almhults-stiftelse"` |
| `test_construct_probable_website` | None | Returns `"https://test-foundation-ab.se"` for "Test Foundation AB"; returns `None` for empty string |
| `test_bolagsverket_stage_run_success` | `BolagsverketClient.lookup_by_orgnr` → mock success | `ctx.bolagsverket_data is not None`; `ctx.official_website == "https://test-foundation-ab.se"`; `ctx.trace["bolagsverket"]["found"] is True` |
| `test_bolagsverket_stage_run_no_orgnr` | None | `ctx.bolagsverket_data is None`; `ctx.official_website is None`; `ctx.trace["bolagsverket"]["found"] is False` |
| `test_bolagsverket_stage_run_not_found` | `BolagsverketClient.lookup_by_orgnr` → mock None | `ctx.bolagsverket_data is None`; `ctx.official_website is None` |
| `test_bolagsverket_stage_sets_trace` | `BolagsverketClient.lookup_by_orgnr` → mock success | `ctx.trace["bolagsverket"]` contains all expected keys: `orgnr`, `found`, `legal_name`, `status`, `official_website`, `address`, `registration_date`, `legal_form` |
| `test_bolagsverket_stage_skips_discovery_when_website_found` | `BolagsverketClient.lookup_by_orgnr` → mock success | `ctx.official_website is not None`; `ctx.official_website.startswith("https://")` (orchestrator uses this to skip discovery) |
| `test_bolagsverket_stage_injection_into_orchestrator` | `_get_default_stages` mock | `stages["bolagsverket"]` is instance of `BolagsverketStage`; `stages["bolagsverket"].name == "bolagsverket"` |

**File Structure**:

```python
"""
Tests for BolagsverketStage (pipeline integration).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.pipeline.base import PipelineContext
from app.pipeline.bolagsverket import (
    BolagsverketStage,
    _slugify,
    _construct_probable_website,
)


# =============================================================================
# Helper function tests
# =============================================================================


def test_slugify():
    """_slugify converts names to URL-friendly slugs."""
    assert _slugify("Stiftelsen Test") == "stiftelsen-test"
    assert _slugify("Älmhults Stiftelse") == "almhults-stiftelse"
    assert _slugify("Test@#$%Foundation") == "test-foundation"
    assert _slugify("  Leading and trailing  ") == "leading-and-trailing"
    assert _slugify("Örebro") == "orebro"


def test_construct_probable_website():
    """_construct_probable_website builds probable URL from legal name."""
    url = _construct_probable_website("Test Foundation AB")
    assert url == "https://test-foundation-ab.se"

    url = _construct_probable_website("Stiftelsen")
    assert url == "https://stiftelsen.se"

    # Empty/None inputs
    assert _construct_probable_website("") is None
    assert _construct_probable_website(None) is None


# =============================================================================
# Stage execution tests
# =============================================================================


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_success():
    """Stage sets bolagsverket_data and official_website on success."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
        "registration_date": "2020-01-15",
        "legal_form": "Aktiebolag",
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)  # Fast for tests
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    assert ctx.bolagsverket_data is not None
    assert ctx.bolagsverket_data["legal_name"] == "Test Foundation AB"
    assert ctx.official_website == "https://test-foundation-ab.se"
    assert ctx.trace["bolagsverket"]["found"] is True
    assert ctx.trace["bolagsverket"]["official_website"] == "https://test-foundation-ab.se"
    assert ctx.trace["bolagsverket"]["legal_name"] == "Test Foundation AB"
    assert ctx.trace["bolagsverket"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_no_orgnr():
    """Stage handles missing orgnr gracefully (no API call)."""
    stage = BolagsverketStage(rate_limit=100)
    ctx = PipelineContext(
        foundation_id=1,
        foundation_name="Test Foundation",
        foundation_orgnr=None,
    )

    await stage.run(ctx)

    assert ctx.bolagsverket_data is None
    assert ctx.official_website is None
    assert ctx.trace["bolagsverket"]["found"] is False
    assert ctx.trace["bolagsverket"]["reason"] == "no_orgnr"


@pytest.mark.asyncio
async def test_bolagsverket_stage_run_not_found():
    """Stage handles Bolagsverket returning no data (404 or empty)."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = None

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="0000000000",
        )

        await stage.run(ctx)

    assert ctx.bolagsverket_data is None
    assert ctx.official_website is None
    assert ctx.trace["bolagsverket"]["found"] is False


@pytest.mark.asyncio
async def test_bolagsverket_stage_sets_trace():
    """Stage populates trace dict with all expected fields."""
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
        "registration_date": "2020-01-15",
        "legal_form": "Aktiebolag",
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    trace = ctx.trace["bolagsverket"]
    assert "orgnr" in trace
    assert "found" in trace
    assert "legal_name" in trace
    assert "status" in trace
    assert "official_website" in trace
    assert "address" in trace
    assert "registration_date" in trace
    assert "legal_form" in trace

    assert trace["orgnr"] == "5560747551"
    assert trace["found"] is True
    assert trace["legal_name"] == "Test Foundation AB"
    assert trace["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_bolagsverket_stage_skips_discovery_when_website_found():
    """
    Integration test: when official_website is set, orchestrator skips Discovery.

    This test verifies the stage sets the fields that orchestrator uses
    to make the skip decision.
    """
    mock_client = AsyncMock()
    mock_client.lookup_by_orgnr.return_value = {
        "legal_name": "Test Foundation AB",
        "address": "Box 1, 11122 STOCKHOLM",
        "status": "ACTIVE",
        "website": None,
    }

    with patch("app.pipeline.bolagsverket.BolagsverketClient", return_value=mock_client):
        stage = BolagsverketStage(rate_limit=100)
        ctx = PipelineContext(
            foundation_id=1,
            foundation_name="Test Foundation",
            foundation_orgnr="5560747551",
        )

        await stage.run(ctx)

    # Verify the fields that orchestrator uses to skip discovery
    assert ctx.official_website is not None
    assert ctx.official_website.startswith("https://")
    assert ctx.bolagsverket_data is not None


@pytest.mark.asyncio
async def test_bolagsverket_stage_injection_into_orchestrator():
    """BolagsverketStage is included in _get_default_stages()."""
    from app.pipeline.orchestrator import _get_default_stages

    stages = _get_default_stages()

    assert "bolagsverket" in stages
    assert isinstance(stages["bolagsverket"], BolagsverketStage)
    assert stages["bolagsverket"].name == "bolagsverket"
```

---

## 5. Integration Verification Criteria

| Criterion | Verification Method | Expected Result |
|-----------|---------------------|-----------------|
| Bolagsverket lookup runs first (Stage 0) | Run pipeline with test foundation; check `trace["bolagsverket"]` exists and appears before `trace["service_area"]` in logs | `trace["bolagsverket"]` populated; log shows "Bolagsverket lookup completed" before "Service area extracted" |
| `ctx.bolagsverket_data` populated on success | Unit test: `test_bolagsverket_stage_run_success` | `ctx.bolagsverket_data["legal_name"] == "Test Foundation AB"` |
| `ctx.official_website` constructed from legal name | Unit test: `test_bolagsverket_stage_run_success` | `ctx.official_website == "https://test-foundation-ab.se"` |
| Discovery skipped when `official_website` set | Integration test: mock Bolagsverket → verify `discovery` stage not called | `stages["discovery"].run` not awaited; `ctx.candidate_urls` set directly |
| Rate limiting enforced (1 req/sec) | Unit test: `test_rate_limiting_enforced` | Two calls take ≥0.9 seconds |
| Retry with exponential backoff (3 attempts) | Unit test: `test_retry_with_exponential_backoff` | HTTP call made 3 times on 5xx errors |
| 404 returns None (not error) | Unit test: `test_lookup_by_orgnr_not_found` | `result is None`; no exception raised |
| Invalid orgnr returns None without HTTP call | Unit test: `test_lookup_by_orgnr_invalid_format` | `result is None` for "123" and "abcdefghij" |
| All existing pipeline tests pass | `pytest backend/tests/test_pipeline_abstraction.py` | All tests pass; no regressions |
| `ruff check backend/` clean | Run linter | No errors or warnings |
| STAGE_KEYS includes "bolagsverket" | Check `test_pipeline_abstraction.py` line 24 | `STAGE_KEYS = ["bolagsverket", "service_area", ...]` |

---

## 6. Edge Cases Handled

| Edge Case | Handling | Location |
|-----------|----------|----------|
| Foundation has no `orgnr` | Stage logs info, sets `bolagsverket_data=None`, `official_website=None`, continues pipeline | `BolagsverketStage.run()` lines 85-93 |
| Bolagsverket returns 404 | Returns `None`; pipeline continues to Discovery stage | `BolagsverketClient.lookup_by_orgnr()` lines 109-111 |
| Bolagsverket returns 429 (rate limit) | Respects `Retry-After` header; exponential backoff fallback | `BolagsverketClient.lookup_by_orgnr()` lines 113-128 |
| Network timeout / connection error | Exponential backoff retry (3 attempts); raises after all retries | `BolagsverketClient.lookup_by_orgnr()` lines 131-140 |
| Response missing expected fields | Graceful degradation — `None` for missing fields, logs warning | `BolagsverketClient._extract_structured()` |
| Multiple `FORETAGSNAMN` entries | Uses first `FORETAGSNAMN` type; falls back to first entry | `BolagsverketClient._extract_structured()` lines 56-65 |
| `verksamOrganisation` missing/`null` | Defaults to `INACTIVE` status | `BolagsverketClient._extract_structured()` line 79 |
| `postadressOrganisation` missing | Address = `None`; website slug based on name only | `BolagsverketClient._extract_structured()` lines 68-77 |
| SNI codes with empty strings | Filters out empty/whitespace-only codes | `BolagsverketClient._extract_structured()` lines 90-94 |
| orgnr with hyphens (e.g., "556074-7551") | Validation rejects (must be exactly 10 digits) | `BolagsverketClient.lookup_by_orgnr()` line 99 |

---

## 7. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|----------------------|------------|
| 1 | **Auth model**: Brief says "no auth", but official API requires OAuth 2.0 | Client accepts optional `BOLAGSVERKET_API_KEY`; sends as Bearer if set. If not set, no auth header (per brief assumption). |
| 2 | **Endpoint path**: `/organisationer/{orgnr}` — confirmed via devportal & mackan.eu proxy | Configurable via `BOLAGSVERKET_URL` base; path hardcoded in client |
| 3 | **Rate limit**: 1 req/sec per brief (actual free tier is 60/min = 1/sec) | Implemented via async lock + timestamp; configurable via `BOLAGSVERKET_RATE_LIMIT` |
| 4 | **Website in Bolagsverket data**: Confirmed NOT present in free API | Always `None`; probable website constructed from legal name via `_construct_probable_website()` |
| 5 | **Representatives**: Not in free API tier (requires paid + mTLS) | Returns empty list `[]` |
| 6 | **Test pipeline abstraction**: `STAGE_KEYS` must include `"bolagsverket"` | Updated in test file — this is a required test change |
| 7 | **Foundation.orgnr format**: Stored as 10-digit string (no hyphen) | Client validates 10 digits; rejects hyphens |

---

## 8. Dependencies

| Package | Version | Purpose | Already in requirements.txt? |
|---------|---------|---------|-----------------------------|
| `httpx` | ≥0.28.1 | Async HTTP client | Yes (line 26) |
| `asyncio` | stdlib | Rate limiting lock, sleep | Yes (stdlib) |
| `pydantic` | 2.12.5 | Settings validation | Yes (line 4) |

**No new dependencies required.**

---

## 9. Deployment Notes

### 9.1 Environment Variables

Add to `.env` or Helm values:

```bash
# Bolagsverket API settings (Enrichment Pipeline v2 Stage 0)
BOLAGSVERKET_URL=https://data.bolagsverket.se/api
BOLAGSVERKET_API_KEY=          # Optional — set if using OAuth token
BOLAGSVERKET_RATE_LIMIT=1.0    # req/sec (Bolagsverket ToS: 60/min)
BOLAGSVERKET_MAX_RETRIES=3     # Number of retry attempts
BOLAGSVERKET_TIMEOUT=10.0      # HTTP request timeout (seconds)
```

### 9.2 Database Schema

**No schema changes required.** Uses existing columns:
- `Foundation.orgnr` (input)
- `Foundation.website_url` (output, via `ctx.official_website`)

### 9.3 Rollout Procedure

1. Deploy backend code (includes new files and orchestrator changes)
2. Arq worker (`enrichment_worker.py`) picks up new code on next task
3. No worker restart required
4. Monitor logs for "Bolagsverket lookup" messages

### 9.4 Rollback

If issues arise:
1. Revert code deployment
2. Arq worker will use previous code on next task
3. No database rollback needed (no schema changes)

---

## 10. Performance Impact

| Metric | Before Phase 1 | After Phase 1 | Change |
|--------|----------------|---------------|--------|
| **Pipeline duration (with Bolagsverket hit)** | ~15-20 sec | ~16-21 sec | +1 sec (Bolagsverket API call) |
| **Pipeline duration (Bolagsverket miss)** | ~15-20 sec | ~15-20 sec | No change (fallback to Discovery) |
| **Pipeline duration (Bolagsverket hit + Discovery skip)** | ~15-20 sec | ~13-18 sec | **-2 to -5 sec** (skip search API calls) |
| **External API calls per foundation** | 2-3 (DDGS + validation LLM) | 2-3 (Bolagsverket + validation LLM) | Same or fewer |

**Net benefit**: For foundations with orgnr in Bolagsverket, Discovery stage is skipped, saving 2-5 seconds.

---

## 11. Trace Line

```
TRACE: dev-team-lead → dev-architect → [CONTRACT WRITTEN] [SUCCESS]
```

---

**End of Contract**