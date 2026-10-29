"""Database models package — entity-specific model files.

Defines the SQLAlchemy ``Base`` and re-exports every model class so that
``from app.db.models import User`` (and similar) continues to work after the
monolithic ``models.py`` was split into per-entity modules.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.db.models.application import Application  # noqa: E402
from app.db.models.enrichment import EnrichmentData, EnrichmentPage, EnrichmentSource  # noqa: E402
from app.db.models.enrichment_prompts import EnrichmentPrompt  # noqa: E402
from app.db.models.foundation import Foundation  # noqa: E402
from app.db.models.grant import Grant  # noqa: E402
from app.db.models.profile import Profile  # noqa: E402
from app.db.models.saved_grant import SavedGrant  # noqa: E402
from app.db.models.user import User  # noqa: E402

__all__ = [
    "Base",
    "User",
    "SavedGrant",
    "Profile",
    "Foundation",
    "EnrichmentSource",
    "EnrichmentPage",
    "EnrichmentData",
    "EnrichmentPrompt",
    "Grant",
    "Application",
]
