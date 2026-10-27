"""Enrichment models: EnrichmentSource, EnrichmentPage, EnrichmentData."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.models import Base


class EnrichmentSource(Base):
    __tablename__ = "enrichment_sources"

    id = Column(Integer, primary_key=True, index=True)
    foundation_id = Column(Integer, ForeignKey("foundations.id"), index=True)
    url = Column(String, nullable=False)
    source_type = Column(String)  # 'aggregator', 'official', 'blog', 'directory'
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
