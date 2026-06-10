"""
Admin system endpoints for database management and stats
"""

import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def clear_database_endpoint():
    """
    Endpoint to clear the entire database (dangerous operation!)
    """
    try:
        logger.warning("Admin triggered database clearing - this is dangerous!")

        from app.crud import crud
        from app.db.database import get_db

        # Get a database session
        db = next(get_db())
        try:
            # Delete all foundations
            deleted_foundations = crud.delete_all_foundations(db)

            # Delete all applications
            deleted_applications = crud.delete_all_applications(db)

            # Clear profiles
            deleted_profiles = crud.delete_all_profiles(db)

            return {
                "status": "success",
                "message": "Database cleared successfully",
                "deleted_foundations": deleted_foundations,
                "deleted_applications": deleted_applications,
                "deleted_profiles": deleted_profiles,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in admin database clear: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database clear failed: {str(e)}"
        )


def get_foundation_stats_endpoint():
    """
    Get statistics about foundation translations and embeddings.
    Returns counts for translated/untranslated and embedded/not-embedded.
    """
    try:

        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            # Get total count
            total = db.query(models.Foundation).count()
            translated = db.query(models.Foundation).filter(models.Foundation.translated_purpose.isnot(None)).count()
            embedded = db.query(models.Foundation).filter(models.Foundation.purpose_embedding.isnot(None)).count()

            return {
                "total_foundations": total,
                "translated": translated,
                "untranslated": total - translated,
                "embedded": embedded,
                "not_embedded": total - embedded,
                "translation_percentage": round((translated / total * 100) if total > 0 else 0, 1),
                "embedding_percentage": round((embedded / total * 100) if total > 0 else 0, 1)
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting foundation stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


def get_active_jobs_endpoint():
    """
    Get a summary of currently active background jobs.
    """
    try:
        from app.foundation.task_manager import get_active_tasks_summary
        return get_active_tasks_summary()
    except Exception as e:
        logger.error(f"Error getting active jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active jobs: {str(e)}"
        )


def search_foundations_admin_endpoint(q: str):
    """
    Search for foundations by name or orgnr for admin utilities.
    Returns a brief list of matches.
    """
    if not q or len(q) < 3:
        return []

    try:
        from sqlalchemy import or_

        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            # PostgreSQL ILIKE search
            results = db.query(models.Foundation).filter(
                or_(
                    models.Foundation.name.ilike(f"%{q}%"),
                    models.Foundation.orgnr.ilike(f"%{q}%")
                )
            ).limit(10).all()

            return [
                {
                    "id": f.id,
                    "name": f.name,
                    "orgnr": f.orgnr
                } for f in results
            ]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error searching foundations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
