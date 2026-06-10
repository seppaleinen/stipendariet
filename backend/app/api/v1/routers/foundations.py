
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.security import get_current_user_payload
from app.crud import crud
from app.db import models, schemas
from app.db.database import get_db
from app.foundation.foundation_api import get_foundations_by_query, poll_foundations
from app.foundation.foundation_schemas import FoundationSearchResponse
from app.foundation.profile_text_generator import generate_profile_text
from app.services.embedding_service import SIMILARITY_THRESHOLD, ollama_embedding_service
from app.services.ollama_translation_service import ollama_translation_service


class TranslationRequest(BaseModel):
    purpose: str


class MatchingRequest(BaseModel):
    needs: str  # User's description of their needs
    threshold: float | None = SIMILARITY_THRESHOLD  # Similarity threshold (0-1)
    limit: int | None = 20  # Max results


class ProfileMatchingRequest(BaseModel):
    profile_id: int | None = None  # Specific profile to match against
    use_geographic_filter: bool = True  # If True, hard filter by county/municipality
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
    foundations = crud.get_foundations(db)
    return foundations


@router.get("/stored/{foundation_id}", response_model=schemas.Foundation)
def get_stored_foundation(foundation_id: int, db: Session = Depends(get_db)):
    """Get a specific stored foundation from the database"""
    foundation = crud.get_foundation(db, foundation_id)
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
    foundations = crud.get_foundations_by_county_code(db, county_code)
    return foundations


