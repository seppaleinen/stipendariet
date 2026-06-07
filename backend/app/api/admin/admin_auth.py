from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings
import secrets

# Security scheme for basic auth
security = HTTPBasic()

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Authenticate admin user using basic auth with credentials from settings
    """
    # Compare credentials securely using secrets module
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def authenticate_admin_request(request: Request):
    """
    Alternative authentication function for requests that may come from the admin page
    """
    # Get the Authorization header
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Decode the basic auth credentials
    import base64
    try:
        # Extract everything after "Basic "
        encoded_credentials = authorization.split(" ", 1)[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        
        # Verify credentials
        correct_username = secrets.compare_digest(username, settings.ADMIN_USERNAME)
        correct_password = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
        
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect admin username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return username
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )