import logging

from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EnrichmentTestRequest(BaseModel):
    force_search: bool = False
    validation_sys_prompt: str | None = None
    validation_usr_prompt: str | None = None
    extraction_sys_prompt: str | None = None
    extraction_usr_prompt: str | None = None



async def trigger_enrichment_endpoint(batch_size: int = None):
    """
    Trigger enrichment for unprocessed foundations.

    Selects foundations with enrichment_status='UNPROCESSED',
    enqueues them to the Arq Redis queue, and sets their status to PENDING.

    Args:
        batch_size: Number of foundations to enqueue (default from settings)
    """
    from arq import create_pool

    try:
        from app.core.config import settings
        from app.db import models
        from app.db.database import get_db
        from app.services.enrichment_schemas import EnrichmentStatus

        batch_size = batch_size or getattr(settings, 'ENRICHMENT_BATCH_SIZE', 50)

        logger.info(f"Admin triggered enrichment for up to {batch_size} foundations")

        db = next(get_db())
        try:
            # Select unprocessed foundations
            foundations = db.query(models.Foundation).filter(
                models.Foundation.enrichment_status == EnrichmentStatus.UNPROCESSED
            ).limit(batch_size).all()

            if not foundations:
                return {
                    "status": "no_work",
                    "message": "No unprocessed foundations found",
                    "enqueued": 0
                }

            # Connect to Redis/Dragonfly
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
            # Assuming parse_redis_url from enrichment_worker is moved or simplified.
            # We can just pass the string to arq if format supported, or use RedisSettings.from_dsn
            from arq.connections import RedisSettings
            redis_settings = RedisSettings.from_dsn(redis_url)
            redis = await create_pool(redis_settings)

            # Enqueue jobs and update status
            enqueued_count = 0
            for foundation in foundations:
                try:
                    await redis.enqueue_job(
                        'run_foundation_pipeline_task',
                        foundation.id
                    )
                    foundation.enrichment_status = EnrichmentStatus.PENDING
                    enqueued_count += 1
                except Exception as e:
                    logger.error(f"Failed to enqueue foundation {foundation.id}: {e}")

            db.commit()
            await redis.close()

            return {
                "status": "success",
                "message": f"Enqueued {enqueued_count} foundations for enrichment",
                "enqueued": enqueued_count,
                "batch_size": batch_size
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error triggering enrichment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger enrichment: {str(e)}"
        )


def get_enrichment_status_endpoint():
    """
    Get statistics about foundation enrichment status.

    Returns counts for each status: UNPROCESSED, PENDING, PROCESSING, COMPLETED, FAILED.
    """
    try:
        from sqlalchemy import func

        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            # Count by enrichment status
            status_counts = db.query(
                models.Foundation.enrichment_status,
                func.count(models.Foundation.id)
            ).group_by(models.Foundation.enrichment_status).all()

            counts = {s or "UNPROCESSED": count for s, count in status_counts}

            # Get total
            total = sum(counts.values())

            # Calculate percentages
            completed = counts.get("COMPLETED", 0)
            failed = counts.get("FAILED", 0)

            return {
                "total": total,
                "counts": counts,
                "completed_percentage": round((completed / total * 100) if total > 0 else 0, 1),
                "failed_count": failed,
                "remaining": total - completed - failed
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting enrichment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get enrichment status: {str(e)}"
        )


def reset_enrichment_status_endpoint():
    """
    Reset all foundation enrichment statuses to UNPROCESSED.

    Useful for re-running the enrichment pipeline.
    """
    try:
        from app.db import models
        from app.db.database import get_db
        from app.services.enrichment_schemas import EnrichmentStatus

        logger.info("Admin triggered enrichment status reset")

        db = next(get_db())
        try:
            # Reset all statuses
            updated = db.query(models.Foundation).update({
                models.Foundation.enrichment_status: EnrichmentStatus.UNPROCESSED,
                models.Foundation.enrichment_error: None
            })
            db.commit()

            return {
                "status": "success",
                "message": f"Reset enrichment status for {updated} foundations",
                "reset_count": updated
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error resetting enrichment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset enrichment status: {str(e)}"
        )


async def enrich_single_foundation_endpoint(
    foundation_id: int,
    background: bool = True,
    force_search: bool = False,
    validation_sys_prompt: str = None,
    validation_usr_prompt: str = None,
    extraction_sys_prompt: str = None,
    extraction_usr_prompt: str = None
):
    """
    Test enrichment on a single foundation.

    If background=True (default), enqueues the job to arq and returns immediately.
    If background=False, runs the pipeline synchronously (may time out if LLM is slow).
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        from app.core.config import settings
        from app.db import models
        from app.db.database import get_db
        from app.services.enrichment_schemas import EnrichmentStatus

        if background:
            logger.info(f"Admin enqueued single enrichment for foundation ID: {foundation_id}")

            # Connect to Redis
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
            redis_settings = RedisSettings.from_dsn(redis_url)
            redis = await create_pool(redis_settings)

            try:
                # Enqueue the job with custom prompts if provided
                job = await redis.enqueue_job(
                    'run_foundation_pipeline_task',
                    foundation_id,
                    force_search=force_search,
                    validation_sys_prompt=validation_sys_prompt,
                    validation_usr_prompt=validation_usr_prompt,
                    extraction_sys_prompt=extraction_sys_prompt,
                    extraction_usr_prompt=extraction_usr_prompt
                )

                # Update status to PENDING
                db = next(get_db())
                try:
                    foundation = db.query(models.Foundation).filter(models.Foundation.id == foundation_id).first()
                    if foundation:
                        foundation.enrichment_status = EnrichmentStatus.PENDING
                        db.commit()
                finally:
                    db.close()

                return {
                    "status": "enqueued",
                    "message": f"Enrichment job for foundation {foundation_id} enqueued",
                    "job_id": job.job_id
                }
            finally:
                await redis.close()
        else:
            # Synchronous execution (for direct testing/debugging)
            from app.pipeline.orchestrator import run_foundation_pipeline_task

            logger.info(f"Admin triggered SYNCHRONOUS single enrichment for foundation ID: {foundation_id}")

            result = await run_foundation_pipeline_task(
                {},
                foundation_id,
                force_search=force_search,
                validation_sys_prompt=validation_sys_prompt,
                validation_usr_prompt=validation_usr_prompt,
                extraction_sys_prompt=extraction_sys_prompt,
                extraction_usr_prompt=extraction_usr_prompt
            )

            if result.get("status") == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Unknown pipeline error")
                )

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enriching single foundation {foundation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich foundation: {str(e)}"
        )


def get_enrichment_details_endpoint(limit: int = 20, status_filter: str = None):
    """
    Get detailed list of recent enrichment results.

    Args:
        limit: Max number of foundations to return
        status_filter: Filter by status (COMPLETED, FAILED, PENDING, PROCESSING, UNPROCESSED, NO_VALID_SITE)
    """
    try:
        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            query = db.query(models.Foundation)

            if status_filter:
                query = query.filter(models.Foundation.enrichment_status == status_filter)
            else:
                # When no filter, show all that have been touched by the pipeline (not NULL and not UNPROCESSED)
                query = query.filter(
                    models.Foundation.enrichment_status.notin_(['UNPROCESSED', None])
                )

            # Order by last run, most recent first
            foundations = query.order_by(
                models.Foundation.enrichment_last_run.desc().nullslast()
            ).limit(limit).all()

            results = []
            for f in foundations:
                results.append({
                    "id": f.id,
                    "name": f.name,
                    "status": f.enrichment_status or "UNPROCESSED",
                    "last_run": f.enrichment_last_run.isoformat() if f.enrichment_last_run else None,
                    "error": f.enrichment_error,
                    "website_url": f.website_url,
                    "application_deadline": f.application_deadline,
                    "application_start": f.application_start,
                    "application_method": f.application_method,
                    "contact_email": f.contact_email,
                    "contact_phone": f.contact_phone,
                    "who_can_apply": f.who_can_apply,
                    "enrichment_notes": f.enrichment_notes,
                })

            return {
                "count": len(results),
                "foundations": results
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting enrichment details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get enrichment details: {str(e)}"
        )


def get_enrichment_defaults_endpoint():
    """
    Get the default enrichment prompt templates.
    """
    from app.core.config import settings
    from app.pipeline.prompts import (
        EXTRACTION_SYSTEM_PROMPT,
        EXTRACTION_USER_PROMPT,
        VALIDATION_SYSTEM_PROMPT,
        VALIDATION_USER_PROMPT,
    )

    return {
        "validation_system_prompt": VALIDATION_SYSTEM_PROMPT,
        "validation_user_prompt": VALIDATION_USER_PROMPT,
        "extraction_system_prompt": EXTRACTION_SYSTEM_PROMPT,
        "extraction_user_prompt": EXTRACTION_USER_PROMPT,
        "model": getattr(settings, 'ENRICHMENT_LLM_MODEL', 'phi3:14b')
    }


def get_enrichment_trace_endpoint(foundation_id: int):
    """
    Get the stored pipeline trace for a specific foundation.
    Returns the full trace including validation LLM responses and crawler page previews.
    """
    try:
        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            # Get the most recent EnrichmentData for this foundation, which has _trace stored
            entry = (
                db.query(models.EnrichmentData)
                .filter(models.EnrichmentData.foundation_id == foundation_id)
                .order_by(models.EnrichmentData.extracted_at.desc())
                .first()
            )
            if not entry:
                raise HTTPException(status_code=404, detail="No trace found for this foundation")

            data = entry.extracted_data or {}
            trace = data.get("_trace")
            if not trace:
                raise HTTPException(status_code=404, detail="Trace not available (run enrichment first)")

            return {"foundation_id": foundation_id, "trace": trace}
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trace for foundation {foundation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trace: {str(e)}"
        )
