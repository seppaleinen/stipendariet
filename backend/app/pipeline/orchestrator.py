import asyncio
import logging
from datetime import datetime

from pydantic import ValidationError

from app.db.database import SessionLocal
from app.db.models import EnrichmentData, EnrichmentPage, EnrichmentSource, Foundation
from app.pipeline.base import PipelineContext, PipelineStage
from app.pipeline.bolagsverket import BolagsverketStage
from app.pipeline.crawler import CrawlStage
from app.pipeline.discovery import DiscoveryStage, _searxng_search, generate_targeted_query
from app.pipeline.extraction import (
    ExtractedFoundationData,
    ExtractionStage,
    merge_extractions,
    merge_missing_only,
)
from app.pipeline.service_area import ServiceAreaStage
from app.pipeline.validation import UrlValidationStage, validate_candidate_url

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = ['stiftelsemedel.se', 'stiftelseansokan.se']

# Phase 6: required content fields + re-search budget
REQUIRED_FIELDS = (
    "contact_email", "contact_phone", "application_open", "application_deadline",
    "who_can_apply", "how_to_apply", "notes", "enriched_description",
)
MAX_RESEARCH_ITERATIONS = 2
RESEARCH_SOURCES_PER_ITERATION = 3



def _is_aggregator(url: str) -> bool:
    return any(d in url.lower() for d in AGGREGATOR_DOMAINS)


def _db_fetch_foundation(foundation_id: int):
    with SessionLocal() as db:
        return db.query(Foundation).filter(Foundation.id == foundation_id).first()


def _db_update_foundation_status(
    foundation_id: int,
    status: str,
    last_run: datetime = None,
    error: str = None,
    website_url: str = None,
    deadline: str = None,
    start: str = None,
    method: str = None,
    email: str = None,
    phone: str = None,
    who: str = None,
    notes: str = None,
    enriched_description: str = None,
):
    with SessionLocal() as db:
        foundation = db.query(Foundation).filter(Foundation.id == foundation_id).first()
        if foundation:
            foundation.enrichment_status = status
            if last_run:
                foundation.enrichment_last_run = last_run
            if error is not None:
                foundation.enrichment_error = error
            if website_url is not None:
                foundation.website_url = website_url
            if deadline is not None:
                foundation.application_deadline = deadline
            if start is not None:
                foundation.application_start = start
            if method is not None:
                foundation.application_method = method
            if email is not None:
                foundation.contact_email = email
            if phone is not None:
                foundation.contact_phone = phone
            if who is not None:
                foundation.who_can_apply = who
            if notes is not None:
                foundation.enrichment_notes = notes
            if enriched_description is not None:
                foundation.enriched_description = enriched_description
            db.commit()


