import json
import logging
from collections import defaultdict

from pydantic import BaseModel, ValidationError

from app.pipeline.base import PipelineContext, PipelineStage
from app.pipeline.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.services.llm_client import chat_completion, strip_code_fences

logger = logging.getLogger(__name__)


def _format_prompt(template: str, **kwargs) -> str:
    """Format a prompt template, tolerating placeholders that are not provided.

    Prompts evolved (e.g. EXTRACTION_USER_PROMPT gained a {url} placeholder),
    so legacy call sites that only pass some of the keys must not crash with
    KeyError. Missing placeholders are substituted with an empty string.
    """
    return template.format_map(defaultdict(str, **kwargs))


class ExtractedFoundationData(BaseModel):
    contact_email: str | None = None
    contact_phone: str | None = None
    application_open: str | None = None
    application_deadline: str | None = None
    who_can_apply: str | None = None
    how_to_apply: str | None = None
    notes: str | None = None
    enriched_description: str | None = None  # 150+ word Swedish description for LLM citation
    confidence: float = 0.0
    per_field_confidence: dict[str, float] = {}
    source_per_field: dict[str, str] = {}  # Maps field name to the source URL that contributed it




def _parse_extraction_response(
    data: dict,
    foundation_name: str,
) -> ExtractedFoundationData | None:
    """
    Parse LLM extraction response, supporting both flat and nested formats.
    
    Flat format (legacy): {"contact_email": "email@example.com", ...}
    Nested format (new): {"contact_email": {"value": "email@example.com", "confidence": 0.9}, ...}
    
    Returns ExtractedFoundationData with confidence scores populated for nested format.
    """
    # Detect format by checking if any known field has nested structure
    known_fields = ExtractedFoundationData.model_fields.keys()
    
    # Check if we have nested format (any field is a dict with value/confidence)
    is_nested = False
    for k, v in data.items():
        if k in known_fields and isinstance(v, dict) and "value" in v:
            is_nested = True
            break
    
    if is_nested:
        # Parse nested format
        field_values = {}
        confidences = {}
        
        for k, v in data.items():
            if k not in known_fields:
                continue
            if isinstance(v, dict) and "value" in v:
                field_values[k] = v.get("value")
                conf = v.get("confidence", 0.0)
                if isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0:
                    confidences[k] = float(conf)
                else:
                    confidences[k] = 0.0
            else:
                # Fallback: treat as flat value with 0.0 confidence
                field_values[k] = v
                confidences[k] = 0.0
        
        # Calculate average confidence for non-null fields
        non_null_confidences = [
            conf for field, conf in confidences.items()
            if field_values.get(field) is not None
        ]
        avg_confidence = sum(non_null_confidences) / len(non_null_confidences) if non_null_confidences else 0.0
        
        # Check if we got anything useful
        values = [v for v in field_values.values() if v]
        if not values:
            logger.warning(f"Extraction returned all-null result for {foundation_name}")
            return None
        
        extracted = ExtractedFoundationData(
            **field_values,
            confidence=avg_confidence,
            per_field_confidence={k: v for k, v in confidences.items() if field_values.get(k) is not None},
        )
        logger.info(f"Extracted {len(values)} fields for {foundation_name} (nested format): {field_values}")
        return extracted
    else:
        # Parse flat format (legacy)
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        extracted = ExtractedFoundationData(**filtered_data)
        
        # Check if we actually got anything useful
        values = [v for v in filtered_data.values() if v]
        if not values:
            logger.warning(f"Extraction returned all-null result for {foundation_name}")
            return None
        
        logger.info(f"Extracted {len(values)} fields for {foundation_name} (flat format): {filtered_data}")
        return extracted


async def extract_data_from_content(
    content: str,
    foundation_name: str,
    custom_system_prompt: str = None,
    custom_user_prompt: str = None
) -> ExtractedFoundationData | None:
    if len(content) > 6000:
        content = content[:6000] + "..."

    sys_prompt = custom_system_prompt or EXTRACTION_SYSTEM_PROMPT
    usr_prompt = custom_user_prompt or EXTRACTION_USER_PROMPT

    prompt = _format_prompt(sys_prompt, foundation_name=foundation_name) + "\n" + _format_prompt(usr_prompt, content=content)

    try:
        raw_response = chat_completion(prompt, temperature=0.1)
        if raw_response:
            logger.info(f"Extraction LLM raw response for {foundation_name}: {raw_response}")
            data = json.loads(strip_code_fences(raw_response))
            return _parse_extraction_response(data, foundation_name)

    except json.JSONDecodeError as e:
        logger.error(f"Extraction LLM returned invalid JSON for {foundation_name}: {e}")
    except ValidationError as e:
        logger.error(f"Extraction data failed validation for {foundation_name}: {e}")
    except Exception as e:
        logger.error(f"Extraction LLM failed for {foundation_name}: {e}")

    return None


