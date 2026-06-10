import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # nullable for OAuth users
    name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)  # Added for application compatibility
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Added for application compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # OAuth fields
    google_id = Column(String, unique=True, nullable=True, index=True)

    # Relationships
    profile = relationship("Profile", back_populates="user")
    saved_grants = relationship("SavedGrant", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class SavedGrant(Base):
    __tablename__ = "saved_grants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    grant_id = Column(String, nullable=False)  # "foundation-123" or "grant-456"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_grants")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Removed unique=True

    name = Column(String, nullable=False, default="My Profile")
    is_default = Column(Boolean, default=False)

    # Section 1: Geography (hard filter)
    county_code = Column(String)  # LANKOD - matches foundation county_code
    municipality_code = Column(String)  # KOMMUNKOD - matches foundation municipality_code

    # Section 2: Life Situation (checkboxes stored as JSON array)
    # Options: low_income, single_parent, widow, pensioner, student, youth, unemployed
    life_situations = Column(JSON)

    # Section 3: Health & Disability (checkboxes + freetext)
    # Options: mobility, vision_hearing, mental_health, allergy, diabetes, cancer, chronic_illness
    health_conditions = Column(JSON)
    health_details = Column(Text)  # Freetext for specific diagnoses

    # Section 4: Occupation & Background (multi-select)
    # Options: hotel_restaurant, retail, maritime, crafts, healthcare, agriculture, arts, journalism
    occupations = Column(JSON)

    # Section 5: Support Purpose (checkboxes)
    # Options: education, financial_aid, health_care, projects, research, travel, equipment
    support_purposes = Column(JSON)

    # Legacy fields preserved for backward compatibility (migrated from old schema)
    legacy_data = Column(JSON)

    user = relationship("User", back_populates="profile")


class Foundation(Base):
    __tablename__ = "foundations"

    id = Column(Integer, primary_key=True, index=True)
    foundation_id = Column(
        Integer, nullable=False, unique=True
    )  # From the external API
    name = Column(String, nullable=False)
    orgnr = Column(String)
    purpose = Column(Text)  # Refined purpose from ändamål
    translated_purpose = Column(Text)  # Translated purpose from old/legalese Swedish to modern Swedish
    summary = Column(Text)  # Better summary extracted from purpose
    address = Column(String)
    postnr = Column(String)
    postort = Column(String)
    county_code = Column(String)  # LANKOD from external API
    municipality_code = Column(String)  # KOMMUNKOD from external API
    phone = Column(String)  # TELEFON from external API
    co_address = Column(String)  # COADRESS from external API
    type = Column(Integer)  # TYP from external API
    signature = Column(Text)  # FIRMATECKNING from external API
    roles = Column(JSON)  # ROLLER from external API (people associated with foundation)
    business_entities = Column(JSON)  # FIRMOR from external API
    last_updated = Column(String)  # From the external API's uppdaterad field
    target_groups = Column(JSON)  # Target groups identified from purpose
    funding_areas = Column(JSON)  # Funding areas identified from purpose
    tags = Column(JSON)  # Combined tags for search and filtering
    category = Column(String)  # Main category assigned by the categorization system
    raw_data = Column(JSON)  # Store the original raw data for reference
    purpose_embedding = Column(Vector(768))  # nomic-embed-text embeddings for semantic search

    # Enrichment job control
    enrichment_status = Column(String, default="UNPROCESSED")
    enrichment_last_run = Column(DateTime, nullable=True)
    enrichment_error = Column(Text, nullable=True)

    # Enriched data (extracted by LLM from scraped website)
    website_url = Column(String, nullable=True)
    application_deadline = Column(String, nullable=True)
    application_start = Column(String, nullable=True)
    application_method = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    who_can_apply = Column(Text, nullable=True)
    enrichment_notes = Column(Text, nullable=True)

    # Relationships
    applications = relationship("Application", back_populates="foundation")
    sources = relationship("EnrichmentSource", back_populates="foundation")
    enrichment_results = relationship("EnrichmentData", back_populates="foundation")

    def __repr__(self):
        return f"<Foundation(id={self.id}, name='{self.name}', foundation_id={self.foundation_id})>"


class EnrichmentSource(Base):
    __tablename__ = "enrichment_sources"

    id = Column(Integer, primary_key=True, index=True)
    foundation_id = Column(Integer, ForeignKey("foundations.id"), index=True)
    url = Column(String, nullable=False)
    is_official = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    last_validated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    foundation = relationship("Foundation", back_populates="sources")
    pages = relationship("EnrichmentPage", back_populates="source")
    data_entries = relationship("EnrichmentData", back_populates="source")


class EnrichmentPage(Base):
    __tablename__ = "enrichment_pages"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("enrichment_sources.id"), index=True)
    url = Column(String, nullable=False)
    page_type = Column(String)  # 'homepage', 'application', 'contact', 'other'
    raw_content = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("EnrichmentSource", back_populates="pages")


class EnrichmentData(Base):
    __tablename__ = "enrichment_data"

    id = Column(Integer, primary_key=True, index=True)
    foundation_id = Column(Integer, ForeignKey("foundations.id"), index=True)
    source_id = Column(Integer, ForeignKey("enrichment_sources.id"), nullable=True)
    extracted_data = Column(JSON)  # Structured JSON from LLM
    confidence = Column(Float, default=0.0)
    extracted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    foundation = relationship("Foundation", back_populates="enrichment_results")
    source = relationship("EnrichmentSource", back_populates="data_entries")


class Grant(Base):
    __tablename__ = "grants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    summary = Column(Text)
    description = Column(Text)
    amount = Column(String)  # Can store range like "10000-50000" or specific amount
    deadline = Column(Date)
    cadence = Column(String)  # How often can apply: one-time, annual, etc.
    link = Column(String)  # URL to apply or get more info
    tags = Column(JSON)  # Array of tags for search and filtering
    category = Column(String)  # Main category for the grant
    created_at = Column(Date)
    updated_at = Column(Date)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    foundation_id = Column(Integer, ForeignKey("foundations.id"), nullable=False)
    status = Column(String, default="draft")
    applied_at = Column(Date)
    next_allowed_application_date = Column(Date)
    notes = Column(Text)
    content = Column(Text)  # Application text content
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    foundation = relationship("Foundation", back_populates="applications")
