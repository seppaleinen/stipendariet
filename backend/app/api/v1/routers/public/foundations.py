# Tags are set at the endpoint level only to avoid duplication on mixed routers
# (those with both public and admin-gated endpoints). FastAPI merges router-level
# and endpoint-level tags, so a router-level tag would duplicate the endpoint tag.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
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
    category: str | None = Field(default=None, max_length=100)  # Filter by category
    county: str | None = Field(default=None, pattern=r"^(0[1-9]|1[0-9]|2[0-3])$")  # Filter by county code (Swedish LANKOD 01-23)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)  # Similarity threshold (0-1)
    limit: int | None = Field(default=None, ge=1, le=200)  # Max results

    @field_validator("threshold", mode="before")
    @classmethod
    def default_threshold(cls, v):
        return v if v is not None else SIMILARITY_THRESHOLD

    @field_validator("limit", mode="before")
    @classmethod
    def default_limit(cls, v):
        return v if v is not None else 50

    @field_validator("county", mode="before")
    @classmethod
    def validate_county(cls, v):
        if v is not None and v != "":
            # Ensure it's a valid 2-digit Swedish LANKOD (01-23)
            if not v.isdigit() or len(v) != 2 or int(v) < 1 or int(v) > 23:
                raise ValueError("County must be a 2-digit Swedish LANKOD (01-23)")
        return v


class ProfileMatchingRequest(BaseModel):
    profile_id: int | None = None  # Specific profile to match against
    use_geographic_filter: bool = True  # If True, hard filter by county/municipality
    use_description: bool = False  # If True, embed the profile's self-description instead of its structured selections
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    limit: int | None = Field(default=None, ge=1, le=200)

    @field_validator("threshold", mode="before")
    @classmethod
    def default_threshold(cls, v):
        return v if v is not None else SIMILARITY_THRESHOLD

    @field_validator("limit", mode="before")
    @classmethod
    def default_limit(cls, v):
        return v if v is not None else 20


class PublicFoundation(BaseModel):
    """Lean foundation schema for public endpoints - excludes raw_data"""
    id: int
    foundation_id: int
    name: str
    orgnr: str | None = None
    purpose: str | None = None
    translated_purpose: str | None = None
    summary: str | None = None
    address: str | None = None
    postnr: str | None = None
    postort: str | None = None
    county_code: str | None = None
    municipality_code: str | None = None
    parsed_service_area: dict | None = None
    phone: str | None = None
    co_address: str | None = None
    type: int | None = None
    signature: str | None = None
    roles: list | None = []
    business_entities: list | None = []
    last_updated: str | None = None
    target_groups: list | None = []
    funding_areas: list | None = []
    tags: list | None = []
    category: str | None = None

    class Config:
        from_attributes = True


class MatchedFoundation(BaseModel):
    foundation: PublicFoundation
    similarity_score: float


class MatchingResponse(BaseModel):
    grants: list[MatchedFoundation]
    categories: list[str]


router = APIRouter(prefix="/api/foundations")


@router.get("/", response_model=FoundationSearchResponse, tags=["foundations"])
def get_all_foundations():
    """Get all foundations by polling the external API"""
    result = poll_foundations()
    if result is None:
        raise HTTPException(
            status_code=503, detail="Could not fetch foundations from external API"
        )
    return result


@router.get("/search", response_model=FoundationSearchResponse, tags=["foundations"])
def search_foundations(query: str | None = None):
    """Search foundations by query parameter"""
    result = get_foundations_by_query(query)
    if result is None:
        raise HTTPException(
            status_code=503, detail="Could not fetch foundations from external API"
        )
    return result


