import os
import time
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# PostgreSQL database URL from environment variables
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "postgres")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "stipendariet")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"


def create_engine_with_retry(max_attempts=10, delay=2):
    """Create database engine with retry logic for startup issues"""
    for attempt in range(max_attempts):
        try:
            # Create engine
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
            # Test the connection
            with engine.connect():
                pass
            print(f"Database connection established on attempt {attempt + 1}")
            return engine
        except OperationalError as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == max_attempts - 1:
                print("Max attempts reached, throwing error")
                raise e
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    # This should not be reached due to the exception in the loop, but added for safety
    raise OperationalError(
        "Could not establish database connection after retries", (), None
    )


# Create engine with retry logic
engine = create_engine_with_retry()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database"""
    from sqlalchemy import text

    from app.db.models import Base

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

    # Create admin user if it doesn't exist
    create_admin_user()


def create_admin_user():
    """Create an admin user if it doesn't exist"""
    from passlib.context import CryptContext

    from app.core.config import settings

    # Configure bcrypt for password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        """Hash a password using bcrypt. Passlib handles the 72-byte limit automatically."""
        if not password:
            return pwd_context.hash("")
        return pwd_context.hash(password)

    SessionLocal = sessionmaker(bind=engine)
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

