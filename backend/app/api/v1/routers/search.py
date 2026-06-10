from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/foundations")
def search_foundations(
    query: str, db: Session = Depends(get_db), limit: int = 10
) -> list[dict[str, Any]]:
    """Search for foundations using SQL text search"""
    try:
        foundations = (
            db.query(models.Foundation)
            .filter(
                or_(
                    models.Foundation.name.ilike(f"%{query}%"),
                    models.Foundation.purpose.ilike(f"%{query}%"),
                    models.Foundation.translated_purpose.ilike(f"%{query}%"),
                    models.Foundation.summary.ilike(f"%{query}%"),
                    models.Foundation.tags.any(query),  # if tags is an array
                )
            )
            .limit(limit)
            .all()
        )

        results = []
        for foundation in foundations:
            results.append(
                {
                    "id": foundation.id,
                    "foundation_id": foundation.foundation_id,
                    "name": foundation.name,
                    "orgnr": foundation.orgnr,
                    "purpose": foundation.purpose,
                    "summary": foundation.summary,
                    "address": foundation.address,
                    "postnr": foundation.postnr,
                    "postort": foundation.postort,
                    "target_groups": foundation.target_groups,
                    "funding_areas": foundation.funding_areas,
                    "tags": foundation.tags,
                    "category": foundation.category,
                }
            )

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching foundations: {str(e)}"
        )


@router.get("/profiles")
def search_profiles(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for profiles (not implemented)"""
    return []
