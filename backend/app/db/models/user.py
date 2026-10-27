"""User model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.models import Base


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
