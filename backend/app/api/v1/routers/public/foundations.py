from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_admin_user, get_current_user_payload
from app.db import models, schemas
from app.db.database import get_db
from app.foundation.foundation_api import get_foundations_by_query, poll_foundations
from app.foundation.foundation_schemas import FoundationSearchResponse
from app.foundation.profile_text_generator import generate_profile_text
from app.repositories.foundation_repo import FoundationRepository
from app.services.embedding_service import SIMILARITY_THRESHOLD, ollama_embedding_service
from app.services.foundation_service import (
    categorize_db_foundations as _categorize_service,
)
from app.services.foundation_service import (
    find_matching_by_profile as _fm_service,
)
from app.services.foundation_service import (
    find_matching_foundations_with_db,
    get_all_categories,
    get_categorization_status,
)
from app.services.foundation_service import (
    reset_categories as _reset_categories_service,
)
from app.services.llm_translation_service import llm_translation_service


class TranslationRequest(BaseModel):
    purpose: str


class MatchingRequest(BaseModel):
    needs: str  # User's description of their needs
    threshold: float | None = SIMILARITY_THRESHOLD  # Similarity threshold (0-1)
    limit: int | None = 20  # Max results


class ProfileMatchingRequest(BaseModel):
    profile_id: int | None = None  # Specific profile to match against
    use_geographic_filter: bool = True  # If True, hard filter by county/municipality
    use_description: bool = False  # If True, embed the profile's self-description instead of its structured selections
    threshold: float | None = SIMILARITY_THRESHOLD
    limit: int | None = 20


class MatchedFoundation(BaseModel):
    foundation: schemas.Foundation
    similarity_score: float


router = APIRouter(prefix="/api/foundations", tags=["foundations"])


@router.get("/", response_model=FoundationSearchResponse)
def get_all_foundations():
    """Get all foundations by polling the external API"""
    result = poll_foundations()
    if result is None:
        raise HTTPException(
            status_code=503, detail="Could not fetch foundations from external API"
        )
    return result


@router.get("/search", response_model=FoundationSearchResponse)
def search_foundations(query: str | None = None):
    """Search foundations by query parameter"""
    result = get_foundations_by_query(query)
    if result is None:
        raise HTTPException(
            status_code=503, detail="Could not fetch foundations from external API"
        )
    return result


# Database-stored foundations endpoints
@router.get("/stored", response_model=list[schemas.Foundation])
def get_stored_foundations(db: Session = Depends(get_db)):
    """Get all stored foundations from the database"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations()
    return foundations


@router.get("/stored/{foundation_id}", response_model=schemas.Foundation)
def get_stored_foundation(foundation_id: int, db: Session = Depends(get_db)):
    """Get a specific stored foundation from the database"""
    repo = FoundationRepository(db)
    foundation = repo.get_foundation(foundation_id)
    if foundation is None:
        raise HTTPException(status_code=404, detail="Foundation not found in database")
    return foundation


@router.get("/stored/by-category/{category}", response_model=list[schemas.Foundation])
def get_stored_foundations_by_category(category: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by category"""
    foundations = (
        db.query(models.Foundation).filter(models.Foundation.category == category).all()
    )
    return foundations


