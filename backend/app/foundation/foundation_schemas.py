from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Foundation(BaseModel):
    id: int
    namn: str
    orgnrNoMinus: str
    andamal: Optional[str] = Field(
        alias="ändamålet", default=None
    )  # Using English field name to avoid special characters
    adress: Optional[str] = None
    postnr: Optional[str] = None
    postort: Optional[str] = None


class FoundationSearchResponse(BaseModel):
    uppdaterad: str
    stiftelser: List[Foundation]
