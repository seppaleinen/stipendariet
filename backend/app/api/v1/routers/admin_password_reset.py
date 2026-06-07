"""
Admin password reset endpoint for emergency access
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db.database import get_db
from app.db import models
from app.core.security import get_admin_user  # This requires admin access to call

logger = logging.getLogger(__name__)

# Password hashing context - matches configuration in auth.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# Emergency admin-only endpoint to reset a user's password
router = APIRouter()


@router.post("/admin/reset-user-password")
def reset_user_password(
    email: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user)  # Only accessible to admins
):
    """Emergency endpoint to reset a user's password (admin only)."""
    # For security, let's limit this to admin users only
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash the new password
    hashed_password = hash_password(new_password)
    user.hashed_password = hashed_password
    
    # Update the database
    db.commit()
    db.refresh(user)
    
    logger.info(f"Password reset for user: {email}")
    return {"message": f"Password successfully reset for {email}"}


# For emergency access when no admin is available, we can temporarily create an endpoint
@router.post("/emergency-reset-admin-password")
def emergency_reset_admin_password(
    email: str,
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Emergency endpoint for resetting admin password when normal login is not working.
    This compares the current_password to a known admin password from settings.
    """
    from app.core.config import settings
    
    # Check if the email is the admin email and current password matches the configured admin password
    if email == settings.ADMIN_EMAIL and current_password == settings.ADMIN_PASSWORD:
        # Find the user in the database
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            # If user doesn't exist, that's odd, but we'll return an error
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found in database"
            )
        
        # Hash the new password and update
        hashed_password = hash_password(new_password)
        user.hashed_password = hashed_password
        
        # Update the database
        db.commit()
        db.refresh(user)
        
        logger.info(f"Admin password reset for user: {email}")
        return {"message": f"Admin password successfully reset for {email}"}
    else:
        # If this doesn't match, they should use the normal login/password reset flow
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password does not match the configured admin password"
        )