@router.get("/stored/by-county/{county_code}", response_model=list[schemas.Foundation])
def get_stored_foundations_by_county(county_code: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by county code"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations_by_county_code(county_code)
    return foundations


@router.get("/stored/by-municipality/{municipality_code}", response_model=list[schemas.Foundation])
def get_stored_foundations_by_municipality(municipality_code: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by municipality code"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations_by_municipality_code(municipality_code)
    return foundations


@router.get("/categories", response_model=list[str])
def get_all_categories_endpoint(db: Session = Depends(get_db)):
    """Get all unique categories from the database"""
    categories = get_all_categories(db)
    return categories


@router.get("/categorization-status", response_model=dict)
def get_categorization_status_endpoint(db: Session = Depends(get_db)):
    """Get status information about foundation categorization"""
    status = get_categorization_status(db)
    return status


# Categorization endpoints
@router.post(
    "/reset-categories",
    tags=["foundations", "admin"],
    summary="Reset all foundation categories in database",
    dependencies=[Depends(get_admin_user)],
)
def reset_categories(db: Session = Depends(get_db)):
    """Reset all foundation categories to allow recategorization"""
    result = _reset_categories_service(db)
    return result


@router.post(
    "/categorize-db-foundations",
    tags=["foundations", "admin"],
    summary="Categorize all foundations in database",
    dependencies=[Depends(get_admin_user)],
)
def categorize_db_foundations(db: Session = Depends(get_db)):
    """Trigger categorization of all foundations stored in the database"""
    result = _categorize_service(db)
    return result


@router.post(
    "/translate-purpose",
    summary="Translate foundation purpose from old Swedish to modern Swedish",
)
def translate_purpose_endpoint(translation_request: TranslationRequest):
    """Translate a foundation purpose from old/legalese Swedish to modern Swedish using Ollama.

    The request body should contain a 'purpose' field with the text to translate.
    """
    purpose = translation_request.purpose
    if not purpose:
        raise HTTPException(
            status_code=400,
            detail="Purpose field is required for translation"
        )

    try:
        translated_purpose = llm_translation_service.translate_purpose(purpose)
        if translated_purpose is None:
            raise HTTPException(
                status_code=500,
                detail="Translation failed. Please try again later."
            )
        return {
            "original_purpose": purpose,
            "translated_purpose": translated_purpose,
            "status": "success",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during translation: {str(e)}"
        )


@router.post("/matching", response_model=list[MatchedFoundation])
def find_matching_foundations(
    matching_request: MatchingRequest,
    db: Session = Depends(get_db)
):
    """Find foundations that semantically match the user's needs.

    Uses vector similarity search on translated purposes.

    Args:
        matching_request: Contains the user's needs description and optional threshold/limit
    Returns:
        List of foundations ranked by similarity score (highest first)
    """
    try:
        service_results = find_matching_foundations_with_db(
            matching_request.needs,
            matching_request.threshold,
            matching_request.limit,
            db
        )
        # Convert service dicts to MatchedFoundation objects
        matched = []
        for item in service_results:
            foundation = schemas.Foundation(
                id=item["id"],
                foundation_id=item["foundation_id"],
                name=item["name"],
                orgnr=item["orgnr"],
                purpose=item["purpose"],
                translated_purpose=item["translated_purpose"],
                summary=item["summary"],
                address=item["address"],
                postnr=item["postnr"],
                postort=item["postort"],
                county_code=item["county_code"],
                municipality_code=item["municipality_code"],
                phone=item["phone"],
                co_address=item["co_address"],
                type=item["type"],
                signature=item["signature"],
                roles=item["roles"],
                business_entities=item["business_entities"],
                last_updated=item["last_updated"],
                target_groups=item["target_groups"],
                funding_areas=item["funding_areas"],
                tags=item["tags"],
                category=item["category"],
                raw_data=item["raw_data"],
            )
            matched.append(MatchedFoundation(
                foundation=foundation,
                similarity_score=item["similarity_score"]
            ))
        return matched
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding matching foundations: {str(e)}"
        )


@router.post("/matching-by-profile", response_model=list[MatchedFoundation])
def find_matching_by_profile(
    request: ProfileMatchingRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db)
):
    """Find foundations that match the user's profile.

    Uses vector similarity search on generated profile text against foundation purposes.
    Optionally applies geographic filtering based on county/municipality.
    """
    from uuid import UUID

    try:
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token")

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token")

        service_results = _fm_service(
            request, user_id, db,
            embedding_service=ollama_embedding_service,
            profile_text_generator=generate_profile_text
        )
        # Convert service dicts to MatchedFoundation objects
        matched = []
        for item in service_results:
            foundation = schemas.Foundation(
                id=item["id"],
                foundation_id=item["foundation_id"],
                name=item["name"],
                orgnr=item["orgnr"],
                purpose=item["purpose"],
                translated_purpose=item["translated_purpose"],
                summary=item["summary"],
                address=item["address"],
                postnr=item["postnr"],
                postort=item["postort"],
                parsed_service_area=item["parsed_service_area"],
                phone=item["phone"],
                co_address=item["co_address"],
                type=item["type"],
                signature=item["signature"],
                roles=item["roles"],
                business_entities=item["business_entities"],
                last_updated=item["last_updated"],
                target_groups=item["target_groups"],
                funding_areas=item["funding_areas"],
                tags=item["tags"],
                category=item["category"],
                raw_data=item["raw_data"],
            )
            matched.append(MatchedFoundation(
                foundation=foundation,
                similarity_score=item["similarity_score"]
            ))
        return matched
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding matching foundations: {str(e)}"
        )
