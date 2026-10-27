"""Grant model."""


from sqlalchemy import JSON, Column, Date, Integer, String, Text

from app.db.models import Base


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
