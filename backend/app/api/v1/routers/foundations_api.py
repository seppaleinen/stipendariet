
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import schemas
from app.db.database import get_db

router = APIRouter(prefix="/api/foundations-api", tags=["foundations"])  # Changed to distinguish from other foundation endpoints


@router.get("/", response_model=list[schemas.Foundation])
def get_foundations_api(
    q: str | None = None,
    category: str | None = None,
    sort: str | None = None,
    db: Session = Depends(get_db),
):
    """Get list of foundations with optional filtering and sorting"""
    foundations = crud.get_foundations_with_category_filter(db=db, q=q, category=category, sort=sort)
    return foundations


@router.get("/{foundation_id}", response_model=schemas.Foundation)
def get_foundation_api(foundation_id: int, db: Session = Depends(get_db)):
    """Get a single foundation by ID"""
    foundation = crud.get_foundation(db=db, foundation_id=foundation_id)
    if foundation is None:
        raise HTTPException(status_code=404, detail="Foundation not found")
    return foundation
