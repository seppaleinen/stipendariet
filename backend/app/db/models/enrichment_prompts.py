"""EnrichmentPrompt model for versioned Jinja2 prompt templates."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.db.models import Base


class EnrichmentPrompt(Base):
    """Versioned prompt template for enrichment extraction."""

    __tablename__ = "enrichment_prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    version = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    is_production = Column(Boolean, default=False, nullable=False)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)
