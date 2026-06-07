#!/usr/bin/env python3
"""
Management script for data-engine service

This script allows performing administrative tasks like creating an admin user.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "data-engine" / "app"))

from app.database import engine
from app.models.user import User
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def seed_admin_user():
    """Seed the database with an initial admin user."""
    print("Seeding database with admin user...")
    
    # Create a database session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.email == "davidbaeriksson@gmail.com").first()
        if existing_user:
            print("Admin user already exists!")
            print(f"Email: {existing_user.email}")
            print(f"Name: {existing_user.full_name}")
            print(f"Is Admin: {existing_user.is_admin}")
            return True

        # Create new admin user
        hashed_password = hash_password("minstlol")
        
        admin_user = User(
            email="davidbaeriksson@gmail.com",
            hashed_password=hashed_password,
            full_name="David Baeriksson",
            is_active=True,
            is_admin=True,
        )
        
        # Add the user to the database
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"Admin user created successfully!")
        print(f"Email: {admin_user.email}")
        print(f"Name: {admin_user.full_name}")
        print(f"Is Admin: {admin_user.is_admin}")
        return True
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_admin_user()
    if success:
        print("\nAdmin user seeding completed successfully!")
        print("You can now log in to the admin interface with:")
        print("  Email: davidbaeriksson@gmail.com")
        print("  Password: minstlol")
    else:
        print("\nAdmin user seeding failed!")
        sys.exit(1)