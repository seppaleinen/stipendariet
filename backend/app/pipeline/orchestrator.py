import asyncio
import logging
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import Foundation, EnrichmentSource, EnrichmentPage, EnrichmentData
from app.pipeline.discovery import discover_candidate_urls
from app.pipeline.validation import validate_candidate_url
from app.pipeline.crawler import crawl_foundation_site
from app.pipeline.extraction import extract_data_from_content

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = ['stiftelsemedel.se', 'stiftelseansokan.se']


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
                raw_content=pc["content"],
            )
            db.add(ep)
        db.commit()


def _db_save_extraction(foundation_id: int, source_id: int, extracted_data: dict, confidence: float):
    with SessionLocal() as db:
        # Delete previous enrichment data — no history, just latest run
        db.query(EnrichmentData).filter(EnrichmentData.foundation_id == foundation_id).delete()
        ed = EnrichmentData(
            foundation_id=foundation_id,
            source_id=source_id,
            extracted_data=extracted_data,
            confidence=confidence,
        )
        db.add(ed)
        db.commit()


async def run_foundation_pipeline_task(
    ctx: dict,
    foundation_id: int,
    force_search: bool = False,
    validation_sys_prompt: str = None,
    validation_usr_prompt: str = None,
    extraction_sys_prompt: str = None,
    extraction_usr_prompt: str = None,
) -> dict:
    """
    Main task triggered by arq to process the full data extraction pipeline.

    Raises on unexpected failures so arq can retry via its max_tries setting.
    Expected non-data outcomes (NO_CANDIDATES, no_valid_site, NO_DATA) return normally.
    """
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
        "discovery": [],
        "validation": [],
        "sources": [],   # per-matched-source: pages + per-source extraction
        "merged": None,  # final merged result written to DB
    }

    # ── Discovery ──────────────────────────────────────────────────────────────
    candidates = await discover_candidate_urls(foundation_name, foundation_orgnr)
    if not candidates:
        await asyncio.to_thread(
            _db_update_foundation_status, foundation_id, "NO_CANDIDATES", datetime.utcnow()
        )
        await asyncio.to_thread(_db_save_extraction, foundation_id, None, {"_trace": trace}, 0.0)
        logger.info(f"No candidates found for: {foundation_name}")
        return {"status": "no_candidates", "trace": trace}

    trace["discovery"] = candidates
    logger.info(f"Found {len(candidates)} candidates for {foundation_name}")

    # ── Parallel validation ────────────────────────────────────────────────────
    validation_results = await asyncio.gather(*[
        validate_candidate_url(
            cand,
            foundation_name,
            foundation_orgnr,
            custom_system_prompt=validation_sys_prompt,
            custom_user_prompt=validation_usr_prompt,
        )
        for cand in candidates
    ])

    matched_candidates = []
    for cand, val in zip(candidates, validation_results):
        source_id = await asyncio.to_thread(
            _db_save_source, foundation_id, cand["url"], val["is_match"], val["confidence"]
        )
        cand["source_id"] = source_id
        trace["validation"].append({
            "url": cand["url"],
            "title": cand.get("title", ""),
            "snippet": cand.get("snippet", ""),
            "is_match": val["is_match"],
            "confidence": val["confidence"],
            "raw_llm_response": val.get("raw_llm_response"),
            "llm_error": val.get("error"),
            "prompt_used": val.get("prompt_used"),
        })
        logger.info(f"  {cand['url']} → is_match={val['is_match']} confidence={val['confidence']:.2f}")
        if val["is_match"]:
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

    # ── Per-source crawl + extraction ──────────────────────────────────────────
    aggregator_data: dict = {}
    own_site_data: dict = {}
    best_own_site_url: str | None = None
    best_aggregator_url: str | None = None

    for cand in matched_candidates:
        is_agg = _is_aggregator(cand["url"])
        logger.info(f"Crawling {'aggregator' if is_agg else 'own-site'}: {cand['url']}")

        pages_crawled = await crawl_foundation_site(cand["url"])

        source_trace: dict = {
            "url": cand["url"],
            "is_aggregator": is_agg,
            "pages": [],
            "extraction": None,
            "fields_extracted": [],
        }

        if not pages_crawled:
            logger.warning(f"Crawler returned no pages for {cand['url']} — skipping source")
            trace["sources"].append(source_trace)
            # Treat a crawler miss on a single source as transient; continue with others
            continue

        await asyncio.to_thread(_db_save_pages, cand["source_id"], pages_crawled)

        source_trace["pages"] = [
            {
                "url": pc["url"],
                "type": pc["type"],
                "size": len(pc["content"]),
                "preview": pc["content"][:500] + "..." if len(pc["content"]) > 500 else pc["content"],
            }
            for pc in pages_crawled
        ]

        # Prioritise subpages (application/contact info) over homepage boilerplate
        pages_sorted = sorted(pages_crawled, key=lambda p: 0 if p["type"] == "subpage" else 1)
        combined = "".join(
            f"\n--- PAGE: {pc['url']} ---\n{pc['content']}\n" for pc in pages_sorted
        )

        extracted = await extract_data_from_content(
            combined,
            foundation_name,
            custom_system_prompt=extraction_sys_prompt,
            custom_user_prompt=extraction_usr_prompt,
        )

        if extracted:
            extracted_dict = extracted.model_dump()
            fields_found = [k for k, v in extracted_dict.items() if v]
            source_trace["extraction"] = extracted_dict
            source_trace["fields_extracted"] = fields_found

            data = {k: v for k, v in extracted_dict.items() if v}
            if is_agg:
                aggregator_data.update(data)
                if not best_aggregator_url:
                    best_aggregator_url = cand["url"]
            else:
                own_site_data.update(data)
                if not best_own_site_url:
                    best_own_site_url = cand["url"]

            logger.info(f"  Extracted {len(fields_found)} fields from {cand['url']}: {fields_found}")
        else:
            logger.info(f"  Extraction returned null for {cand['url']}")

        trace["sources"].append(source_trace)

    # Merge: aggregator as baseline, own-site overwrites (preferred)
    merged = {**aggregator_data, **own_site_data}
    best_url = best_own_site_url or best_aggregator_url

    if not merged:
        await asyncio.to_thread(
            _db_update_foundation_status,
            foundation_id, "NO_DATA", datetime.utcnow(),
            error="All sources matched but extraction returned null",
        )
        await asyncio.to_thread(_db_save_extraction, foundation_id, None, {"_trace": trace}, 0.0)
        logger.warning(f"No data extracted from any source for {foundation_name}")
        return {"status": "no_data", "trace": trace}

    trace["merged"] = merged
    primary_source_id = matched_candidates[0].get("source_id")
    await asyncio.to_thread(
        _db_save_extraction, foundation_id, primary_source_id, {**merged, "_trace": trace}, 1.0
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
    )

    logger.info(f"Pipeline completed for {foundation_name}: {list(merged.keys())}")
    return {"status": "success", "data": merged, "trace": trace}

