"""
Admin enrichment source CRUD endpoints.

Manage the web sources (aggregators, official sites, blogs, directories)
used during enrichment crawling.
"""

import logging

from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---- Pydantic schemas ----


class EnrichmentSourceCreate(BaseModel):
    """Schema for creating a new enrichment source."""

    url: str = Field(..., description="Source URL (e.g. aggregator or official site)")
    is_official: bool = Field(False, description="Whether this is an official/verified source")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Reliability score 0.0-1.0")
    source_type: str | None = Field(
        None,
        description="Type hint: 'aggregator', 'official', 'blog', 'directory'",
    )
    foundation_id: int | None = Field(None, description="Optional: link source to a specific foundation")


class EnrichmentSourceUpdate(BaseModel):
    """Schema for updating an enrichment source."""

    url: str | None = None
    is_official: bool | None = None
    confidence: float | None = None
    source_type: str | None = None


class EnrichmentSourceInDB(BaseModel):
    """Schema returned to the client."""

    id: int
    foundation_id: int | None
    url: str
    is_official: bool
    confidence: float
    source_type: str | None
    last_validated: str | None
    created_at: str | None

    class Config:
        from_attributes = True


# ---- Service functions ----


def _to_schema(source) -> EnrichmentSourceInDB:
    """Convert an EnrichmentSource ORM row to the response schema."""
    return EnrichmentSourceInDB(
        id=source.id,
        foundation_id=source.foundation_id,
        url=source.url,
        is_official=source.is_official,
        confidence=source.confidence,
        source_type=source.source_type,
        last_validated=str(source.last_validated) if source.last_validated else None,
        created_at=str(source.created_at) if source.created_at else None,
    )


def _get_session():
    from app.db.database import get_db

    return next(get_db())


# ---- API endpoint handlers ----


def list_sources_endpoint(
    foundation_id: int | None = Query(None, description="Filter by foundation ID"),
    is_official: bool | None = Query(None, description="Filter by official status"),
    source_type: str | None = Query(None, description="Filter by source type"),
):
    """List enrichment sources."""
    from sqlalchemy import select

    from app.db import models

    try:
        db = _get_session()
        try:
            query = select(models.EnrichmentSource)

            if foundation_id is not None:
                query = query.where(models.EnrichmentSource.foundation_id == foundation_id)
            if is_official is not None:
                query = query.where(models.EnrichmentSource.is_official == is_official)
            if source_type is not None:
                query = query.where(models.EnrichmentSource.source_type == source_type)

            sources = db.execute(query).scalars().all()
            return [_to_schema(s) for s in sources]
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing enrichment sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sources: {str(e)}",
        )


def get_source_endpoint(source_id: int):
    """Get a single source by ID."""
    from sqlalchemy import select

    from app.db import models

    try:
        db = _get_session()
        try:
            source = db.execute(
                select(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id)
            ).scalar_one_or_none()

            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
            return _to_schema(source)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enrichment source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get source: {str(e)}",
        )


def create_source_endpoint(payload: EnrichmentSourceCreate):
    """Create a new enrichment source."""
    from sqlalchemy import insert, select

    from app.db import models

    try:
        db = _get_session()
        try:
            db.execute(
                insert(models.EnrichmentSource).values(
                    url=payload.url,
                    is_official=payload.is_official,
                    confidence=payload.confidence,
                    source_type=payload.source_type,
                    foundation_id=payload.foundation_id,
                )
            )
            db.commit()

            # Re-fetch the newly inserted source by URL (most recent for this URL)
            source = db.execute(
                select(models.EnrichmentSource)
                .where(models.EnrichmentSource.url == payload.url)
                .order_by(models.EnrichmentSource.id.desc())
                .limit(1)
            ).scalar_one_or_none()

            if not source:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve newly created source",
                )

            return _to_schema(source)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating enrichment source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create source: {str(e)}",
        )


def update_source_endpoint(
    source_id: int,
    payload: EnrichmentSourceUpdate,
):
    """Update an enrichment source."""
    from sqlalchemy import select, update

    from app.db import models

    try:
        db = _get_session()
        try:
            existing = db.execute(
                select(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id)
            ).scalar_one_or_none()

            if not existing:
                raise HTTPException(status_code=404, detail="Source not found")

            # Build update dict, only include non-None fields
            update_data = {}
            if payload.url is not None:
                update_data["url"] = payload.url
            if payload.is_official is not None:
                update_data["is_official"] = payload.is_official
            if payload.confidence is not None:
                update_data["confidence"] = payload.confidence
            if payload.source_type is not None:
                update_data["source_type"] = payload.source_type

            db.execute(
                update(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id).values(**update_data)
            )
            db.commit()

            updated = db.execute(
                select(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id)
            ).scalar_one_or_none()

            if not updated:
                raise HTTPException(status_code=404, detail="Source not found")
            return _to_schema(updated)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating enrichment source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update source: {str(e)}",
        )


def delete_source_endpoint(source_id: int):
    """Delete an enrichment source."""
    from sqlalchemy import delete, select

    from app.db import models

    try:
        db = _get_session()
        try:
            existing = db.execute(
                select(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id)
            ).scalar_one_or_none()

            if not existing:
                raise HTTPException(status_code=404, detail="Source not found")

            db.execute(delete(models.EnrichmentSource).where(models.EnrichmentSource.id == source_id))
            db.commit()
            return {"detail": "Source deleted successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting enrichment source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete source: {str(e)}",
        )
