"""Profile model."""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.models import Base


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

    # Section 6: Self-description (the user's situation in their own words)
    self_description = Column(Text)  # Alternative matching text source

    # Legacy fields preserved for backward compatibility (migrated from old schema)
    legacy_data = Column(JSON)

    user = relationship("User", back_populates="profile")
