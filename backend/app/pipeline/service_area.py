"""
Service Area Extraction Pipeline Stage.

Extracts geographic service area from foundation name and purpose text
using LLM, then maps the result to Swedish municipality/county codes.
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from app.data.swedish_regions import COUNTY_LOOKUP, MUNICIPALITY_LOOKUP
from app.pipeline.prompts import SERVICE_AREA_SYSTEM_PROMPT, SERVICE_AREA_USER_PROMPT
from app.services.llm_client import chat_completion, strip_code_fences

logger = logging.getLogger(__name__)


class LLMServiceAreaResult(BaseModel):
    location_name: str | None = None
    granularity: str | None = None  # "municipality" or "county"
    service_area_detail: str | None = None  # fine-grained free text (street/neighborhood/area)


class ParsedServiceArea(BaseModel):
    municipality_code: str | None = None
    county_code: str | None = None
    municipality_name: str | None = None
    county_name: str | None = None
    source_text: str | None = None
    confidence: str | None = None  # "high", "medium", "low"
    service_area_detail: str | None = None  # fine-grained eligibility detail, preserved and displayed


def _map_location_to_codes(
    location_name: str | None,
    granularity: str | None,
) -> dict[str, Any] | None:
    """Map a location name and granularity to Swedish region codes.

    Returns a dict with codes and names, or None if no match found.
    Prefers municipality-level when granularity is "municipality".
    Falls back to county when granularity is "county" or when
    municipality lookup fails.
    """
    if not location_name:
        return None

    normalised = location_name.strip().lower()

    # Try municipality lookup first (when granularity indicates municipality)
    if granularity == "municipality":
        match = MUNICIPALITY_LOOKUP.get(normalised)
        if match:
            muni_code, county_code = match
            # Find county name from code
            county_name = None
            for name, code in COUNTY_LOOKUP.items():
                if code == county_code:
                    county_name = name
                    break
            return {
                "municipality_code": muni_code,
                "county_code": county_code,
                "municipality_name": location_name.strip(),
                "county_name": county_name.title() + " län" if county_name else None,
            }

    # Try county lookup (with and without "län" suffix)
    county_code = COUNTY_LOOKUP.get(normalised)
    if not county_code and normalised.endswith(" län"):
        # Strip "län" suffix and try again
        county_code = COUNTY_LOOKUP.get(normalised[:-4].strip())
    if county_code:
        county_name = None
        for name, code in COUNTY_LOOKUP.items():
            if code == county_code:
                county_name = name
                break
        return {
            "municipality_code": None,
            "county_code": county_code,
            "municipality_name": None,
            "county_name": county_name.title() + " län" if county_name else None,
        }

    # Fuzzy: try matching as a municipality even when granularity was county
    match = MUNICIPALITY_LOOKUP.get(normalised)
    if match:
        muni_code, county_code_fallback = match
        county_name = None
        for name, code in COUNTY_LOOKUP.items():
            if code == county_code_fallback:
                county_name = name
                break
        return {
            "municipality_code": muni_code,
            "county_code": county_code_fallback,
            "municipality_name": location_name.strip(),
            "county_name": county_name.title() + " län" if county_name else None,
        }

    return None


async def extract_service_area(
    foundation_name: str,
    purpose: str | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Extract geographic service area from foundation name and purpose.

    Uses LLM to identify location mentions, then maps them to
    Swedish municipality/county codes.

    Returns a dict suitable for storing in the parsed_service_area JSON column,
    or None if no geographic restriction was found.
    """
    # Build the text to analyse — combine available text fields
    text_parts = [foundation_name]
    if purpose:
        text_parts.append(purpose)
    if description:
        text_parts.append(description)
    combined_text = " | ".join(text_parts)

    # Truncate to avoid token limits
    if len(combined_text) > 2000:
        combined_text = combined_text[:2000] + "..."

    prompt = SERVICE_AREA_USER_PROMPT.format(
        foundation_name=foundation_name,
        purpose=combined_text,
    )

    try:
        raw_response = chat_completion(
            prompt,
            system_prompt=SERVICE_AREA_SYSTEM_PROMPT,
            temperature=0.1,
        )
        if not raw_response:
            logger.debug(f"Service area LLM returned empty for {foundation_name}")
            return None

        logger.debug(f"Service area LLM response for {foundation_name}: {raw_response}")
        data = json.loads(strip_code_fences(raw_response))

        llm_result = LLMServiceAreaResult(**data)

        if not llm_result.location_name:
            logger.debug(f"No geographic restriction found for {foundation_name}")
            return None

        # Map to codes
        codes = _map_location_to_codes(
            llm_result.location_name,
            llm_result.granularity,
        )

        if not codes:
            logger.warning(
                f"LLM identified location '{llm_result.location_name}' "
                f"but no matching code found for {foundation_name}"
            )
            return None

        result = ParsedServiceArea(
            **codes,
            source_text=llm_result.location_name,
            confidence="high" if llm_result.granularity == "municipality" else "medium",
            service_area_detail=llm_result.service_area_detail,
        )

        logger.info(
            f"Service area extracted for {foundation_name}: "
            f"{result.municipality_code or result.county_code} "
            f"({result.municipality_name or result.county_name})"
        )
        return result.model_dump()

    except json.JSONDecodeError as e:
        logger.error(f"Service area LLM returned invalid JSON for {foundation_name}: {e}")
    except ValidationError as e:
        logger.error(f"Service area data failed validation for {foundation_name}: {e}")
    except Exception as e:
        logger.error(f"Service area extraction failed for {foundation_name}: {e}")

    return None
