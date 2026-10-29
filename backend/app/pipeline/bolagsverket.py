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
