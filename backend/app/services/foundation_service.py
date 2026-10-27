"""
Foundation service layer — business logic for foundation operations.

Encapsulates business logic previously in foundations.py router, keeping
HTTP concerns only in the router. Service is unit-testable (no FastAPI imports).

Public API is unchanged — routers delegate to this service.
"""

import json
from uuid import UUID

from sqlalchemy import or_, text

from app.db import models, schemas
from app.services.embedding_service import SIMILARITY_THRESHOLD, ollama_embedding_service
from app.services.llm_translation_service import llm_translation_service


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


def translate_purpose(purpose: str) -> dict:
    """Translate a foundation purpose from old Swedish to modern Swedish using Ollama.

    Args:
        purpose: The purpose text to translate

    Returns:
        dict with original_purpose, translated_purpose, and status
    """
    if not purpose:
        return {
            "original_purpose": "",
            "translated_purpose": "",
            "status": "error",
            "detail": "Purpose field is required for translation",
        }

    try:
        translated_purpose = llm_translation_service.translate_purpose(purpose)
        if translated_purpose is None:
            return {
                "original_purpose": purpose,
                "translated_purpose": "",
                "status": "error",
                "detail": "Translation failed. Please try again later.",
            }
        return {
            "original_purpose": purpose,
            "translated_purpose": translated_purpose,
            "status": "success",
        }
    except Exception as e:
        return {
            "original_purpose": purpose,
            "translated_purpose": "",
            "status": "error",
            "detail": f"Error during translation: {str(e)}",
        }


def find_matching_foundations_with_db(needs: str, threshold: float | None = None, limit: int | None = 20, db=None) -> list:
    """Find foundations that semantically match the user's needs (with db session).

    Uses vector similarity search on translated purposes.

    Args:
        needs: User's description of their needs
        threshold: Similarity threshold (0-1), defaults to SIMILARITY_THRESHOLD
        limit: Max results, defaults to 20
        db: Database session

    Returns:
        List of dicts with foundation data and similarity_score
    """
    if not needs or not needs.strip():
        raise ValueError("Needs description is required")

    # Use default threshold if not provided
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD

    # Use default limit if not provided
    if limit is None:
        limit = 20

    # Generate embedding for user's needs
    needs_embedding = ollama_embedding_service.generate_embedding(needs)
    if needs_embedding is None:
        raise RuntimeError(
            "Could not generate embedding. Embedding service may be unavailable."
        )

    # Convert embedding to string format for pgvector
    embedding_str = "[" + ",".join(str(x) for x in needs_embedding) + "]"

    # Calculate threshold as cosine distance (lower is more similar)
    # Cosine similarity = 1 - cosine distance
    # If threshold is 0.5, we want similarity >= 0.5, so distance <= 0.5
    effective_threshold = 1 - threshold

    # Query using pgvector cosine distance operator (<=>)
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
        "threshold": effective_threshold,
        "limit": limit
    })

    rows = result.fetchall()

    results = []
    for row in rows:
        foundation_data = {
            "id": row.id,
            "foundation_id": row.foundation_id,
            "name": row.name,
            "orgnr": row.orgnr,
            "purpose": row.purpose,
            "translated_purpose": row.translated_purpose,
            "summary": row.summary,
            "address": row.address,
            "postnr": row.postnr,
            "postort": row.postort,
            "county_code": row.county_code,
            "municipality_code": row.municipality_code,
            "phone": row.phone,
            "co_address": row.co_address,
            "type": row.type,
            "signature": row.signature,
            "roles": parse_json_field(row.roles, []),
            "business_entities": parse_json_field(row.business_entities, []),
            "last_updated": row.last_updated,
            "target_groups": parse_json_field(row.target_groups, []),
            "funding_areas": parse_json_field(row.funding_areas, []),
            "tags": parse_json_field(row.tags, []),
            "category": row.category,
            "raw_data": parse_json_field(row.raw_data, None),
            "similarity_score": round(row.similarity_score, 4)
        }
        results.append(foundation_data)

    return results


