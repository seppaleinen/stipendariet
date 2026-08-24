"""
Admin password reset endpoint (admin JWT required)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.security import get_admin_user  # This requires admin access to call
from app.db import models
from app.db.database import get_db

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