@router.get("/stored/by-municipality/{municipality_code}", response_model=list[schemas.Foundation])
def get_stored_foundations_by_municipality(municipality_code: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by municipality code"""
    foundations = crud.get_foundations_by_municipality_code(db, municipality_code)
    return foundations


@router.get("/categories", response_model=list[str])
def get_all_categories(db: Session = Depends(get_db)):
    """Get all unique categories from the database"""
    categories = (
        db.query(models.Foundation.category)
        .distinct()
        .filter(models.Foundation.category.isnot(None))
        .all()
    )
    return [cat[0] for cat in categories]


@router.get("/categorization-status", response_model=dict)
def get_categorization_status(db: Session = Depends(get_db)):
    """Get status information about foundation categorization"""
    from sqlalchemy import func

    # Total number of foundations
    total_foundations = db.query(models.Foundation).count()

    # Uncategorized foundations
    uncategorized_foundations = (
        db.query(models.Foundation)
        .filter(
            or_(models.Foundation.category.is_(None), models.Foundation.category == "")
        )
        .count()
    )

    # Count of each category
    categories_with_counts = (
        db.query(models.Foundation.category, func.count(models.Foundation.id))
        .filter(
            models.Foundation.category.isnot(None), models.Foundation.category != ""
        )
        .group_by(models.Foundation.category)
        .all()
    )

    return {
        "total_foundations": total_foundations,
        "uncategorized_foundations": uncategorized_foundations,
        "categorized_foundations": total_foundations - uncategorized_foundations,
        "category_distribution": [
            {"category": cat, "count": count} for cat, count in categories_with_counts
        ],
    }


# Categorization endpoints
@router.post("/reset-categories", summary="Reset all foundation categories in database")
def reset_categories(db: Session = Depends(get_db)):
    """Reset all foundation categories to allow recategorization"""
    try:
        from app.foundation.categorization.categorize_foundations import (
            FoundationCategorizer,
        )

        categorizer = FoundationCategorizer()
        reset_count = categorizer.reset_categories_in_db()
        return {
            "message": "All foundation categories have been reset",
            "status": "success",
            "reset_foundations": reset_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error during category reset: {str(e)}"
        )


@router.post(
    "/categorize-db-foundations", summary="Categorize all foundations in database"
)
def categorize_db_foundations(db: Session = Depends(get_db)):
    """Trigger categorization of all foundations stored in the database"""
    try:
        from app.foundation.categorization.categorize_foundations import (
            FoundationCategorizer,
        )

        categorizer = FoundationCategorizer()
        updated_count = categorizer.categorize_foundations_in_db()
        return {
            "message": "Database foundation categorization completed",
            "status": "success",
            "updated_foundations": updated_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error during categorization: {str(e)}"
        )


@router.post("/translate-purpose", summary="Translate foundation purpose from old Swedish to modern Swedish")
def translate_purpose(translation_request: TranslationRequest):
    """
    Translate a foundation purpose from old/legalese Swedish to modern Swedish using Ollama.
    The request body should contain a 'purpose' field with the text to translate.
    """
    try:
        if not translation_request.purpose:
            raise HTTPException(
                status_code=400,
                detail="Purpose field is required for translation"
            )

        translated_purpose = ollama_translation_service.translate_purpose(translation_request.purpose)

        if translated_purpose is None:
            raise HTTPException(
                status_code=500,
                detail="Translation failed. Please try again later."
            )

        return {
            "original_purpose": translation_request.purpose,
            "translated_purpose": translated_purpose,
            "status": "success"
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions
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
    """
    Find foundations that semantically match the user's needs.
    Uses vector similarity search on translated purposes.

    Args:
        matching_request: Contains the user's needs description and optional threshold/limit

    Returns:
        List of foundations ranked by similarity score (highest first)
    """
    try:
        if not matching_request.needs or not matching_request.needs.strip():
            raise HTTPException(
                status_code=400,
                detail="Needs description is required"
            )

        # Generate embedding for user's needs
        needs_embedding = ollama_embedding_service.generate_embedding(matching_request.needs)

        if needs_embedding is None:
            raise HTTPException(
                status_code=503,
                detail="Could not generate embedding. Embedding service may be unavailable."
            )

        # Convert embedding to string format for pgvector
        embedding_str = "[" + ",".join(str(x) for x in needs_embedding) + "]"

        # Calculate threshold as cosine distance (lower is more similar)
        # Cosine similarity = 1 - cosine distance
        # If threshold is 0.5, we want similarity >= 0.5, so distance <= 0.5
        1 - matching_request.threshold

        # Query using pgvector cosine distance operator (<=>)
        # Returns foundations with embeddings, ordered by similarity
        query = text("""
            SELECT
                id,
                foundation_id,
                name,
                orgnr,
                purpose,
                translated_purpose,
                summary,
                address,
                postnr,
                postort,
                county_code,
                municipality_code,
                phone,
                co_address,
                type,
                signature,
                roles,
                business_entities,
                last_updated,
                target_groups,
                funding_areas,
                tags,
                category,
                raw_data,
                1 - (purpose_embedding <=> CAST(:embedding AS vector)) as similarity_score
            FROM foundations
            WHERE purpose_embedding IS NOT NULL
              AND 1 - (purpose_embedding <=> CAST(:embedding AS vector)) >= :threshold
            ORDER BY similarity_score DESC
            LIMIT :limit
        """)

        result = db.execute(query, {
            "embedding": embedding_str,
            "threshold": matching_request.threshold,
            "limit": matching_request.limit
        })

        rows = result.fetchall()

        import json

        def parse_json_field(value, default):
            """Parse a field that might be a JSON string or already parsed."""
            if value is None:
                return default
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default
            return value

        matched_foundations = []
        for row in rows:
            foundation = schemas.Foundation(
                id=row.id,
                foundation_id=row.foundation_id,
                name=row.name,
                orgnr=row.orgnr,
                purpose=row.purpose,
                translated_purpose=row.translated_purpose,
                summary=row.summary,
                address=row.address,
                postnr=row.postnr,
                postort=row.postort,
                county_code=row.county_code,
                municipality_code=row.municipality_code,
                phone=row.phone,
                co_address=row.co_address,
                type=row.type,
                signature=row.signature,
                roles=parse_json_field(row.roles, []),
                business_entities=parse_json_field(row.business_entities, []),
                last_updated=row.last_updated,
                target_groups=parse_json_field(row.target_groups, []),
                funding_areas=parse_json_field(row.funding_areas, []),
                tags=parse_json_field(row.tags, []),
                category=row.category,
                raw_data=parse_json_field(row.raw_data, None)
            )
            matched_foundations.append(MatchedFoundation(
                foundation=foundation,
                similarity_score=round(row.similarity_score, 4)
            ))

        return matched_foundations

    except HTTPException:
        raise
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
    """
    Find foundations that match the user's profile.
    Uses vector similarity search on generated profile text against foundation purposes.
    Optionally applies geographic filtering based on county/municipality.
    """
    from uuid import UUID

    try:
        # Get user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token")

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user's profile
        if request.profile_id:
            profile = db.query(models.Profile).filter(
                models.Profile.id == request.profile_id,
                models.Profile.user_id == user_id
            ).first()
        else:
            # Default behavior based on "default" profile
            profile = db.query(models.Profile).filter(
                models.Profile.user_id == user_id,
                models.Profile.is_default
            ).first()

            if not profile:
                 profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()

        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found. Please set up your profile first.")

        # Convert DB model to schema for text generation
        profile_schema = schemas.Profile(
            county_code=profile.county_code,
            municipality_code=profile.municipality_code,
            life_situations=profile.life_situations or [],
            health_conditions=profile.health_conditions or [],
            health_details=profile.health_details,
            occupations=profile.occupations or [],
            support_purposes=profile.support_purposes or [],
        )

        # Generate Swedish text from profile selections
        profile_text = generate_profile_text(profile_schema, include_geography=not request.use_geographic_filter)

        if not profile_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Profile is empty. Please fill in at least some information in your profile."
            )

        # Generate embedding for profile text
        profile_embedding = ollama_embedding_service.generate_embedding(profile_text)

        if profile_embedding is None:
            raise HTTPException(
                status_code=503,
                detail="Could not generate embedding. Embedding service may be unavailable."
            )

        # Convert embedding to string format for pgvector
        embedding_str = "[" + ",".join(str(x) for x in profile_embedding) + "]"

        # Build geographic filter clause
        geo_filter = ""
        geo_params = {}

        if request.use_geographic_filter and profile.county_code:
            # Filter foundations that match user's county or are for "Hela Sverige" (nationwide)
            geo_filter = "AND (county_code = :county_code OR county_code IS NULL OR county_code = '')"
            geo_params["county_code"] = profile.county_code

            if profile.municipality_code:
                # Also filter by municipality if specified
                geo_filter = "AND (municipality_code = :municipality_code OR municipality_code IS NULL OR municipality_code = '' OR county_code = :county_code)"
                geo_params["municipality_code"] = profile.municipality_code
                geo_params["county_code"] = profile.county_code

        # Query using pgvector cosine distance operator (<=>)
        query_text = f"""
            SELECT
                id,
                foundation_id,
                name,
                orgnr,
                purpose,
                translated_purpose,
                summary,
                address,
                postnr,
                postort,
                county_code,
                municipality_code,
                phone,
                co_address,
                type,
                signature,
                roles,
                business_entities,
                last_updated,
                target_groups,
                funding_areas,
                tags,
                category,
                raw_data,
                1 - (purpose_embedding <=> CAST(:embedding AS vector)) as similarity_score
            FROM foundations
            WHERE purpose_embedding IS NOT NULL
              AND 1 - (purpose_embedding <=> CAST(:embedding AS vector)) >= :threshold
              {geo_filter}
            ORDER BY similarity_score DESC
            LIMIT :limit
        """

        result = db.execute(text(query_text), {
            "embedding": embedding_str,
            "threshold": request.threshold,
            "limit": request.limit,
            **geo_params
        })

        rows = result.fetchall()

        import json

        def parse_json_field(value, default):
            """Parse a field that might be a JSON string or already parsed."""
            if value is None:
                return default
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default
            return value

        matched_foundations = []
        for row in rows:
            foundation = schemas.Foundation(
                id=row.id,
                foundation_id=row.foundation_id,
                name=row.name,
                orgnr=row.orgnr,
                purpose=row.purpose,
                translated_purpose=row.translated_purpose,
                summary=row.summary,
                address=row.address,
                postnr=row.postnr,
                postort=row.postort,
                county_code=row.county_code,
                municipality_code=row.municipality_code,
                phone=row.phone,
                co_address=row.co_address,
                type=row.type,
                signature=row.signature,
                roles=parse_json_field(row.roles, []),
                business_entities=parse_json_field(row.business_entities, []),
                last_updated=row.last_updated,
                target_groups=parse_json_field(row.target_groups, []),
                funding_areas=parse_json_field(row.funding_areas, []),
                tags=parse_json_field(row.tags, []),
                category=row.category,
                raw_data=parse_json_field(row.raw_data, None)
            )
            matched_foundations.append(MatchedFoundation(
                foundation=foundation,
                similarity_score=round(row.similarity_score, 4)
            ))

        return matched_foundations

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding matching foundations: {str(e)}"
        )
