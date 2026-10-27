
import warnings

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models, schemas
from app.repositories.foundation_repo import FoundationRepository


def get_foundation_batch_size() -> int:
    try:
        return max(50, int(getattr(settings, "FOUNDATION_BATCH_SIZE", 500)))
    except Exception:
        return 500


# Foundation CRUD operations
# NOTE: Foundation CRUD operations are deprecated. Use
# app.repositories.foundation_repo.FoundationRepository instead.
def get_foundations_with_category_filter(
    db: Session,
    q: str | None = None,
    category: str | None = None,
    sort: str | None = None,
) -> list[models.Foundation]:
    """Get all foundations with optional filtering and sorting

    .. deprecated::
        Use ``FoundationRepository.get_foundations_with_category_filter`` instead.
    """
    warnings.warn(
        "crud.get_foundations_with_category_filter is deprecated, "
        "use FoundationRepository.get_foundations_with_category_filter",
        DeprecationWarning,
        stacklevel=2,
    )
    return (
        FoundationRepository(db)
        .get_foundations_with_category_filter(q=q, category=category, sort=sort)
    )


# Application CRUD operations - now for foundations
def get_applications(db: Session) -> list[models.Application]:
    """Get all applications"""
    return db.query(models.Application).all()


def get_application(db: Session, application_id: int) -> models.Application | None:
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
) -> models.Application | None:
    """Update an existing foundation application"""
    db_application = get_application(db, application_id)
    if db_application:
        update_data = application_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_application, field, value)
        db.commit()
        db.refresh(db_application)
    return db_application


def delete_application(db: Session, application_id: int) -> bool:
    """Delete an application by ID. Returns True if deleted, False if not found."""
    db_application = get_application(db, application_id)
    if db_application is None:
        return False
    db.delete(db_application)
    db.commit()
    return True


# Profile CRUD operations
def get_profile(db: Session) -> models.Profile | None:
    """Get the saved profile (assuming single profile for now)"""
    return db.query(models.Profile).first()


def save_profile(db: Session, profile: schemas.Profile) -> models.Profile:
    """Save or update the profile"""
    db_profile = get_profile(db)
    if db_profile:
        # Update existing profile
        # Use model_dump for Pydantic v2 compatibility, fallback to dict for v1
        profile_data = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
        for field, value in profile_data.items():
            setattr(db_profile, field, value)
    else:
        # Create new profile
        # Use model_dump for Pydantic v2 compatibility, fallback to dict for v1
        profile_dict = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
        db_profile = models.Profile(**profile_dict)
        db.add(db_profile)

    db.commit()
    db.refresh(db_profile)

    return db_profile


# Foundation CRUD operations
def get_foundations(db: Session) -> list[models.Foundation]:
    """Get all foundations

    .. deprecated::
        Use ``FoundationRepository.get_foundations`` instead.
    """
    warnings.warn(
        "crud.get_foundations is deprecated, use FoundationRepository.get_foundations",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).get_foundations()


def get_foundation(
    db: Session, foundation_id: int
) -> models.Foundation | None:
    """Get a single foundation by foundation_id (from external API)

    .. deprecated::
        Use ``FoundationRepository.get_foundation`` instead.
    """
    warnings.warn(
        "crud.get_foundation is deprecated, use FoundationRepository.get_foundation",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).get_foundation(foundation_id)


def get_foundations_by_county_code(
    db: Session, county_code: str
) -> list[models.Foundation]:
    """Get all foundations in a specific county by county code

    .. deprecated::
        Use ``FoundationRepository.get_foundations_by_county_code`` instead.
    """
    warnings.warn(
        "crud.get_foundations_by_county_code is deprecated, "
        "use FoundationRepository.get_foundations_by_county_code",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).get_foundations_by_county_code(county_code)


def get_foundations_by_municipality_code(
    db: Session, municipality_code: str
) -> list[models.Foundation]:
    """Get all foundations in a specific municipality by municipality code

    .. deprecated::
        Use ``FoundationRepository.get_foundations_by_municipality_code`` instead.
    """
    warnings.warn(
        "crud.get_foundations_by_municipality_code is deprecated, "
        "use FoundationRepository.get_foundations_by_municipality_code",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).get_foundations_by_municipality_code(
        municipality_code
    )


def get_foundation_by_db_id(db: Session, db_id: int) -> models.Foundation | None:
    """Get a single foundation by database ID

    .. deprecated::
        Use ``FoundationRepository.get_foundation_by_db_id`` instead.
    """
    warnings.warn(
        "crud.get_foundation_by_db_id is deprecated, "
        "use FoundationRepository.get_foundation_by_db_id",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).get_foundation_by_db_id(db_id)


def create_or_update_foundation(
    db: Session, foundation_data: dict
) -> models.Foundation:
    """Create a foundation or update if it already exists.

    Preserves translated_purpose and purpose_embedding on updates.

    .. deprecated::
        Use ``FoundationRepository.create_or_update_foundation`` instead.
    """
    warnings.warn(
        "crud.create_or_update_foundation is deprecated, "
        "use FoundationRepository.create_or_update_foundation",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).create_or_update_foundation(foundation_data)


def create_foundations(
    db: Session, foundations_data: list[dict]
) -> list[models.Foundation]:
    """Create/update multiple foundations in batch

    .. deprecated::
        Use ``FoundationRepository.create_foundations`` instead.
    """
    warnings.warn(
        "crud.create_foundations is deprecated, use FoundationRepository.create_foundations",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).create_foundations(foundations_data)


def create_foundations_batch(
    db: Session, foundations_data: list[dict]
) -> list[models.Foundation]:
    """Create/update multiple foundations in one transaction.

    Preserves translated_purpose and purpose_embedding on updates to avoid
    losing work from translation/embedding jobs.

    .. deprecated::
        Use ``FoundationRepository.create_foundations_batch`` instead.
    """
    warnings.warn(
        "crud.create_foundations_batch is deprecated, "
        "use FoundationRepository.create_foundations_batch",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).create_foundations_batch(foundations_data)


def delete_all_foundations(db: Session) -> int:
    """Delete all foundations from the database (useful for clean sync)

    .. deprecated::
        Use ``FoundationRepository.delete_all_foundations`` instead.
    """
    warnings.warn(
        "crud.delete_all_foundations is deprecated, "
        "use FoundationRepository.delete_all_foundations",
        DeprecationWarning,
        stacklevel=2,
    )
    return FoundationRepository(db).delete_all_foundations()


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
def get_grants(db: Session) -> list[models.Grant]:
    """Get all grants"""
    return db.query(models.Grant).all()


def get_grant(db: Session, grant_id: int) -> models.Grant | None:
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
) -> models.Grant | None:
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
