from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models, schemas
from app.core.config import settings


def get_foundation_batch_size() -> int:
    try:
        return max(50, int(getattr(settings, "FOUNDATION_BATCH_SIZE", 500)))
    except Exception:
        return 500


# Foundation CRUD operations
def get_foundations_with_category_filter(
    db: Session,
    q: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
) -> List[models.Foundation]:
    """Get all foundations with optional filtering and sorting"""
    query = db.query(models.Foundation)

    if q:
        query = query.filter(
            or_(
                models.Foundation.name.contains(q),
                models.Foundation.purpose.contains(q),
                models.Foundation.translated_purpose.contains(q),
                models.Foundation.summary.contains(q)
            )
        )

    if category:
        query = query.filter(models.Foundation.category == category)

    if sort == "name":
        query = query.order_by(models.Foundation.name)
    elif sort == "location":
        query = query.order_by(models.Foundation.postort)

    return query.all()


# Application CRUD operations - now for foundations
def get_applications(db: Session) -> List[models.Application]:
    """Get all applications"""
    return db.query(models.Application).all()


def get_application(db: Session, application_id: int) -> Optional[models.Application]:
    """Get a single application by ID"""
    return (
        db.query(models.Application)
        .filter(models.Application.id == application_id)
        .first()
    )


def create_application(
    db: Session, application: schemas.ApplicationCreate
) -> models.Application:
    """Create a new foundation application"""
    db_application = models.Application(**application.dict())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


def update_application(
    db: Session, application_id: int, application_update: schemas.ApplicationUpdate
) -> Optional[models.Application]:
    """Update an existing foundation application"""
    db_application = get_application(db, application_id)
    if db_application:
        update_data = application_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_application, field, value)
        db.commit()
        db.refresh(db_application)
    return db_application


# Profile CRUD operations
def get_profile(db: Session) -> Optional[models.Profile]:
    """Get the saved profile (assuming single profile for now)"""
    return db.query(models.Profile).first()


def save_profile(db: Session, profile: schemas.Profile) -> models.Profile:
    """Save or update the profile"""
    db_profile = get_profile(db)
    if db_profile:
        # Update existing profile
        # Use model_dump for Pydantic v2 compatibility, fallback to dict for v1
        if hasattr(profile, "model_dump"):
            profile_data = profile.model_dump()
        else:
            profile_data = profile.dict()
        for field, value in profile_data.items():
            setattr(db_profile, field, value)
    else:
        # Create new profile
        # Use model_dump for Pydantic v2 compatibility, fallback to dict for v1
        if hasattr(profile, "model_dump"):
            profile_dict = profile.model_dump()
        else:
            profile_dict = profile.dict()
        db_profile = models.Profile(**profile_dict)
        db.add(db_profile)

    db.commit()
    db.refresh(db_profile)

    return db_profile


# Foundation CRUD operations
def get_foundations(db: Session) -> List[models.Foundation]:
    """Get all foundations"""
    return db.query(models.Foundation).all()


def get_foundation(
    db: Session, foundation_id: int
) -> Optional[models.Foundation]:
    """Get a single foundation by foundation_id (from external API)"""
    if foundation_id is None:
        return None
    return (
        db.query(models.Foundation)
        .filter(models.Foundation.foundation_id == foundation_id)
        .first()
    )


def get_foundations_by_county_code(
    db: Session, county_code: str
) -> List[models.Foundation]:
    """Get all foundations in a specific county by county code"""
    return (
        db.query(models.Foundation)
        .filter(models.Foundation.county_code == county_code)
        .all()
    )


def get_foundations_by_municipality_code(
    db: Session, municipality_code: str
) -> List[models.Foundation]:
    """Get all foundations in a specific municipality by municipality code"""
    return (
        db.query(models.Foundation)
        .filter(models.Foundation.municipality_code == municipality_code)
        .all()
    )


def get_foundation_by_db_id(db: Session, db_id: int) -> Optional[models.Foundation]:
    """Get a single foundation by database ID"""
    return db.query(models.Foundation).filter(models.Foundation.id == db_id).first()


