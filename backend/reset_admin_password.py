"""
Database script to reset admin user password
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from app.db import models
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Initialize password hashing context to match the one used in the application
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plaintext password using the same method as the application."""
    return pwd_context.hash(password)

def reset_admin_password():
    """Reset the admin user password in the database."""
    print("Resetting admin user password...")
    
    # Create a database session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Find the admin user by email
        user = db.query(models.User).filter(models.User.email == "davidbaeriksson@gmail.com").first()
        
        if not user:
            print("Admin user not found in database. Are you sure the user exists?")
            return False
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Reset the password to the known working password
        new_password = "placeholder-password"
        hashed_password = hash_password(new_password)
        
        print(f"Updating password for user {user.email}...")
        
        # Update the password hash
        user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        
        print("Password successfully reset!")
        print(f"User: {user.email}")
        print(f"New password hash: {hashed_password[:20]}...")  # Show only beginning for security
        
        return True
        
    except Exception as e:
        print(f"Error resetting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = reset_admin_password()
    if success:
        print("\nAdmin password reset completed successfully!")
        print("You should now be able to log in with:")
        print("  Email: davidbaeriksson@gmail.com")
        print("  Password: placeholder-password")
    else:
        print("\nAdmin password reset failed!")
        sys.exit(1)