def _db_save_source(foundation_id: int, url: str, is_match: bool, confidence: float) -> int:
    with SessionLocal() as db:
        source = EnrichmentSource(
            foundation_id=foundation_id,
            url=url,
            is_official=is_match,
            confidence=confidence,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source.id


def _db_save_pages(source_id: int, pages: list):
    with SessionLocal() as db:
        for pc in pages:
            ep = EnrichmentPage(
                source_id=source_id,
                url=pc["url"],
                page_type=pc["type"],
                raw_content=pc["markdown"] if "markdown" in pc else pc.get("content", ""),
            )
            db.add(ep)
        db.commit()


def _db_save_extraction(foundation_id: int, source_id: int, extracted_data: dict, confidence: float, source_url: str | None = None):
    with SessionLocal() as db:
        # Delete previous enrichment data — no history, just latest run
        db.query(EnrichmentData).filter(EnrichmentData.foundation_id == foundation_id).delete()
        ed = EnrichmentData(
            foundation_id=foundation_id,
            source_id=source_id,
            extracted_data=extracted_data,
            confidence=confidence,
            source_url=source_url,
        )
        db.add(ed)
        db.commit()


def _db_save_parsed_service_area(
    foundation_id: int,
    parsed_service_area: dict,
    service_area_status: str | None = None,
):
    with SessionLocal() as db:
        foundation = db.query(Foundation).filter(Foundation.id == foundation_id).first()
        if foundation:
            save_dict = {k: v for k, v in parsed_service_area.items() if k != "service_area_status"}
            foundation.parsed_service_area = save_dict
            foundation.service_area_status = service_area_status
            db.commit()


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


async def run_foundation_pipeline_task(
    ctx: dict,
    foundation_id: int,
    force_search: bool = False,
    validation_sys_prompt: str = None,
    validation_usr_prompt: str = None,
    extraction_sys_prompt: str = None,
    extraction_usr_prompt: str = None,
    stages: dict = None,
) -> dict:
    """
    Main task triggered by arq to process the full data extraction pipeline.

    Raises on unexpected failures so arq can retry via its max_tries setting.
    Expected non-data outcomes (NO_CANDIDATES, no_valid_site, NO_DATA) return normally.
    """
    if stages is None:
        stages = _get_default_stages()
    else:
        for key, stage in stages.items():
            if not isinstance(stage, PipelineStage):
                raise TypeError(
                    f"stages['{key}'] must be a PipelineStage instance, "
                    f"got {type(stage).__name__}"
                )
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

    foundation = await asyncio.to_thread(_db_fetch_foundation, foundation_id)
    if not foundation:
        raise ValueError(f"Foundation {foundation_id} not found")

    foundation_name = foundation.name
    foundation_orgnr = foundation.orgnr

    await asyncio.to_thread(_db_update_foundation_status, foundation_id, "PROCESSING", datetime.utcnow())
    logger.info(f"Starting pipeline for foundation: {foundation_name}")

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
    if pctx.parsed_service_area:
        await asyncio.to_thread(
            _db_save_parsed_service_area,
            foundation_id,
            pctx.parsed_service_area,
            pctx.service_area_status,
        )
        trace["service_area"] = pctx.parsed_service_area
        logger.info(f"Service area extracted for {foundation_name}: {pctx.parsed_service_area}")

    # ── Discovery ──────────────────────────────────────────────────────────────
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

    # ── Parallel validation ────────────────────────────────────────────────────
    await stages["validation"].run(pctx)

    matched_candidates = []
    for cand in pctx.validated_sources:
        source_id = await asyncio.to_thread(
            _db_save_source, foundation_id, cand["url"], cand["is_match"], cand["confidence"]
        )
        cand["source_id"] = source_id
        trace["validation"].append({
            "url": cand["url"],
            "title": cand.get("title", ""),
            "snippet": cand.get("snippet", ""),
            "is_match": cand["is_match"],
            "confidence": cand["confidence"],
            "raw_llm_response": cand.get("raw_llm_response"),
            "llm_error": cand.get("error"),
            "prompt_used": cand.get("prompt_used"),
        })
        logger.info(f"  {cand['url']} → is_match={cand['is_match']} confidence={cand['confidence']:.2f}")
        if cand["is_match"]:
            matched_candidates.append(cand)

    if not matched_candidates:
        await asyncio.to_thread(
            _db_update_foundation_status, foundation_id, "no_valid_site", datetime.utcnow()
        )
        await asyncio.to_thread(_db_save_extraction, foundation_id, None, {"_trace": trace}, 0.0)
        logger.info(f"No valid site found for: {foundation_name}")
        return {"status": "no_valid_site", "trace": trace}

    # Sort: own-site first, aggregators last so own-site data takes priority in merge
    matched_candidates.sort(key=lambda c: 1 if _is_aggregator(c["url"]) else 0)

    # Cost control: limit to top 5 validated sources
    MAX_SOURCES_PER_PIPELINE = 5
    sources_to_process = matched_candidates[:MAX_SOURCES_PER_PIPELINE]
    if len(sources_to_process) < len(matched_candidates):
        logger.info(
            f"Limiting extraction to top {len(sources_to_process)} of {len(matched_candidates)} "
            f"validated sources (cost control)"
        )

    # Content fields for filtering/building merged dict
    CONTENT_FIELDS = (
        "contact_email", "contact_phone", "application_open", "application_deadline",
        "who_can_apply", "how_to_apply", "notes", "enriched_description",
    )

    # ── Per-source crawl + extraction ──────────────────────────────────────────
    extractions: list[tuple[ExtractedFoundationData, str]] = []  # (ExtractedFoundationData, source_url)
    best_own_site_url: str | None = None
    best_aggregator_url: str | None = None

    for cand in sources_to_process:
        is_agg = _is_aggregator(cand["url"])
        logger.info(f"Crawling {'aggregator' if is_agg else 'own-site'}: {cand['url']}")

        pctx.active_source = cand
        await stages["crawl"].run(pctx)

        source_trace: dict = {
            "url": cand["url"],
            "is_aggregator": is_agg,
            "pages": [],
            "extraction": None,
            "fields_extracted": [],
        }

        if not pctx.crawled_pages:
            logger.warning(f"Crawler returned no pages for {cand['url']} — skipping source")
            trace["sources"].append(source_trace)
            # Treat a crawler miss on a single source as transient; continue with others
            continue

        await asyncio.to_thread(_db_save_pages, cand["source_id"], pctx.crawled_pages)

        source_trace["pages"] = [
            {
                "url": pc["url"],
                "type": pc["type"],
                "size": len(pc.get("markdown", pc.get("content", ""))),
                "preview": (pc.get("markdown", pc.get("content", ""))[:500] + "..."
                           if len(pc.get("markdown", pc.get("content", ""))) > 500
                           else pc.get("markdown", pc.get("content", ""))),
            }
            for pc in pctx.crawled_pages
        ]

        # Run extraction stage per source (populates pctx.extracted_data)
        await stages["extraction"].run(pctx)

        if pctx.extracted_data:
            # Rehydrate ExtractedFoundationData from dict (handles both real and stub output)
            try:
                extracted = ExtractedFoundationData(**pctx.extracted_data)
            except ValidationError:
                logger.warning(f"Failed to rehydrate extracted data for {cand['url']}")
                extracted = None

            if extracted:
                fields_found = [
                    k for k, v in pctx.extracted_data.items()
                    if v is not None and k in CONTENT_FIELDS
                ]
                source_trace["extraction"] = pctx.extracted_data
                source_trace["fields_extracted"] = fields_found

                # Track best URL per category (for fallback website_url)
                if is_agg:
                    if not best_aggregator_url and fields_found:
                        best_aggregator_url = cand["url"]
                else:
                    if not best_own_site_url and fields_found:
                        best_own_site_url = cand["url"]

                logger.info(f"  Extracted {len(fields_found)} fields from {cand['url']}: {fields_found}")
                extractions.append((extracted, cand["url"]))
            else:
                logger.info(f"  Extraction returned null for {cand['url']}")
        else:
            logger.info(f"  Extraction returned null for {cand['url']}")

        trace["sources"].append(source_trace)

    # Merge extractions using highest-confidence-wins per field
    merged_extraction = merge_extractions(extractions)

    # Build plain dict of only the content fields for DB/storage (omit None)
    merged = {f: v for f in CONTENT_FIELDS if (v := getattr(merged_extraction, f)) is not None}
    best_url = best_own_site_url or best_aggregator_url

    if not any(merged.values()):
        await asyncio.to_thread(
            _db_update_foundation_status,
            foundation_id, "NO_DATA", datetime.utcnow(),
            error="All sources matched but extraction returned null",
        )
        await asyncio.to_thread(_db_save_extraction, foundation_id, None, {"_trace": trace}, 0.0)
        logger.warning(f"No data extracted from any source for {foundation_name}")
        return {"status": "no_data", "trace": trace}

    # ── Phase 6: Targeted Re-Search for Missing Fields ─────────────────────────
    # Gap analysis: identify which REQUIRED_FIELDS are still missing
    pctx.missing_fields = [f for f in REQUIRED_FIELDS if not getattr(merged_extraction, f, None)]
    trace["re_search"] = []

    while pctx.missing_fields and pctx.re_search_iterations < MAX_RESEARCH_ITERATIONS:
        pctx.re_search_iterations += 1
        iteration = pctx.re_search_iterations
        logger.info(
            f"Phase 6 re-search iteration {iteration}/{MAX_RESEARCH_ITERATIONS}: "
            f"targeting {len(pctx.missing_fields)} missing fields: {pctx.missing_fields}"
        )

        # Generate targeted queries for each missing field
        targeted_queries = [
            generate_targeted_query(field, foundation_name)
            for field in pctx.missing_fields
        ]
        logger.info(f"  Targeted queries: {targeted_queries}")

        # Run Discovery with targeted queries (skip Stages 0-1, reuse validated pipeline)
        targeted_candidates: list[dict] = []
        for query in targeted_queries:
            logger.info(f"  Running targeted discovery: {query}")
            results = await _searxng_search(query, max_results=5)
            for r in results:
                url = r.get("url", "")
                if url and url not in {c["url"] for c in pctx.candidate_urls}:
                    targeted_candidates.append({
                        "url": url,
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "strategy": f"targeted_{iteration}",
                    })

        if not targeted_candidates:
            logger.info("  No new candidates from targeted queries — stopping re-search")
            break

        # Validate targeted candidates
        logger.info(f"  Validating {len(targeted_candidates)} targeted candidates")
        validated_targeted: list[dict] = []
        for cand in targeted_candidates:
            val = await validate_candidate_url(
                cand,
                foundation_name,
                foundation_orgnr or "",
                custom_system_prompt=validation_sys_prompt,
                custom_user_prompt=validation_usr_prompt,
            )
            cand_with_validation = {**cand, **val}
            if val["is_match"]:
                validated_targeted.append(cand_with_validation)

        if not validated_targeted:
            logger.info("  No validated targeted candidates — stopping re-search")
            break

        # Limit sources for cost control
        sources_to_crawl = validated_targeted[:RESEARCH_SOURCES_PER_ITERATION]
        logger.info(f"  Crawling {len(sources_to_crawl)} targeted sources")

        # Crawl + extract from targeted sources
        targeted_extractions: list[tuple[ExtractedFoundationData, str]] = []
        for cand in sources_to_crawl:
            is_agg = _is_aggregator(cand["url"])
            logger.info(f"  Crawling targeted {'aggregator' if is_agg else 'own-site'}: {cand['url']}")

            pctx.active_source = cand
            await stages["crawl"].run(pctx)

            if not pctx.crawled_pages:
                logger.warning(f"  Crawler returned no pages for targeted {cand['url']} — skipping")
                continue

            await stages["extraction"].run(pctx)

            if pctx.extracted_data:
                try:
                    extracted = ExtractedFoundationData(**pctx.extracted_data)
                    fields_found = [
                        k for k, v in pctx.extracted_data.items()
                        if v is not None and k in CONTENT_FIELDS
                    ]
                    if fields_found:
                        logger.info(f"    Extracted {len(fields_found)} fields: {fields_found}")
                        targeted_extractions.append((extracted, cand["url"]))
                except ValidationError:
                    logger.warning(f"  Failed to rehydrate targeted extraction for {cand['url']}")

        if not targeted_extractions:
            logger.info("  No data extracted from targeted sources — stopping re-search")
            break

        # Merge ONLY missing fields (don't overwrite existing high-confidence values)
        merged_extraction = merge_missing_only(
            merged_extraction,
            targeted_extractions,
            target_fields=pctx.missing_fields,
        )

        # Update merged dict and trace
        merged = {f: v for f in CONTENT_FIELDS if (v := getattr(merged_extraction, f)) is not None}
        trace["re_search"].append({
            "iteration": iteration,
            "queries": targeted_queries,
            "sources_crawled": [c["url"] for c in sources_to_crawl],
            "extractions_count": len(targeted_extractions),
            "fields_filled": [
                f for f in REQUIRED_FIELDS
                if getattr(merged_extraction, f, None) is not None and f in pctx.missing_fields
            ],
        })

        # Re-calculate missing fields for next iteration
        pctx.missing_fields = [f for f in REQUIRED_FIELDS if not getattr(merged_extraction, f, None)]
        logger.info(f"  After iteration {iteration}: {len(pctx.missing_fields)} fields still missing")

    # End Phase 6 re-search loop ────────────────────────────────────────────────

    # Include confidence and audit trail in trace
    trace["merged"] = merged_extraction.model_dump()
    primary_source_id = matched_candidates[0].get("source_id")
    await asyncio.to_thread(
        _db_save_extraction, foundation_id, primary_source_id, {**merged, "_trace": trace},
        merged_extraction.confidence, best_url
    )
    await asyncio.to_thread(
        _db_update_foundation_status,
        foundation_id,
        "COMPLETED",
        last_run=datetime.utcnow(),
        website_url=best_url,
        deadline=merged.get("application_deadline"),
        start=merged.get("application_open"),
        method=merged.get("how_to_apply"),
        email=merged.get("contact_email"),
        phone=merged.get("contact_phone"),
        who=merged.get("who_can_apply"),
        notes=merged.get("notes"),
        enriched_description=merged.get("enriched_description"),
    )

    logger.info(
        f"Pipeline completed for {foundation_name}: {len(merged)} fields, "
        f"re_search_iterations={pctx.re_search_iterations}, "
        f"missing_fields={len(pctx.missing_fields)}"
    )
    return {"status": "success", "data": merged, "trace": trace}