async def extract_from_source(
    content: str,
    url: str,
    foundation_name: str,
    custom_system_prompt: str | None = None,
    custom_user_prompt: str | None = None,
) -> ExtractedFoundationData | None:
    """
    Extract data from a single source with field-level confidence scores.
    
    Args:
        content: The text content to extract from
        url: The source URL (used in prompt and tracking)
        foundation_name: Name of the foundation
        custom_system_prompt: Optional override for system prompt
        custom_user_prompt: Optional override for user prompt
    
    Returns:
        ExtractedFoundationData with confidence scores, or None if extraction failed
    """
    if len(content) > 6000:
        content = content[:6000] + "..."

    sys_prompt = custom_system_prompt or EXTRACTION_SYSTEM_PROMPT
    usr_prompt = custom_user_prompt or EXTRACTION_USER_PROMPT

    # Use the new nested format prompt that includes URL
    prompt = sys_prompt.format(foundation_name=foundation_name) + "\n" + usr_prompt.format(content=content, url=url)

    try:
        raw_response = chat_completion(prompt, temperature=0.1)
        if raw_response:
            logger.info(f"Extraction LLM raw response for {foundation_name} (source: {url}): {raw_response}")
            data = json.loads(strip_code_fences(raw_response))
            
            extracted = _parse_extraction_response(data, foundation_name)
            
            if extracted:
                # Set source_per_field for all non-null fields
                for field_name, value in extracted.model_dump().items():
                    if value is not None and field_name not in ("confidence", "per_field_confidence", "source_per_field"):
                        extracted.source_per_field[field_name] = url
            
            return extracted

    except json.JSONDecodeError as e:
        logger.error(f"Extraction LLM returned invalid JSON for {foundation_name} (source: {url}): {e}")
    except ValidationError as e:
        logger.error(f"Extraction data failed validation for {foundation_name} (source: {url}): {e}")
    except Exception as e:
        logger.error(f"Extraction LLM failed for {foundation_name} (source: {url}): {e}")

    return None


def merge_extractions(
    extractions: list[tuple[ExtractedFoundationData, str]],
) -> ExtractedFoundationData:
    """
    Merge multiple extractions using highest-confidence-wins per field.
    
    Args:
        extractions: List of (ExtractedFoundationData, source_url) tuples
    
    Returns:
        Merged ExtractedFoundationData with best value per field
    """
    if not extractions:
        return ExtractedFoundationData()
    
    # Track best value and confidence per field
    field_best: dict[str, tuple[str | None, float, str]] = {}  # field -> (value, confidence, source_url)
    
    for extracted, source_url in extractions:
        for field_name in ExtractedFoundationData.model_fields.keys():
            # Skip metadata fields
            if field_name in ("confidence", "per_field_confidence", "source_per_field"):
                continue
            
            value = getattr(extracted, field_name, None)
            conf = extracted.per_field_confidence.get(field_name, 0.0)
            
            # Only consider non-null values
            if value is None:
                continue
            
            # Check if this is better than what we have
            if field_name not in field_best:
                field_best[field_name] = (value, conf, source_url)
            else:
                _, best_conf, _ = field_best[field_name]
                if conf > best_conf:
                    field_best[field_name] = (value, conf, source_url)
    
    # Build merged result
    merged_data = {}
    merged_confidences = {}
    merged_sources = {}
    
    for field_name, (value, conf, source_url) in field_best.items():
        merged_data[field_name] = value
        merged_confidences[field_name] = conf
        merged_sources[field_name] = source_url
    
    # Calculate overall confidence (average of per-field confidences)
    avg_confidence = sum(merged_confidences.values()) / len(merged_confidences) if merged_confidences else 0.0
    
    if not merged_data:
        logger.warning("merge_extractions: no fields extracted from any source")
        return ExtractedFoundationData()
    
    result = ExtractedFoundationData(
        **merged_data,
        confidence=avg_confidence,
        per_field_confidence=merged_confidences,
        source_per_field=merged_sources,
    )
    
    logger.info(
        f"Merged {len(extractions)} extractions: {len(merged_data)} fields, "
        f"avg_confidence={avg_confidence:.2f}, sources={set(merged_sources.values())}"
    )

    return result


