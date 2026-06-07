from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import schemas
from app.db.database import get_db

router = APIRouter(prefix="/api", tags=["generate"])


@router.post(
    "/generate-application", response_model=schemas.GenerateApplicationResponse
)
def generate_application(
    request: schemas.GenerateApplicationRequest, db: Session = Depends(get_db)
):
    """Generate a draft application email using LLM (placeholder implementation)"""

    # Verify that the grant exists
    grant = crud.get_grant(db=db, grant_id=request.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    # Placeholder LLM logic - in real implementation, this would call an LLM service
    family_members_text = ", ".join(
        [
            f"{member.name} ({member.age} år gammal, {member.role})"
            for member in request.profile.family_members
        ]
    )

    email_template = f"""
Ämne: Ansökan om {grant.name} - {grant.provider}

Jag skriver för att ansöka om stödet {grant.name} som erbjuds av {grant.provider}.

Om vår familj:
{family_members_text}

Ekonomisk Situation:
{request.profile.economic_situation}

Bakgrund:
{request.profile.background}

Prestationer:
{request.profile.achievements}

Mål:
{request.profile.goals}

Detaljer om stödet:
- Belopp: {grant.amount or 'Ej angivet'}
- Sista ansökningsdag: {grant.deadline or 'Ej angivet'}
- Sammanfattning: {grant.summary or 'Ej tillgänglig'}

Vi tror att vår familj skulle märkbart gynnas av detta stöd. Tack för er tid och övervägande.

Vänliga hälsningar,
[Er familjs namn]

---
Detta är ett förslag på e-post genererad av StipendieAssistenten. Granska och anpassa innan sändning.
""".strip()

    return schemas.GenerateApplicationResponse(email_text=email_template)
