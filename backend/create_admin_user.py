#!/usr/bin/env python3
"""
Management script for creating an admin user in the backend service

This script allows creating an admin user directly in the database.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker

from app.db.database import engine
from app.db.models import User


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def create_admin_user(email: str, password: str, name: str = "Admin"):
    """Create an admin user in the database."""
    print(f"Creating admin user with email: {email}")

    # Create a database session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print("Admin user already exists!")
            print(f"Email: {existing_user.email}")
            print(f"Name: {existing_user.name}")
            print(f"Is Admin: {existing_user.is_admin}")
            return True

        # Create new admin user
        hashed_password = hash_password(password)

        admin_user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            full_name=name,
            is_active=True,
            is_admin=True,
        )

        # Add the user to the database
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("Admin user created successfully!")
        print(f"Email: {admin_user.email}")
        print(f"Name: {admin_user.name}")
        print(f"Is Admin: {admin_user.is_admin}")
        return True

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Use the standard admin credentials if not provided as arguments
    admin_email = os.getenv("ADMIN_EMAIL", "davidbaeriksson@gmail.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "placeholder-password")
    admin_name = os.getenv("ADMIN_NAME", "Admin User")

    success = create_admin_user(admin_email, admin_password, admin_name)
    if success:
        print("\nAdmin user creation completed successfully!")
        print("You can now log in with:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
    else:
        print("\nAdmin user creation failed!")
        sys.exit(1)