def create_or_update_foundation(
    db: Session, foundation_data: dict
) -> models.Foundation:
    """Create a foundation or update if it already exists.
    
    Preserves translated_purpose and purpose_embedding on updates.
    """
    # Fields that should NOT be overwritten on update
    preserve_fields = {'translated_purpose', 'purpose_embedding'}
    
    # Check if foundation already exists using the foundation_id
    foundation_id = foundation_data.get("foundation_id")
    existing_foundation = get_foundation(db, foundation_id)

    if existing_foundation:
        # Update existing foundation
        # Only update fields that are in the foundation_data dict
        for field, value in foundation_data.items():
            # Skip preserved fields - don't overwrite translations/embeddings
            if field in preserve_fields:
                continue
            if hasattr(existing_foundation, field):
                setattr(existing_foundation, field, value)
        db.commit()
        db.refresh(existing_foundation)
        return existing_foundation
    else:
        # Create new foundation
        # Filter the data to only include fields that exist in the model
        valid_fields = {}
        for field, value in foundation_data.items():
            # Check if the field exists in the model
            if hasattr(models.Foundation, field):
                valid_fields[field] = value

        db_foundation = models.Foundation(**valid_fields)
        db.add(db_foundation)
        db.commit()
        db.refresh(db_foundation)
        return db_foundation


def create_foundations(
    db: Session, foundations_data: List[dict]
) -> List[models.Foundation]:
    """Create/update multiple foundations in batch"""
    created_foundations = []

    for foundation_data in foundations_data:
        foundation = create_or_update_foundation(db, foundation_data)
        created_foundations.append(foundation)

    return created_foundations


def create_foundations_batch(
    db: Session, foundations_data: List[dict]
) -> List[models.Foundation]:
    """Create/update multiple foundations in one transaction.
    
    Preserves translated_purpose and purpose_embedding on updates to avoid
    losing work from translation/embedding jobs.
    """
    created_foundations = []
    
    # Fields that should NOT be overwritten on update (preserve translations/embeddings)
    preserve_fields = {'translated_purpose', 'purpose_embedding'}

    for foundation_data in foundations_data:
        foundation_id = foundation_data.get("foundation_id")
        existing = get_foundation(db, foundation_id)
        if existing:
            for field, value in foundation_data.items():
                # Skip preserved fields - don't overwrite translations/embeddings
                if field in preserve_fields:
                    continue
                if hasattr(existing, field):
                    setattr(existing, field, value)
            created_foundations.append(existing)
        else:
            valid_fields = {k: v for k, v in foundation_data.items() if hasattr(models.Foundation, k)}
            db_foundation = models.Foundation(**valid_fields)
            db.add(db_foundation)
            created_foundations.append(db_foundation)

    db.commit()
    for foundation in created_foundations:
        db.refresh(foundation)

    return created_foundations


def delete_all_foundations(db: Session) -> int:
    """Delete all foundations from the database (useful for clean sync)"""
    count = db.query(models.Foundation).delete()
    db.commit()
    return count


def delete_all_profiles(db: Session) -> int:
    """Delete all profiles from the database"""
    count = db.query(models.Profile).delete()
    db.commit()
    return count


def delete_all_applications(db: Session) -> int:
    """Delete all applications from the database"""
    count = db.query(models.Application).delete()
    db.commit()
    return count


# Grant CRUD operations
def get_grants(db: Session) -> List[models.Grant]:
    """Get all grants"""
    return db.query(models.Grant).all()


def get_grant(db: Session, grant_id: int) -> Optional[models.Grant]:
    """Get a single grant by ID"""
    return db.query(models.Grant).filter(models.Grant.id == grant_id).first()


def create_grant(db: Session, grant: schemas.GrantCreate) -> models.Grant:
    """Create a new grant"""
    db_grant = models.Grant(**grant.dict())
    db.add(db_grant)
    db.commit()
    db.refresh(db_grant)
    return db_grant


def update_grant(
    db: Session, grant_id: int, grant_update: schemas.GrantUpdate
) -> Optional[models.Grant]:
    """Update an existing grant"""
    db_grant = get_grant(db, grant_id)
    if db_grant:
        update_data = grant_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_grant, field, value)
        db.commit()
        db.refresh(db_grant)
    return db_grant


def delete_grant(db: Session, grant_id: int) -> bool:
    """Delete a grant by ID"""
    db_grant = get_grant(db, grant_id)
    if db_grant:
        db.delete(db_grant)
        db.commit()
        return True
    return False
