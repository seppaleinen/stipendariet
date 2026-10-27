"""Application model."""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.models import Base


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
