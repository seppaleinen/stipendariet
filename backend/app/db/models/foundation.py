"""Foundation model."""


from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.models import Base


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
    parsed_service_area = Column(JSON)  # LLM-extracted location from name/purpose text
    service_area_status = Column(String)  # NULL | 'CONFIRMED' | 'REVIEW' — contradiction check result
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
    enriched_description = Column(Text, nullable=True)  # 150+ word Swedish description for LLM citation

    # Relationships
    applications = relationship("Application", back_populates="foundation")
    sources = relationship("EnrichmentSource", back_populates="foundation")
    enrichment_results = relationship("EnrichmentData", back_populates="foundation")

    def __repr__(self):
        return f"<Foundation(id={self.id}, name='{self.name}', foundation_id={self.foundation_id})>"
