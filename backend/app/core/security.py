import hmac
import ipaddress
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from jose import jwt as pyjwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
bearer_scheme = HTTPBearer(auto_error=False)

# Pre-compile internal network CIDRs once at module load to avoid
# re-parsing ip_network on every request.
COMPILED_INTERNAL_NETWORKS = [
    ipaddress.ip_network(cidr, strict=False)
    for cidr in settings.INTERNAL_NETWORKS
]


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
    """Get decoded JWT payload for current user (does not fetch from DB)."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


def _is_internal_request(request: Request) -> bool:
    """Check if request comes from trusted internal network."""
    client_host = request.client.host if request.client else None
    if not client_host:
        return False

    try:
        client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False

    return any(client_ip in network for network in COMPILED_INTERNAL_NETWORKS)


def _validate_forwardauth(request: Request) -> dict[str, Any]:
    """Validate ForwardAuth headers from Authentik proxy.

    Returns synthetic admin payload if validation succeeds.
    """
    # Check internal auth token if configured
    if settings.INTERNAL_AUTH_TOKEN:
        internal_auth = request.headers.get("X-Internal-Auth", "")
        if not hmac.compare_digest(internal_auth, settings.INTERNAL_AUTH_TOKEN):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid internal auth token"
            )

    # Require request from trusted proxy network
    if not _is_internal_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request not from trusted proxy"
        )

    # Parse and validate ForwardAuth groups
    groups_header = request.headers.get("X-Forwarded-Groups", "")
    groups = [g.strip() for g in groups_header.split(",") if g.strip()]
    if settings.AUTHENTIK_ADMIN_GROUP not in groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin group membership required"
        )

    # Require email
    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Forwarded-Email required"
        )

    name = request.headers.get("X-Forwarded-User", "")

    return {
        "sub": email,
        "email": email,
        "role": "admin",
        "name": name
    }


def get_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    request: Request = None,
) -> dict[str, Any]:
    # Try JWT first
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_token(credentials.credentials)
        except HTTPException:
            # Invalid/expired JWT: fall through to ForwardAuth on exchange path
            payload = None
        else:
            if payload.get("role") != "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

            # Optional whitelist by email/username
            allowed = settings.ADMIN_EMAIL or settings.ADMIN_USERNAME
            if allowed:
                if payload.get("email") != allowed and payload.get("sub") != allowed:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access denied")

            return payload

    # No JWT or invalid JWT: try ForwardAuth only for exchange endpoint
    path = request.url.path if request else ""
    if path.rstrip("/") == "/api/auth/exchange":
        return _validate_forwardauth(request)

    # No JWT and not exchange path
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
