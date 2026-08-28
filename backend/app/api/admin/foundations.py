"""
Admin foundational list endpoints for translation judging.

Provides a paginated list of foundations (with original purpose, translated
purpose and supporting row data) so a human judge can eyeball LLM translations
side by side.
"""

import logging

from fastapi import HTTPException, Query, status

logger = logging.getLogger(__name__)


def list_foundations_for_translation_endpoint(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    status_filter: str = Query(
        "all",
        description="Filter by translation status: all, translated, missing",
    ),
):
    """
    Return a paginated list of foundations for translation judging.

    Every item carries both the original Swedish `purpose` and the LLM-translated
    `translated_purpose`, plus the foundation's row data (name, orgnr, address,
    county/municipality codes, parsed_service_area, etc.) to judge translations in
    situ against the foundation's other data.

    Args:
        page: 1-based page number.
        page_size: items per page (1-200).
        status_filter: 'all' | 'translated' | 'missing'.
    """
    if status_filter not in ("all", "translated", "missing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of: all, translated, missing",
        )

    try:
        from app.db import models
        from app.db.database import get_db

        db = next(get_db())
        try:
            query = db.query(models.Foundation)

            if status_filter == "translated":
                query = query.filter(models.Foundation.translated_purpose.isnot(None))
            elif status_filter == "missing":
                query = query.filter(
                    models.Foundation.translated_purpose.is_(None)
                )

            total = query.count()

            foundations = (
                query.order_by(models.Foundation.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            items = []
            for f in foundations:
                items.append({
                    "id": f.id,
                    "foundation_id": f.foundation_id,
                    "name": f.name,
                    "orgnr": f.orgnr,
                    "purpose": f.purpose,
                    "translated_purpose": f.translated_purpose,
                    "summary": f.summary,
                    "address": f.address,
                    "postnr": f.postnr,
                    "postort": f.postort,
                    "county_code": f.county_code,
                    "municipality_code": f.municipality_code,
                    "parsed_service_area": f.parsed_service_area,
                    "category": f.category,
                    "last_updated": f.last_updated,
                })

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items,
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing foundations for translation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list foundations: {str(e)}",
        )
