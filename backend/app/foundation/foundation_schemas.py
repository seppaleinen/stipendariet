
from pydantic import BaseModel, Field


class Foundation(BaseModel):
    id: int
    namn: str
    orgnrNoMinus: str
    andamal: str | None = Field(
        alias="ändamålet", default=None
    )  # Using English field name to avoid special characters
    adress: str | None = None
    postnr: str | None = None
    postort: str | None = None


class FoundationSearchResponse(BaseModel):
    uppdaterad: str
    stiftelser: list[Foundation]
