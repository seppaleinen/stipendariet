"""EnrichmentPrompt model for versioned Jinja2 prompt templates."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from app.db.models import Base


class EnrichmentPrompt(Base):
    """Versioned prompt template for enrichment extraction."""

    __tablename__ = "enrichment_prompts"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    is_production = Column(Boolean, default=False, nullable=False)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    created_by = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint("name", "version", name="uq_prompt_name_version"),)
