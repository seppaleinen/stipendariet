from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import schemas
from app.db.database import get_db

router = APIRouter(prefix="/api", tags=["funding"])


@router.get("/funding", response_model=List[schemas.FundingOpportunity])
def get_all_funding(db: Session = Depends(get_db)):
    """
    Get all funding opportunities (grants and foundations) from the database.
    This endpoint combines traditional grants and foundations into a unified response.
    """
    # Get grants (traditional funding)
    grants = crud.get_grants(db)
    print("Grants fetched:", len(grants))

    # Get foundations (from external API, stored in DB)
    foundations = crud.get_foundations(db)
    print("Foundations fetched:", len(foundations))

    # Convert foundations to a format similar to grants
    funding_list = []

    # Add grants directly
    for grant in grants:
        funding_list.append(
            {
                "id": f"grant-{grant.id}",
                "name": grant.name,
                "provider": grant.provider,
                "summary": grant.summary or "",
                "description": grant.description or "",
                "amount": grant.amount,
                "deadline": grant.deadline.isoformat() if grant.deadline else None,
                "cadence": grant.cadence,
                "link": grant.link,
                "tags": grant.tags if grant.tags else [],
                "category": grant.category,  # Include category for grants
            }
        )

    # Add foundations converted to grant-like format
    for foundation in foundations:
        funding_list.append(
            {
                "id": f"foundation-{foundation.id}",  # Using the db id with prefix
                "name": foundation.name,
                "provider": f"Stiftelse ({foundation.orgnr if foundation.orgnr else 'Org.nr saknas'})",
                "summary": (
                    foundation.summary or foundation.purpose[:200] + "..."
                    if foundation.purpose and len(foundation.purpose) > 200
                    else foundation.purpose or "Syfte inte tillgängligt"
                ),
                "description": foundation.purpose or "Ingen beskrivning tillgänglig",
                "amount": "Kontakta stiftelsen direkt",  # Foundations typically don't have standard amounts
                "deadline": None,
                "cadence": "Årlig/Periodisk",
                "link": f"https://stiftelser.lansstyrelsen.se/search/{foundation.foundation_id}",
                "tags": (
                    foundation.tags or [foundation.postort, "Stiftelse"]
                    if foundation.postort
                    else ["Stiftelse"]
                ),
                "category": foundation.category,
            }
        )
        print("Added foundation:", foundation)

    return funding_list


@router.get("/funding/{funding_id}", response_model=schemas.FundingOpportunity)
def get_funding_by_id(funding_id: str, db: Session = Depends(get_db)):
    """
    Get a specific funding opportunity by ID.
    Handles both grants (grant-{id}) and foundations (foundation-{id}).
    """
    if funding_id.startswith("grant-"):
        # Extract the numeric part and get the grant
        grant_id = int(funding_id.replace("grant-", ""))
        grant = crud.get_grant(db, grant_id)
        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")

        return {
            "id": f"grant-{grant.id}",
            "name": grant.name,
            "provider": grant.provider,
            "summary": grant.summary or "",
            "description": grant.description or "",
            "amount": grant.amount,
            "deadline": grant.deadline.isoformat() if grant.deadline else None,
            "cadence": grant.cadence,
            "link": grant.link,
            "tags": grant.tags if grant.tags else [],
        }

    elif funding_id.startswith("foundation-"):
        # Extract the numeric part and get the foundation
        # The id after 'foundation-' is the database id, not the foundation_id from external API
        foundation_db_id = int(funding_id.replace("foundation-", ""))
        foundation = crud.get_foundation_by_db_id(db, foundation_db_id)
        if not foundation:
            raise HTTPException(status_code=404, detail="Foundation not found")

        return {
            "id": f"foundation-{foundation.id}",
            "name": foundation.name,
            "provider": f"Stiftelse ({foundation.orgnr if foundation.orgnr else 'Org.nr saknas'})",
            "summary": (
                foundation.summary or foundation.purpose[:200] + "..."
                if foundation.purpose and len(foundation.purpose) > 200
                else foundation.purpose or "Syfte inte tillgängligt"
            ),
            "description": foundation.purpose or "Ingen beskrivning tillgänglig",
            "amount": "Kontakta stiftelsen direkt",
            "deadline": None,
            "cadence": "Periodisk/Årlig",
            "link": f"https://stiftelser.lansstyrelsen.se/search/{foundation.foundation_id}",
            "tags": (
                foundation.tags or [foundation.postort, "Stiftelse"]
                if foundation.postort
                else ["Stiftelse"]
            ),
            "category": foundation.category,
        }

    else:
        # Handle legacy numeric IDs
        try:
            grant_id = int(funding_id)
            grant = crud.get_grant(db, grant_id)
            if not grant:
                raise HTTPException(
                    status_code=404, detail="Funding opportunity not found"
                )

            return {
                "id": f"grant-{grant.id}",
                "name": grant.name,
                "provider": grant.provider,
                "summary": grant.summary or "",
                "description": grant.description or "",
                "amount": grant.amount,
                "deadline": grant.deadline.isoformat() if grant.deadline else None,
                "cadence": grant.cadence,
                "link": grant.link,
                "tags": grant.tags if grant.tags else [],
            }
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid funding ID format")
