"""SavedGrant model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.models import Base


class SavedGrant(Base):
    __tablename__ = "saved_grants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    grant_id = Column(String, nullable=False)  # "foundation-123" or "grant-456"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_grants")
