"""Foundation repository - data access layer for Foundation entity."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models


class FoundationRepository:
    """Repository for Foundation data access operations.

    This class encapsulates all database operations for the Foundation entity,
    providing a clean separation between data access and business logic.
    """

    def __init__(self, db: Session):
        """Initialize the repository with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_foundations_with_category_filter(
        self,
        q: str | None = None,
        category: str | None = None,
        sort: str | None = None,
    ) -> list[models.Foundation]:
        """Get all foundations with optional filtering and sorting.

        Args:
            q: Optional search query (searches name, purpose, translated_purpose, summary)
            category: Optional category filter
            sort: Optional sort field ("name" or "location")

        Returns:
            List of Foundation models matching the criteria
        """
        query = self.db.query(models.Foundation)

        if q:
            query = query.filter(
                or_(
                    models.Foundation.name.contains(q),
                    models.Foundation.purpose.contains(q),
                    models.Foundation.translated_purpose.contains(q),
                    models.Foundation.summary.contains(q),
                )
            )

        if category:
            query = query.filter(models.Foundation.category == category)

        if sort == "name":
            query = query.order_by(models.Foundation.name)
        elif sort == "location":
            query = query.order_by(models.Foundation.postort)

        return query.all()

    def get_foundations(self) -> list[models.Foundation]:
        """Get all foundations.

        Returns:
            List of all Foundation models
        """
        return self.db.query(models.Foundation).all()

    def get_foundation(self, foundation_id: int) -> models.Foundation | None:
        """Get a single foundation by foundation_id (from external API).

        Args:
            foundation_id: The external foundation ID

        Returns:
            Foundation model or None if not found
        """
        if foundation_id is None:
            return None
        return (
            self.db.query(models.Foundation)
            .filter(models.Foundation.foundation_id == foundation_id)
            .first()
        )

    def get_foundations_by_county_code(
        self, county_code: str
    ) -> list[models.Foundation]:
        """Get all foundations in a specific county by county code.

        Args:
            county_code: The county code to filter by

        Returns:
            List of Foundation models in the specified county
        """
        return (
            self.db.query(models.Foundation)
            .filter(models.Foundation.county_code == county_code)
            .all()
        )

    def get_foundations_by_municipality_code(
        self, municipality_code: str
    ) -> list[models.Foundation]:
        """Get all foundations in a specific municipality by municipality code.

        Args:
            municipality_code: The municipality code to filter by

        Returns:
            List of Foundation models in the specified municipality
        """
        return (
            self.db.query(models.Foundation)
            .filter(models.Foundation.municipality_code == municipality_code)
            .all()
        )

    def get_foundation_by_db_id(self, db_id: int) -> models.Foundation | None:
        """Get a single foundation by database ID.

        Args:
            db_id: The internal database ID

        Returns:
            Foundation model or None if not found
        """
        return self.db.query(models.Foundation).filter(models.Foundation.id == db_id).first()

    def create_or_update_foundation(
        self, foundation_data: dict
    ) -> models.Foundation:
        """Create a foundation or update if it already exists.

        Preserves translated_purpose and purpose_embedding on updates.

        Args:
            foundation_data: Dictionary containing foundation data

        Returns:
            The created or updated Foundation model
        """
        # Fields that should NOT be overwritten on update
        preserve_fields = {"translated_purpose", "purpose_embedding", "category"}

        # Check if foundation already exists using the foundation_id
        foundation_id = foundation_data.get("foundation_id")
        existing_foundation = self.get_foundation(foundation_id)

        if existing_foundation:
            # Update existing foundation
            # Only update fields that are in the foundation_data dict
            for field, value in foundation_data.items():
                # Skip preserved fields - don't overwrite translations/embeddings
                if field in preserve_fields:
                    continue
                if hasattr(existing_foundation, field):
                    setattr(existing_foundation, field, value)
            self.db.commit()
            self.db.refresh(existing_foundation)
            return existing_foundation
        else:
            # Create new foundation
            # Filter the data to only include fields that exist in the model
            valid_fields = {}
            for field, value in foundation_data.items():
                # Check if the field exists in the model
                if hasattr(models.Foundation, field):
                    valid_fields[field] = value

            db_foundation = models.Foundation(**valid_fields)
            self.db.add(db_foundation)
            self.db.commit()
            self.db.refresh(db_foundation)
            return db_foundation

    def create_foundations(
        self, foundations_data: list[dict]
    ) -> list[models.Foundation]:
        """Create/update multiple foundations in batch.

        Args:
            foundations_data: List of dictionaries containing foundation data

        Returns:
            List of created or updated Foundation models
        """
        created_foundations = []

        for foundation_data in foundations_data:
            foundation = self.create_or_update_foundation(foundation_data)
            created_foundations.append(foundation)

        return created_foundations

    def create_foundations_batch(
        self, foundations_data: list[dict]
    ) -> list[models.Foundation]:
        """Create/update multiple foundations in one transaction.

        Preserves translated_purpose and purpose_embedding on updates to avoid
        losing work from translation/embedding jobs.

        Args:
            foundations_data: List of dictionaries containing foundation data

        Returns:
            List of created or updated Foundation models
        """
        created_foundations = []

        # Fields that should NOT be overwritten on update (preserve translations/embeddings/category)
        preserve_fields = {"translated_purpose", "purpose_embedding", "category"}

        for foundation_data in foundations_data:
            foundation_id = foundation_data.get("foundation_id")
            existing = self.get_foundation(foundation_id)
            if existing:
                for field, value in foundation_data.items():
                    # Skip preserved fields - don't overwrite translations/embeddings
                    if field in preserve_fields:
                        continue
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                created_foundations.append(existing)
            else:
                valid_fields = {
                    k: v for k, v in foundation_data.items() if hasattr(models.Foundation, k)
                }
                db_foundation = models.Foundation(**valid_fields)
                self.db.add(db_foundation)
                created_foundations.append(db_foundation)

        self.db.commit()
        for foundation in created_foundations:
            self.db.refresh(foundation)

        return created_foundations

    def delete_all_foundations(self) -> int:
        """Delete all foundations from the database (useful for clean sync).

        Returns:
            Number of foundations deleted
        """
        count = self.db.query(models.Foundation).delete()
        self.db.commit()
        return count
