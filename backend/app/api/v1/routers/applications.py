
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import schemas
from app.db.database import get_db

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("/", response_model=list[schemas.Application])
def get_applications(db: Session = Depends(get_db)):
    """Get all applications"""
    applications = crud.get_applications(db=db)
    return applications


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_application(
    application: schemas.ApplicationCreate, db: Session = Depends(get_db)
):
    """Create a new application record"""
    # Verify that the grant exists
    grant = crud.get_grant(db=db, grant_id=application.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    db_application = crud.create_application(db=db, application=application)
    return {"message": "Application created successfully", "id": db_application.id}


@router.get("/{application_id}", response_model=schemas.Application)
def get_application(application_id: int, db: Session = Depends(get_db)):
    """Get an application by ID"""
    application = crud.get_application(db=db, application_id=application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{application_id}")
def update_application(
    application_id: int,
    application_update: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
):
    """Update an application"""
    application = crud.update_application(
        db=db, application_id=application_id, application_update=application_update
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"message": "Application updated successfully"}
