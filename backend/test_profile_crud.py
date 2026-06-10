#!/usr/bin/env python3
"""
Test script to verify the profile CRUD operations work correctly
"""
import os
import sys

# Add backend to path
sys.path.append("/Users/daveri/workspace/personal/stipendariet/backend")

# Create a temporary database for testing
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import schemas
from app.db.models import Base

# Create temporary database file
temp_db = NamedTemporaryFile(delete=False, suffix=".db")
temp_db.close()

DATABASE_URL = f"sqlite:///{temp_db.name}"

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Create a test session
db = TestingSessionLocal()


def test_profile_crud():
    from app.crud import crud

    print("Testing Profile CRUD operations...")

    # First, get profile (should be None initially)
    profile = crud.get_profile(db)
    print(f"Initial profile: {profile}")

    # Create a test profile
    test_profile = schemas.Profile(
        family_members=[
            {"name": "John Doe", "age": 35, "role": "Father"},
            {"name": "Jane Doe", "age": 32, "role": "Mother"},
            {"name": "Jimmy Doe", "age": 8, "role": "Child"},
        ],
        economic_situation="Middle class family with stable income",
        background="We are a family of four living in Stockholm",
        achievements="Successfully managed household budget despite rising costs",
        goals="Looking for educational grants for our children",
    )

    print("Saving profile...")
    saved_profile = crud.save_profile(db, test_profile)
    print(f"Saved profile ID: {saved_profile.id}")
    print(f"Saved family members: {saved_profile.family_members}")

    # Get the profile again
    retrieved_profile = crud.get_profile(db)
    print(f"Retrieved profile ID: {retrieved_profile.id}")
    print(f"Retrieved family members: {retrieved_profile.family_members}")

    # Check if the data matches
    if retrieved_profile.family_members == test_profile.family_members:
        print("✅ Profile data correctly saved and retrieved!")
    else:
        print("❌ Profile data mismatch!")

    # Update the profile with new data
    updated_profile = schemas.Profile(
        family_members=[
            {"name": "John Doe", "age": 35, "role": "Father"},
            {"name": "Jane Doe", "age": 32, "role": "Mother"},
            {"name": "Jimmy Doe", "age": 8, "role": "Child"},
            {
                "name": "Jenny Doe",
                "age": 3,
                "role": "Child",
            },  # Added a new family member
        ],
        economic_situation="Middle class family with stable income",
        background="We are a family of five (added a new baby) living in Stockholm",
        achievements="Successfully managed household budget despite rising costs",
        goals="Looking for educational grants for our children",
    )

    print("Updating profile...")
    updated_saved_profile = crud.save_profile(db, updated_profile)
    print(f"Updated profile ID: {updated_saved_profile.id}")
    print(f"Updated family members: {updated_saved_profile.family_members}")

    # Get the profile again to verify update
    updated_retrieved_profile = crud.get_profile(db)
    print(f"Updated retrieved profile ID: {updated_retrieved_profile.id}")
    print(
        f"Updated retrieved family members: {updated_retrieved_profile.family_members}"
    )

    # Check if the update worked
    if len(updated_retrieved_profile.family_members) == 4:  # Should have 4 members now
        print("✅ Profile correctly updated!")
    else:
        print("❌ Profile update failed!")

    # Close session and cleanup
    db.close()

    # Remove temp database file
    os.unlink(temp_db.name)

    print("Test completed successfully!")


if __name__ == "__main__":
    test_profile_crud()
