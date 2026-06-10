from fastapi import APIRouter, Depends, Query

from app.core.security import get_admin_user

# Initialize router with authentication dependency (Bearer JWT admin)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])

# Import from split modules
from app.api.admin.categorization import (
    reset_categories_endpoint,
    trigger_bulk_categorization_endpoint,
)
from app.api.admin.embeddings import (
    generate_single_embedding_endpoint,
    trigger_bulk_embedding_generation_endpoint,
)
from app.api.admin.enrichment import (
    EnrichmentTestRequest,
    enrich_single_foundation_endpoint,
    get_enrichment_defaults_endpoint,
    get_enrichment_details_endpoint,
    get_enrichment_status_endpoint,
    get_enrichment_trace_endpoint,
    reset_enrichment_status_endpoint,
    trigger_enrichment_endpoint,
)
from app.api.admin.sync import (
    get_sync_status_endpoint,
    trigger_foundation_sync_endpoint,
    trigger_grant_sync_endpoint,
)
from app.api.admin.system import (
    clear_database_endpoint,
    get_active_jobs_endpoint,
    get_foundation_stats_endpoint,
    search_foundations_admin_endpoint,
)
from app.api.admin.translation import (
    get_translation_defaults_endpoint,
    get_translation_task_status_endpoint,
    translate_single_foundation_endpoint,
    trigger_bulk_purpose_translation_endpoint,
)


# --- Sync Routes ---
@router.post("/trigger-foundation-sync")
def trigger_foundation_sync():
    return trigger_foundation_sync_endpoint()

@router.get("/sync-status/{task_id}")
def get_sync_status(task_id: str):
    return get_sync_status_endpoint(task_id)

@router.post("/trigger-grant-sync")
def trigger_grant_sync():
    return trigger_grant_sync_endpoint()

# --- System Routes ---
@router.post("/reset-categories")
def reset_categories():
    return reset_categories_endpoint()

@router.post("/trigger-bulk-categorization")
def trigger_bulk_categorization():
    return trigger_bulk_categorization_endpoint()

@router.post("/clear-database")
def clear_database():
    return clear_database_endpoint()

@router.get("/foundation-stats")
def get_foundation_stats():
    return get_foundation_stats_endpoint()

@router.get("/active-jobs")
def get_active_jobs():
    return get_active_jobs_endpoint()

@router.get("/foundations/search")
def search_foundations(q: str = Query(..., min_length=3)):
    return search_foundations_admin_endpoint(q)

# --- Translation Routes ---
@router.post("/trigger-bulk-purpose-translation")
def trigger_bulk_translation(force: bool = Query(False, description="Force retranslation of all foundations")):
    return trigger_bulk_purpose_translation_endpoint(force=force)

@router.get("/bulk-translation-status/{task_id}")
def get_translation_task_status(task_id: str):
    return get_translation_task_status_endpoint(task_id)

@router.post("/translate-foundation/{foundation_id}")
def translate_foundation(
    foundation_id: int,
    model: str = Query(None, description="LLM model to use"),
    prompt: str = Query(None, description="Custom prompt template (use {purpose} as placeholder)")
):
    return translate_single_foundation_endpoint(foundation_id, model=model, custom_prompt=prompt)

@router.get("/translation-defaults")
def get_translation_defaults():
    return get_translation_defaults_endpoint()

# --- Embedding Routes ---
@router.post("/trigger-bulk-embedding-generation")
def trigger_bulk_embedding_generation():
    return trigger_bulk_embedding_generation_endpoint()

@router.post("/generate-embedding/{foundation_id}")
def generate_single_embedding(foundation_id: int):
    return generate_single_embedding_endpoint(foundation_id)

# --- Enrichment Routes ---
@router.post("/enrich/start")
async def trigger_enrichment(batch_size: int = Query(None)):
    return await trigger_enrichment_endpoint(batch_size=batch_size)

@router.get("/enrich/status")
def get_enrichment_status():
    return get_enrichment_status_endpoint()

@router.post("/enrich/reset")
def reset_enrichment_status():
    return reset_enrichment_status_endpoint()

@router.post("/enrich/foundation/{foundation_id}")
async def enrich_single_foundation(
    foundation_id: int,
    request: EnrichmentTestRequest,
    background: bool = Query(True, description="Run in background worker (default: True)")
):
    return await enrich_single_foundation_endpoint(
        foundation_id,
        background=background,
        force_search=request.force_search,
        validation_sys_prompt=request.validation_sys_prompt,
        validation_usr_prompt=request.validation_usr_prompt,
        extraction_sys_prompt=request.extraction_sys_prompt,
        extraction_usr_prompt=request.extraction_usr_prompt
    )

@router.get("/enrich/details")
def get_enrichment_details(limit: int = Query(20), status: str = Query(None)):
    return get_enrichment_details_endpoint(limit=limit, status_filter=status)

@router.get("/enrich/defaults")
def get_enrichment_defaults():
    return get_enrichment_defaults_endpoint()

@router.get("/enrich/trace/{foundation_id}")
def get_enrichment_trace(foundation_id: int):
    return get_enrichment_trace_endpoint(foundation_id)
