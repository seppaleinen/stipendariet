from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: UUID
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: User


class FamilyMember(BaseModel):
    name: str
    age: int
    role: str
    occupation: Optional[str] = None
    income: Optional[str] = None
    education: Optional[str] = None
    health_status: Optional[str] = None
    additional_info: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class Profile(BaseModel):
    id: Optional[int] = None
    name: str = "My Profile"
    is_default: bool = False

    # Section 1: Geography (hard filter)
    county_code: Optional[str] = Field(default=None, alias="countyCode")
    municipality_code: Optional[str] = Field(default=None, alias="municipalityCode")

    # Section 2: Life Situation (checkboxes)
    # Options: low_income, single_parent, widow, pensioner, student, youth, unemployed
    life_situations: Optional[List[str]] = Field(default=None, alias="lifeSituations")

    # Section 3: Health & Disability
    # Options: mobility, vision_hearing, mental_health, allergy, diabetes, cancer, chronic_illness
    health_conditions: Optional[List[str]] = Field(default=None, alias="healthConditions")
    health_details: Optional[str] = Field(default=None, alias="healthDetails")

    # Section 4: Occupation & Background
    # Options: hotel_restaurant, retail, maritime, crafts, healthcare, agriculture, arts, journalism
    occupations: Optional[List[str]] = None

    # Section 5: Support Purpose
    # Options: education, financial_aid, health_care, projects, research, travel, equipment
    support_purposes: Optional[List[str]] = Field(default=None, alias="supportPurposes")

    # Legacy data from old profile format
    legacy_data: Optional[Dict[str, Any]] = Field(default=None, alias="legacyData")

    model_config = {"populate_by_name": True, "from_attributes": True}


class FoundationBase(BaseModel):
    foundation_id: int
    name: str
    orgnr: Optional[str] = None
    purpose: Optional[str] = None
    translated_purpose: Optional[str] = None  # Translated purpose from old/legalese Swedish to modern Swedish
    summary: Optional[str] = None
    address: Optional[str] = None
    postnr: Optional[str] = None
    postort: Optional[str] = None
    county_code: Optional[str] = None  # LANKOD from external API
    municipality_code: Optional[str] = None  # KOMMUNKOD from external API
    phone: Optional[str] = None  # TELEFON from external API
    co_address: Optional[str] = None  # COADRESS from external API
    type: Optional[int] = None  # TYP from external API
    signature: Optional[str] = None  # FIRMATECKNING from external API
    roles: Optional[list] = []  # ROLLER from external API (people associated with foundation)
    business_entities: Optional[list] = []  # FIRMOR from external API
    last_updated: Optional[str] = None
    target_groups: Optional[list] = []
    funding_areas: Optional[list] = []
    tags: Optional[list] = []
    category: Optional[str] = None
    raw_data: Optional[dict] = None


class Foundation(FoundationBase):
    id: int

    class Config:
        from_attributes = True


# Application schemas for foundations
class ApplicationBase(BaseModel):
    foundation_id: int
    status: Optional[str] = "draft"
    applied_at: Optional[date] = None
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    next_allowed_application_date: Optional[date] = None


class Application(ApplicationBase):
    id: int
    next_allowed_application_date: Optional[date] = None

    class Config:
        from_attributes = True


class GrantBase(BaseModel):
    name: str
    provider: str
    summary: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[str] = None
    deadline: Optional[date] = None
    cadence: Optional[str] = None
    link: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None


class GrantCreate(GrantBase):
    pass


class GrantUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[str] = None
    deadline: Optional[date] = None
    cadence: Optional[str] = None
    link: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    updated_at: Optional[date] = None


class Grant(GrantBase):
    id: int

    class Config:
        from_attributes = True


class FundingOpportunity(BaseModel):
    id: str  # Using string to accommodate prefixes like 'foundation-456'
    name: str
    provider: str
    summary: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[str] = None
    deadline: Optional[str] = (
        None  # Using string as dates are often serialized this way
    )
    cadence: Optional[str] = None
    link: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None

    class Config:
        from_attributes = True