def merge_missing_only(
    current: ExtractedFoundationData,
    new_extractions: list[tuple[ExtractedFoundationData, str]],
    target_fields: list[str] | None = None,
) -> ExtractedFoundationData:
    """
    Fill missing fields on `current` from `new_extractions` without overwriting.

    Used by the Phase 6 re-search loop: after the initial merge, targeted
    re-search produces new extractions. Only fields that are still None on
    `current` (optionally restricted to `target_fields`) are filled — existing
    values, regardless of confidence, are never replaced.

    When multiple new extractions provide the same missing field, the
    highest-confidence value wins (same rule as merge_extractions).

    Args:
        current: The merged result from the initial run (may have gaps)
        new_extractions: List of (ExtractedFoundationData, source_url) from re-search
        target_fields: Optional whitelist of fields to consider (the gap set)

    Returns:
        An updated ExtractedFoundationData (a new instance; `current` is not mutated)
    """
    if not new_extractions:
        return ExtractedFoundationData(**current.model_dump())

    content_fields = [
        f for f in ExtractedFoundationData.model_fields.keys()
        if f not in ("confidence", "per_field_confidence", "source_per_field")
    ]

    # Best candidate per missing field across the new extractions
    best_for_missing: dict[str, tuple[str, float, str]] = {}
    for extracted, source_url in new_extractions:
        for field_name in content_fields:
            if target_fields is not None and field_name not in target_fields:
                continue
            value = getattr(extracted, field_name, None)
            if value is None:
                continue
            conf = extracted.per_field_confidence.get(field_name, 0.0)
            if field_name not in best_for_missing:
                best_for_missing[field_name] = (value, conf, source_url)
            else:
                _, best_conf, _ = best_for_missing[field_name]
                if conf > best_conf:
                    best_for_missing[field_name] = (value, conf, source_url)

    # Apply only to fields still missing on current
    data = current.model_dump()
    filled: dict[str, str] = {}
    for field_name, (value, conf, source_url) in best_for_missing.items():
        if data.get(field_name) is None:
            data[field_name] = value
            filled[field_name] = f"{source_url} (conf {conf:.2f})"
            data.setdefault("per_field_confidence", {})[field_name] = conf
            data.setdefault("source_per_field", {})[field_name] = source_url

    if not filled:
        logger.info("merge_missing_only: no new fields to fill")
        return ExtractedFoundationData(**current.model_dump())

    logger.info(
        f"merge_missing_only: filled {len(filled)} missing fields: "
        f"{', '.join(sorted(filled.keys()))}"
    )
    return ExtractedFoundationData(**data)


class ExtractionStage(PipelineStage):
    """Pipeline stage for extracting data from crawled content."""
    name = "extraction"

    async def run(self, ctx: PipelineContext) -> None:
        if not ctx.crawled_pages:
            ctx.extracted_data = None
            return

        # Prioritise subpages over homepage
        pages_sorted = sorted(ctx.crawled_pages, key=lambda p: 0 if p["type"] == "subpage" else 1)
        combined = "".join(
            f"\n--- PAGE: {pc['url']} ---\n{pc.get('markdown', pc.get('content', ''))}\n"
            for pc in pages_sorted
        )

        extracted = await extract_data_from_content(
            combined,
            ctx.foundation_name,
            custom_system_prompt=ctx.extraction_sys_prompt,
            custom_user_prompt=ctx.extraction_usr_prompt,
        )

        if extracted:
            # Attributing non-null fields to the active source URL (if available)
            if ctx.active_source and ctx.active_source.get("url"):
                source_url = ctx.active_source["url"]
                for field_name in (
                    "contact_email", "contact_phone", "application_open", "application_deadline",
                    "who_can_apply", "how_to_apply", "notes", "enriched_description",
                ):
                    if getattr(extracted, field_name) is not None:
                        extracted.source_per_field[field_name] = source_url

            ctx.extracted_data = extracted.model_dump()
        else:
            ctx.extracted_data = None
