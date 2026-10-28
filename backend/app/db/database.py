import os
import time
from collections.abc import Generator
from typing import Callable

from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

# PostgreSQL database URL from environment variables
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "postgres")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "stipendariet")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"


def create_engine_with_retry(
    max_attempts: int = 10,
    delay: int = 2,
    sleep_fn: Callable[[float], None] = time.sleep,
    log_fn: Callable[[str], None] = print,
) -> Engine:
    """Create database engine with retry logic for startup issues"""
    for attempt in range(max_attempts):
        try:
            # Create engine
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
            # Test the connection
            with engine.connect():
                pass
            log_fn(f"Database connection established on attempt {attempt + 1}")
            return engine
        except OperationalError as e:
            log_fn(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == max_attempts - 1:
                log_fn("Max attempts reached, throwing error")
                raise e
            log_fn(f"Retrying in {delay} seconds...")
            sleep_fn(delay)

    # This should not be reached due to the exception in the loop, but added for safety
    raise OperationalError(
        "Could not establish database connection after retries", (), None
    )


# Create engine with retry logic
engine = create_engine_with_retry()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lazy re-exports to avoid circular imports
__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "create_engine_with_retry",
    "create_tables",
    "create_admin_user",
    "Base",
]


def __getattr__(name: str):
    """Lazy re-exports to avoid circular imports."""
    if name == "create_tables":
        from app.db.bootstrap import create_tables
        return create_tables
    if name == "create_admin_user":
        from app.db.bootstrap import create_admin_user
        return create_admin_user
    if name == "Base":
        from app.db.models import Base
        return Base
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
