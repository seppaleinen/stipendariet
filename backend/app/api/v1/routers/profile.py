from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user_payload
from app.db import models, schemas
from app.db.database import get_db

router = APIRouter(prefix="/api/profile", tags=["profile"])


def get_user_id_from_payload(payload: dict) -> UUID:
    """Extract user UUID from JWT payload."""
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# --- Saved Grants Endpoints ---

class SaveGrantRequest(BaseModel):
    grant_id: str


@router.get("/saved-grants")
def get_saved_grants(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Get authenticated user's saved grant IDs."""
    user_id = get_user_id_from_payload(payload)
    
    saved = db.query(models.SavedGrant).filter(models.SavedGrant.user_id == user_id).all()
    return {"saved_grants": [s.grant_id for s in saved]}


@router.post("/saved-grants", status_code=status.HTTP_201_CREATED)
def save_grant(
    request: SaveGrantRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Save a grant for the authenticated user."""
    user_id = get_user_id_from_payload(payload)
    
    # Check if already saved
    existing = db.query(models.SavedGrant).filter(
        models.SavedGrant.user_id == user_id,
        models.SavedGrant.grant_id == request.grant_id,
    ).first()
    
    if existing:
        return {"message": "Grant already saved", "grant_id": request.grant_id}
    
    saved = models.SavedGrant(user_id=user_id, grant_id=request.grant_id)
    db.add(saved)
    db.commit()
    
    return {"message": "Grant saved", "grant_id": request.grant_id}


@router.delete("/saved-grants/{grant_id}")
def remove_saved_grant(
    grant_id: str,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Remove a saved grant for the authenticated user."""
    user_id = get_user_id_from_payload(payload)
    
    deleted = db.query(models.SavedGrant).filter(
        models.SavedGrant.user_id == user_id,
        models.SavedGrant.grant_id == grant_id,
    ).delete()
    
    db.commit()
    
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved grant not found")
    
    return {"message": "Grant removed", "grant_id": grant_id}


# --- Multi-Profile Endpoints ---

@router.get("/list", response_model=List[schemas.Profile])
def list_profiles(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """List all profiles for the authenticated user."""
    user_id = get_user_id_from_payload(payload)
    profiles = db.query(models.Profile).filter(models.Profile.user_id == user_id).all()
    return profiles


@router.post("/", response_model=schemas.Profile, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: schemas.Profile,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Create a new profile."""
    user_id = get_user_id_from_payload(payload)

    # Check if this is the first profile, if so make it default
    existing_count = db.query(models.Profile).filter(models.Profile.user_id == user_id).count()
    is_default = profile_data.is_default or (existing_count == 0)

    # If setting as default, unset others (though we only enforce one default via logic, not DB constraint yet)
    if is_default:
        db.query(models.Profile).filter(
            models.Profile.user_id == user_id, 
            models.Profile.is_default == True
        ).update({"is_default": False})

    db_profile = models.Profile(
        user_id=user_id,
        name=profile_data.name,
        is_default=is_default,
        county_code=profile_data.county_code,
        municipality_code=profile_data.municipality_code,
        life_situations=profile_data.life_situations,
        health_conditions=profile_data.health_conditions,
        health_details=profile_data.health_details,
        occupations=profile_data.occupations,
        support_purposes=profile_data.support_purposes,
        legacy_data=profile_data.legacy_data,
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/{profile_id}", response_model=schemas.Profile)
def get_profile(
    profile_id: int,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Get a specific profile."""
    user_id = get_user_id_from_payload(payload)
    profile = db.query(models.Profile).filter(
        models.Profile.id == profile_id,
        models.Profile.user_id == user_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
    return profile


@router.put("/{profile_id}", response_model=schemas.Profile)
def update_profile(
    profile_id: int,
    profile_data: schemas.Profile,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Update a specific profile."""
    user_id = get_user_id_from_payload(payload)
    profile = db.query(models.Profile).filter(
        models.Profile.id == profile_id,
        models.Profile.user_id == user_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Handle default toggle
    if profile_data.is_default and not profile.is_default:
        # Unset others
        db.query(models.Profile).filter(
            models.Profile.user_id == user_id, 
            models.Profile.is_default == True
        ).update({"is_default": False})
        profile.is_default = True
    elif not profile_data.is_default and profile.is_default:
         # Warn or allow? Allow for now.
         profile.is_default = False

    profile.name = profile_data.name
    profile.county_code = profile_data.county_code
    profile.municipality_code = profile_data.municipality_code
    profile.life_situations = profile_data.life_situations
    profile.health_conditions = profile_data.health_conditions
    profile.health_details = profile_data.health_details
    profile.occupations = profile_data.occupations
    profile.support_purposes = profile_data.support_purposes
    if profile_data.legacy_data is not None:
        profile.legacy_data = profile_data.legacy_data

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Delete a profile."""
    user_id = get_user_id_from_payload(payload)
    
    # Don't allow deleting the last profile maybe? Or just allow it.
    
    result = db.query(models.Profile).filter(
        models.Profile.id == profile_id,
        models.Profile.user_id == user_id
    ).delete()
    
    db.commit()
    
    if result == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return None


# --- Legacy / Default Profile Endpoints ---

@router.get("/family", response_model=schemas.Profile)
def get_family_profile(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Get authenticated user's default profile (backward compatibility)."""
    user_id = get_user_id_from_payload(payload)
    
    # Try to find default profile
    profile = db.query(models.Profile).filter(
        models.Profile.user_id == user_id,
        models.Profile.is_default == True
    ).first()
    
    # Fallback to any profile
    if not profile:
        profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
        
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return profile


@router.put("/family", response_model=schemas.Profile)
def upsert_family_profile(
    profile_data: schemas.Profile,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Create or update authenticated user's default profile (backward compatibility)."""
    user_id = get_user_id_from_payload(payload)
    
    # Try to find default profile
    db_profile = db.query(models.Profile).filter(
        models.Profile.user_id == user_id,
        models.Profile.is_default == True
    ).first()
    
    # Fallback to any profile
    if not db_profile:
        db_profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
    
    if db_profile:
        # Update existing
        db_profile.name = profile_data.name # Update name if provided in legacy call? Sure.
        db_profile.county_code = profile_data.county_code
        db_profile.municipality_code = profile_data.municipality_code
        db_profile.life_situations = profile_data.life_situations
        db_profile.health_conditions = profile_data.health_conditions
        db_profile.health_details = profile_data.health_details
        db_profile.occupations = profile_data.occupations
        db_profile.support_purposes = profile_data.support_purposes
        if profile_data.legacy_data is not None:
            db_profile.legacy_data = profile_data.legacy_data
        
        # Ensure it is marked default if we are treating it as such
        db_profile.is_default = True
        
    else:
        # Create new default profile
        db_profile = models.Profile(
            user_id=user_id,
            name=profile_data.name or "My Profile",
            is_default=True,
            county_code=profile_data.county_code,
            municipality_code=profile_data.municipality_code,
            life_situations=profile_data.life_situations,
            health_conditions=profile_data.health_conditions,
            health_details=profile_data.health_details,
            occupations=profile_data.occupations,
            support_purposes=profile_data.support_purposes,
            legacy_data=profile_data.legacy_data,
        )
        db.add(db_profile)
    
    db.commit()
    db.refresh(db_profile)
    return db_profile



