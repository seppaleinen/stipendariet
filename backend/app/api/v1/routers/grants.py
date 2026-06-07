from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.crud import crud
from app.db.database import get_db

router = APIRouter(prefix="/api/grants", tags=["grants"])


@router.get("")
def list_grants(
    category: Optional[str] = None,
    search: Optional[str] = None,
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
            "id": f"foundation-{f.id}",
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


@router.get("/{grant_id}")
def get_grant(grant_id: str, db: Session = Depends(get_db)):
    """Grant detail; supports foundation-{id} where id is DB id."""
    if grant_id.startswith("foundation-"):
        db_id = grant_id.replace("foundation-", "")
        try:
            db_id_int = int(db_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Grant not found")
        foundation = crud.get_foundation_by_db_id(db, db_id_int)
        if not foundation:
            raise HTTPException(status_code=404, detail="Grant not found")
        return {
            "id": f"foundation-{foundation.id}",
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
            "deadline": None,
        }
    # Legacy numeric id -> try foundations then grants
    try:
        db_id_int = int(grant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Grant not found")

    foundation = crud.get_foundation_by_db_id(db, db_id_int)
    if foundation:
        return {
            "id": f"foundation-{foundation.id}",
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
            "deadline": None,
        }

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
