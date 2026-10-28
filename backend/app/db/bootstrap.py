"""Bootstrap module — database initialization and schema drift handling."""
from typing import TYPE_CHECKING

from app.db.database import engine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # For type hints only  # noqa: F401


def create_tables():
    """Create all tables in the database"""
    from sqlalchemy import text  # noqa: F811

    from app.db.models import Base  # noqa: F811

    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("pgvector extension enabled")

    # Create tables based on models
    Base.metadata.create_all(bind=engine)

    # Check if the category column exists, if not, add it
    with engine.connect() as conn:
        # Check if category column exists
        result = conn.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='foundations' AND column_name='category'
        """
            )
        )

        if not result.fetchone():
            # Add the category column
            conn.execute(text("ALTER TABLE foundations ADD COLUMN category VARCHAR"))
            conn.commit()
            print("Added 'category' column to foundations table")
        else:
            print("Category column already exists in foundations table")

        # Check if the profile table has the new columns, if not, add them
        # personal_description column
        result = conn.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='profiles' AND column_name='personal_description'
        """
            )
        )

        if not result.fetchone():
            # Add the new columns to profiles table
            conn.execute(text("ALTER TABLE profiles ADD COLUMN personal_description TEXT"))
            conn.execute(text("ALTER TABLE profiles ADD COLUMN contact_information JSON"))
            conn.execute(text("ALTER TABLE profiles ADD COLUMN living_situation TEXT"))
            conn.execute(text("ALTER TABLE profiles ADD COLUMN additional_notes TEXT"))
            conn.commit()
            print("Added new columns to profiles table")
        else:
            print("New columns already exist in profiles table")

        # Check for additional new foundation columns and add them if they don't exist
        new_columns = [
            ("county_code", "VARCHAR"),
            ("municipality_code", "VARCHAR"),
            ("phone", "VARCHAR"),
            ("co_address", "VARCHAR"),
            ("type", "INTEGER"),
            ("signature", "TEXT"),
            ("roles", "JSON"),
            ("business_entities", "JSON"),
            ("translated_purpose", "TEXT"),
            ("purpose_embedding", "vector(768)"),
            ("service_area_status", "VARCHAR"),
        ]

        for col_name, col_type in new_columns:
            result = conn.execute(text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='foundations' AND column_name='{col_name}'
            """))

            if not result.fetchone():
                # Add the new column
                conn.execute(text(f"ALTER TABLE foundations ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Added '{col_name}' column to foundations table")
            else:
                print(f"'{col_name}' column already exists in foundations table")

        # Add missing columns to users table if not exists
        user_columns = [
            ("name", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP DEFAULT NOW()"),
            ("google_id", "VARCHAR"),
        ]
        for col_name, col_type in user_columns:
            result = conn.execute(text(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='{col_name}'
            """))
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Added '{col_name}' column to users table")

        # Add user_id to profiles if not exists
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='profiles' AND column_name='user_id'
        """))
        if not result.fetchone():
            conn.execute(text("ALTER TABLE profiles ADD COLUMN user_id UUID REFERENCES users(id)"))
            conn.commit()
            print("Added 'user_id' column to profiles table")

        # Add new columns to applications if not exists
        app_columns = [
            ("user_id", "UUID REFERENCES users(id)"),
            ("content", "TEXT"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP DEFAULT NOW()"),
        ]
        for col_name, col_type in app_columns:
            result = conn.execute(text(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='applications' AND column_name='{col_name}'
            """))
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE applications ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Added '{col_name}' column to applications table")

        # Check if the source_type column exists on enrichment_sources, if not, add it
        result = conn.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='enrichment_sources' AND column_name='source_type'
        """
            )
        )

        if not result.fetchone():
            # Add the source_type column
            conn.execute(text("ALTER TABLE enrichment_sources ADD COLUMN source_type VARCHAR"))
            conn.commit()
            print("Added 'source_type' column to enrichment_sources table")
        else:
            print("Source_type column already exists in enrichment_sources table")

    # Create admin user if it doesn't exist
    create_admin_user()


def create_admin_user():
    """Create an admin user if it doesn't exist"""
    from passlib.context import CryptContext  # noqa: F811
    from sqlalchemy.orm import sessionmaker  # noqa: F811

    from app.core.config import settings  # noqa: F811

    # Configure bcrypt for password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        """Hash a password using bcrypt. Passlib handles the 72-byte limit automatically."""
        if not password:
            return pwd_context.hash("")
        return pwd_context.hash(password)

    SessionLocal = sessionmaker(bind=engine)  # noqa: F811
    db = SessionLocal()

    try:
        # Get admin credentials from settings (which pull from environment variables)
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD

        # Only create admin user if both email and password are configured
        if not admin_email or not admin_password:
            print("Admin credentials not configured, skipping admin user creation")
            return

        # Check if admin user already exists in the database
        from app.db.models import User
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            print(f"Admin user already exists: {admin_email}")
            return

        # Create new admin user
        hashed_password = hash_password(admin_password)
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
            name="Admin",  # Default name for admin
            full_name="Admin User",  # Full name for admin
            is_active=True,
            is_admin=True,  # Mark as admin
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print(f"Admin user created successfully: {admin_email}")

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()

    finally:
        db.close()