def find_matching_by_profile(request, user_id: UUID, db,
                            embedding_service=None,
                            profile_text_generator=None) -> list:
    """Find foundations that match the user's profile.

    Uses vector similarity search on generated profile text against foundation purposes.
    Optionally applies geographic filtering based on county/municipality.

    Args:
        request: ProfileMatchingRequest containing filter options
        user_id: The user's UUID from the auth token
        db: Database session
        embedding_service: Embedding service instance (defaults to app.services.embedding_service)
        profile_text_generator: Profile text generator function (defaults to app.foundation.profile_text_generator)

    Returns:
        List of dicts with foundation data and similarity_score
    """
    # Use provided services or import defaults
    if embedding_service is None:
        from app.services.embedding_service import ollama_embedding_service as _embedding_service
    else:
        _embedding_service = embedding_service

    if profile_text_generator is None:
        from app.foundation.profile_text_generator import generate_profile_text as _generate_profile_text
    else:
        _generate_profile_text = profile_text_generator

    try:
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
            raise ValueError("Profile not found. Please set up your profile first.")

        # Derive the Matching text from exactly one source — never blended:
        # either the Self-description (raw free text) or the Structured selections.
        if request.use_description:
            profile_text = (profile.self_description or "").strip()
            if not profile_text:
                raise ValueError(
                    "Self-description is empty. Please write a description of your situation in your profile first."
                )
        else:
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
            profile_text = _generate_profile_text(profile_schema, include_geography=not request.use_geographic_filter)
            if not profile_text.strip():
                raise ValueError(
                    "Profile is empty. Please fill in at least some information in your profile."
                )

        # Generate embedding for profile text
        profile_embedding = _embedding_service.generate_embedding(profile_text)
        if profile_embedding is None:
            raise RuntimeError(
                "Could not generate embedding. Embedding service may be unavailable."
            )

        # Convert embedding to string format for pgvector
        embedding_str = "[" + ",".join(str(x) for x in profile_embedding) + "]"

        # Build geographic filter clause
        # parsed_service_area takes precedence over official codes when present
        geo_filter = ""
        geo_params = {}

        if request.use_geographic_filter and profile.county_code:
            geo_params["county_code"] = profile.county_code
            if profile.municipality_code:
                # Municipality filter: parsed_service_area first, then official codes
                geo_filter = """AND (
                    -- Foundation has parsed_service_area AND it is confirmed → check it (takes precedence)
                    (
                        parsed_service_area IS NOT NULL
                        AND (service_area_status IS DISTINCT FROM 'REVIEW')
                        AND (
                            parsed_service_area->>'municipality_code' = :municipality_code
                            OR parsed_service_area->>'county_code' = :county_code
                        )
                    )
                    OR
                    -- Foundation has NO usable parsed_service_area (NULL or REVIEW) → use official codes
                    (
                        (parsed_service_area IS NULL OR service_area_status = 'REVIEW')
                        AND (
                            municipality_code = :municipality_code
                            OR municipality_code IS NULL
                            OR municipality_code = ''
                            OR county_code = :county_code
                        )
                    )
                )"""
                geo_params["municipality_code"] = profile.municipality_code
            else:
                # County-only filter: parsed_service_area first, then official codes
                geo_filter = """AND (
                    -- Foundation has parsed_service_area AND it is confirmed → check it (takes precedence)
                    (
                        parsed_service_area IS NOT NULL
                        AND (service_area_status IS DISTINCT FROM 'REVIEW')
                        AND parsed_service_area->>'county_code' = :county_code
                    )
                    OR
                    -- Foundation has NO usable parsed_service_area (NULL or REVIEW) → use official codes
                    (
                        (parsed_service_area IS NULL OR service_area_status = 'REVIEW')
                        AND (
                            county_code = :county_code
                            OR county_code IS NULL
                            OR county_code = ''
                        )
                    )
                )"""

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

        results = []

        for row in rows:
            foundation_data = {
                "id": row.id,
                "foundation_id": row.foundation_id,
                "name": row.name,
                "orgnr": row.orgnr,
                "purpose": row.purpose,
                "translated_purpose": row.translated_purpose,
                "summary": row.summary,
                "address": row.address,
                "postnr": row.postnr,
                "postort": row.postort,
                "parsed_service_area": parse_json_field(row.parsed_service_area, None),
                "phone": row.phone,
                "co_address": row.co_address,
                "type": row.type,
                "signature": row.signature,
                "roles": parse_json_field(row.roles, []),
                "business_entities": parse_json_field(row.business_entities, []),
                "last_updated": row.last_updated,
                "target_groups": parse_json_field(row.target_groups, []),
                "funding_areas": parse_json_field(row.funding_areas, []),
                "tags": parse_json_field(row.tags, []),
                "category": row.category,
                "raw_data": parse_json_field(row.raw_data, None),
                "similarity_score": round(row.similarity_score, 4)
            }
            results.append(foundation_data)

        return results

    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error finding matching foundations: {str(e)}")


def reset_categories(db) -> dict:
    """Reset all foundation categories in database to allow recategorization.

    Args:
        db: Database session

    Returns:
        dict with message, status, and reset_foundations count
    """
    try:
        from app.foundation.foundation_categorization.categorize_foundations import FoundationCategorizer

        categorizer = FoundationCategorizer()
        reset_count = categorizer.reset_categories_in_db()
        return {
            "message": "All foundation categories have been reset",
            "status": "success",
            "reset_foundations": reset_count,
        }
    except Exception as e:
        raise RuntimeError(f"Error during category reset: {str(e)}")


def categorize_db_foundations(db) -> dict:
    """Trigger categorization of all foundations stored in the database.

    Args:
        db: Database session

    Returns:
        dict with message, status, and updated_foundations count
    """
    try:
        from app.foundation.foundation_categorization.categorize_foundations import FoundationCategorizer

        categorizer = FoundationCategorizer()
        updated_count = categorizer.categorize_foundations_in_db()
        return {
            "message": "Database foundation categorization completed",
            "status": "success",
            "updated_foundations": updated_count,
        }
    except Exception as e:
        raise RuntimeError(f"Error during categorization: {str(e)}")


def get_all_categories(db) -> list:
    """Get all unique categories from the database.

    Args:
        db: Database session

    Returns:
        List of category strings
    """
    categories = (
        db.query(models.Foundation.category)
        .distinct()
        .filter(models.Foundation.category.isnot(None))
        .all()
    )
    return [cat[0] for cat in categories]


def get_categorization_status(db) -> dict:
    """Get status information about foundation categorization.

    Args:
        db: Database session

    Returns:
        dict with categorization status information
    """
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
