
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.crud import crud
from app.db.database import get_db

router = APIRouter(prefix="/api/grants", tags=["grants"])


@router.get("")
def list_grants(
    category: str | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return (max 200)"),
    db: Session = Depends(get_db),
):
    """Public grants/foundations listing with pagination."""
    query = db.query(crud.models.Foundation)

    if category:
        query = query.filter(crud.models.Foundation.category == category)
    if search:
        query = query.filter(
            or_(
                crud.models.Foundation.name.ilike(f"%{search}%"),
                crud.models.Foundation.purpose.ilike(f"%{search}%"),
                crud.models.Foundation.summary.ilike(f"%{search}%"),
            )
        )

    # Get total count before pagination
    total = query.count()

    # Apply pagination and order by name for consistent results
    foundations = query.order_by(crud.models.Foundation.name).offset(skip).limit(limit).all()

    def serialize(f):
        return {
            "id": f"foundation-{f.foundation_id}",
            "name": f.name,
            "organization": f"Stiftelse ({f.orgnr or 'Org.nr saknas'})",
            "summary": f.summary or (f.purpose[:200] + "...") if f.purpose and len(f.purpose) > 200 else f.purpose,
            "category": f.category,
            "deadline": None,
        }

    return {
        "grants": [serialize(f) for f in foundations],
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(foundations) < total,
    }


@router.get("/sitemap-data")
def get_sitemap_data(db: Session = Depends(get_db)):
    """Lightweight endpoint — returns (foundation_id, last_updated) for every grant.

    Used by the sitemap generator to populate <lastmod> without fetching full
    grant data. Returns a flat list of {id, last_updated} entries.  The id field
    matches the frontend format: "foundation-{foundation_id}".
    """
    foundations = db.query(crud.models.Foundation.foundation_id, crud.models.Foundation.last_updated).all()
    return [
        {"id": f"foundation-{f.foundation_id}", "last_updated": f.last_updated}
        for f in foundations
    ]


@router.get("/{grant_id}")
def get_grant(grant_id: str, db: Session = Depends(get_db)):
    """Grant detail; supports foundation-{foundation_id} where foundation_id is the external id."""
    if grant_id.startswith("foundation-"):
        raw = grant_id.replace("foundation-", "")
        try:
            foundation_id = int(raw)
        except ValueError:
            raise HTTPException(status_code=404, detail="Grant not found")
        foundation = crud.get_foundation(db, foundation_id)
        if not foundation:
            raise HTTPException(status_code=404, detail="Grant not found")
        return {
            "id": f"foundation-{foundation.foundation_id}",
            "name": foundation.name,
            "organization": f"Stiftelse ({foundation.orgnr or 'Org.nr saknas'})",
            "orgnr": foundation.orgnr,
            "purpose": foundation.purpose,
            "translated_purpose": foundation.translated_purpose,
            "summary": foundation.summary,
            "category": foundation.category,
            "address": foundation.address,
            "postnr": foundation.postnr,
            "postort": foundation.postort,
            "co_address": foundation.co_address,
            "phone": foundation.phone,
            "signature": foundation.signature,
            "roles": foundation.roles or [],
            "parsed_service_area": foundation.parsed_service_area,
            "website_url": foundation.website_url,
            "application_deadline": foundation.application_deadline,
            "application_start": foundation.application_start,
            "application_method": foundation.application_method,
            "contact_email": foundation.contact_email,
            "contact_phone": foundation.contact_phone,
            "who_can_apply": foundation.who_can_apply,
            "enriched_description": foundation.enriched_description,
            "deadline": None,
        }

    # Legacy numeric (DB) id fallback is intentionally removed (issue #19):
    # grant detail is resolved canonically via foundation_id for foundations.
    # A numeric id can only be a legacy grant row.
    try:
        db_id_int = int(grant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Grant not found")

    grant = crud.get_grant(db, db_id_int)
    if grant:
        return {
            "id": f"grant-{grant.id}",
            "name": grant.name,
            "organization": grant.provider,
            "summary": grant.summary or grant.description,
            "category": grant.category,
            "deadline": grant.deadline.isoformat() if grant.deadline else None,
        }

    raise HTTPException(status_code=404, detail="Grant not found")
