from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    full_name: str | None = None
    is_admin: bool | None = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: UUID
    full_name: str | None = None
    is_active: bool = True
    is_admin: bool | None = False
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: User


class FamilyMember(BaseModel):
    name: str
    age: int
    role: str
    occupation: str | None = None
    income: str | None = None
    education: str | None = None
    health_status: str | None = None
    additional_info: str | None = None
    contact_info: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class Profile(BaseModel):
    id: int | None = None
    name: str = "My Profile"
    is_default: bool = False

    # Section 1: Geography (hard filter)
    county_code: str | None = Field(default=None, alias="countyCode")
    municipality_code: str | None = Field(default=None, alias="municipalityCode")

    # Section 2: Life Situation (checkboxes)
    # Options: low_income, single_parent, widow, pensioner, student, youth, unemployed
    life_situations: list[str] | None = Field(default=None, alias="lifeSituations")

    # Section 3: Health & Disability
    # Options: mobility, vision_hearing, mental_health, allergy, diabetes, cancer, chronic_illness
    health_conditions: list[str] | None = Field(default=None, alias="healthConditions")
    health_details: str | None = Field(default=None, alias="healthDetails")

    # Section 4: Occupation & Background
    # Options: hotel_restaurant, retail, maritime, crafts, healthcare, agriculture, arts, journalism
    occupations: list[str] | None = None

    # Section 5: Support Purpose
    # Options: education, financial_aid, health_care, projects, research, travel, equipment
    support_purposes: list[str] | None = Field(default=None, alias="supportPurposes")

    # Legacy data from old profile format
    legacy_data: dict[str, Any] | None = Field(default=None, alias="legacyData")

    model_config = {"populate_by_name": True, "from_attributes": True}


class FoundationBase(BaseModel):
    foundation_id: int
    name: str
    orgnr: str | None = None
    purpose: str | None = None
    translated_purpose: str | None = None  # Translated purpose from old/legalese Swedish to modern Swedish
    summary: str | None = None
    address: str | None = None
    postnr: str | None = None
    postort: str | None = None
    county_code: str | None = None  # LANKOD from external API
    municipality_code: str | None = None  # KOMMUNKOD from external API
    phone: str | None = None  # TELEFON from external API
    co_address: str | None = None  # COADRESS from external API
    type: int | None = None  # TYP from external API
    signature: str | None = None  # FIRMATECKNING from external API
    roles: list | None = []  # ROLLER from external API (people associated with foundation)
    business_entities: list | None = []  # FIRMOR from external API
    last_updated: str | None = None
    target_groups: list | None = []
    funding_areas: list | None = []
    tags: list | None = []
    category: str | None = None
    raw_data: dict | None = None


class Foundation(FoundationBase):
    id: int

    class Config:
        from_attributes = True


# Application schemas for foundations
class ApplicationBase(BaseModel):
    foundation_id: int
    status: str | None = "draft"
    applied_at: date | None = None
    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    next_allowed_application_date: date | None = None


class Application(ApplicationBase):
    id: int
    next_allowed_application_date: date | None = None

    class Config:
        from_attributes = True


class GrantBase(BaseModel):
    name: str
    provider: str
    summary: str | None = None
    description: str | None = None
    amount: str | None = None
    deadline: date | None = None
    cadence: str | None = None
    link: str | None = None
    tags: list[str] = []
    category: str | None = None
    created_at: date | None = None
    updated_at: date | None = None


class GrantCreate(GrantBase):
    pass


class GrantUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    summary: str | None = None
    description: str | None = None
    amount: str | None = None
    deadline: date | None = None
    cadence: str | None = None
    link: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    updated_at: date | None = None


class Grant(GrantBase):
    id: int

    class Config:
        from_attributes = True


class FundingOpportunity(BaseModel):
    id: str  # Using string to accommodate prefixes like 'foundation-456'
    name: str
    provider: str
    summary: str | None = None
    description: str | None = None
    amount: str | None = None
    deadline: str | None = (
        None  # Using string as dates are often serialized this way
    )
    cadence: str | None = None
    link: str | None = None
    tags: list[str] = []
    category: str | None = None

    class Config:
        from_attributes = True
