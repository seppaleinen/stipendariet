from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_user_payload
from app.db.database import get_db
from app.db import models, schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Configure bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    hashed_pw = hash_password(user_data.password)
    db_user = models.User(
        email=user_data.email,
        hashed_password=hashed_pw,
        name=user_data.name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_token_for_user(user: models.User, role: str = "user") -> str:
    return create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": role,
        "name": user.name or "",
    })


# --- User Endpoints ---

@router.post("/signup", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = create_user(db, payload)
    token = create_token_for_user(user)
    
    return schemas.TokenResponse(
        access_token=token,
        user=schemas.User(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    configured_admin_email = settings.ADMIN_EMAIL or "davidbaeriksson@gmail.com"  # Default to known admin
    is_configured_admin_email = payload.email in (configured_admin_email, settings.ADMIN_USERNAME)

    # Check if user exists in DB
    user = get_user_by_email(db, payload.email)

    if user:
        # User exists in DB - verify password
        password_valid = verify_password(payload.password, user.hashed_password)

        # Check if this is a configured admin trying to log in with admin password
        is_configured_admin_login = is_configured_admin_email and _verify_admin_password(payload.password)

        # Allow login if either the password matches the stored hash OR it's a configured admin with correct admin password
        if not (password_valid or is_configured_admin_login):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )

        # Determine role based on database flag or configured admin status
        role = "admin" if (user.is_admin or is_configured_admin_login) else "user"
        token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": role,
            "name": user.name or "",
        })

        return schemas.TokenResponse(
            access_token=token,
            user=schemas.User(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                is_admin=user.is_admin,  # Include is_admin in response
                created_at=user.created_at,
            ),
        )

    # User not in DB - check if this is a configured admin login and auto-create
    if is_configured_admin_email and _verify_admin_password(payload.password):
        # Auto-create admin user in database
        admin_user = models.User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            name="Admin",
            is_active=True,
            is_admin=True,  # Mark as admin
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        token = create_access_token({
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "role": "admin",
            "name": "Admin",
        })

        return schemas.TokenResponse(
            access_token=token,
            user=schemas.User(
                id=admin_user.id,
                email=admin_user.email,
                name="Admin",
                is_active=True,
                is_admin=True,  # Include is_admin in response
                created_at=admin_user.created_at,
            ),
        )

    # Neither regular user nor valid admin
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


def _verify_admin_password(password: str) -> bool:
    """Check admin password (plain text comparison only)."""
    expected = settings.ADMIN_PASSWORD
    if not expected:
        return False
    # Simple plain text comparison - ADMIN_PASSWORD should be set as plain text in env
    return password == expected


@router.get("/me", response_model=schemas.User)
def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Get current authenticated user."""
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return schemas.User(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/logout")
def logout(payload: dict = Depends(get_current_user_payload)):
    """Logout current user (token invalidation is client-side for stateless JWT)."""
    return {"message": "Logged out successfully"}


@router.get("/google")
def google_oauth_redirect():
    """Redirect to Google OAuth consent screen (stub)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth not yet implemented"
    )