# Database-stored foundations endpoints
@router.get("/stored", response_model=list[schemas.Foundation], tags=["foundations"])
def get_stored_foundations(db: Session = Depends(get_db)):
    """Get all stored foundations from the database"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations()
    return foundations


@router.get("/stored/{foundation_id}", response_model=schemas.Foundation, tags=["foundations"])
def get_stored_foundation(foundation_id: int, db: Session = Depends(get_db)):
    """Get a specific stored foundation from the database"""
    repo = FoundationRepository(db)
    foundation = repo.get_foundation(foundation_id)
    if foundation is None:
        raise HTTPException(status_code=404, detail="Foundation not found in database")
    return foundation


@router.get("/stored/by-category/{category}", response_model=list[schemas.Foundation], tags=["foundations"])
def get_stored_foundations_by_category(category: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by category"""
    foundations = (
        db.query(models.Foundation).filter(models.Foundation.category == category).all()
    )
    return foundations


@router.get("/stored/by-county/{county_code}", response_model=list[schemas.Foundation], tags=["foundations"])
def get_stored_foundations_by_county(county_code: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by county code"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations_by_county_code(county_code)
    return foundations


@router.get("/stored/by-municipality/{municipality_code}", response_model=list[schemas.Foundation], tags=["foundations"])
def get_stored_foundations_by_municipality(municipality_code: str, db: Session = Depends(get_db)):
    """Get all stored foundations from the database filtered by municipality code"""
    repo = FoundationRepository(db)
    foundations = repo.get_foundations_by_municipality_code(municipality_code)
    return foundations


@router.get("/categories", response_model=list[str], tags=["foundations"])
def get_all_categories_endpoint(db: Session = Depends(get_db)):
    """Get all unique categories from the database"""
    categories = get_all_categories(db)
    return categories


@router.get("/categorization-status", response_model=dict, tags=["foundations"])
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
    tags=["foundations"],
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


@router.post("/matching", response_model=MatchingResponse, tags=["foundations"])
def find_matching_foundations(
    matching_request: MatchingRequest,
    db: Session = Depends(get_db)
):
    """Find foundations that semantically match the user's needs.

    Uses vector similarity search on translated purposes.
    Optionally filters by category and county.

    Args:
        matching_request: Contains the user's needs description, optional category, county, threshold, and limit
    Returns:
        MatchingResponse with grants (list of foundations ranked by similarity score) and categories
    """
    try:
        from sqlalchemy import text

        # Validate needs
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

        # Use validated threshold and limit (validators handle defaults)
        threshold = matching_request.threshold
        limit = matching_request.limit

        # Build query with conditional WHERE clauses using bound parameters
        where_clauses = [
            "purpose_embedding IS NOT NULL",
            "1 - (purpose_embedding <=> CAST(:embedding AS vector)) >= :threshold"
        ]
        params = {
            "embedding": embedding_str,
            "threshold": threshold,
            "limit": limit,
        }

        # County filter (Swedish LANKOD 01-23)
        if matching_request.county:
            params["county_code"] = matching_request.county
            where_clauses.append("""(
                (parsed_service_area IS NOT NULL
                 AND (service_area_status IS DISTINCT FROM 'REVIEW')
                 AND parsed_service_area->>'county_code' = :county_code)
                OR
                ((parsed_service_area IS NULL OR service_area_status = 'REVIEW')
                 AND (county_code = :county_code OR county_code IS NULL OR county_code = ''))
            )""")

        # Category filter
        if matching_request.category:
            params["category"] = matching_request.category
            where_clauses.append("category = :category")

        # Build final query
        query = text(f"""
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
                parsed_service_area,
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
                1 - (purpose_embedding <=> CAST(:embedding AS vector)) as similarity_score
            FROM foundations
            WHERE {' AND '.join(where_clauses)}
            ORDER BY similarity_score DESC
            LIMIT :limit
        """)

        result = db.execute(query, params)
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

        matched = []
        for row in rows:
            foundation = PublicFoundation(
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
                parsed_service_area=parse_json_field(row.parsed_service_area, None),
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
            )
            matched.append(MatchedFoundation(
                foundation=foundation,
                similarity_score=round(row.similarity_score, 4)
            ))

        # Fetch distinct categories from the database for the response
        categories = get_all_categories(db)

        return MatchingResponse(grants=matched, categories=categories)

    except HTTPException:
        raise
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


@router.post("/matching-by-profile", response_model=list[MatchedFoundation], tags=["foundations"])
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
