import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.routers import (
    admin as admin_router,
)
from app.api.v1.routers import (
    admin_password_reset,
    applications,
    auth,
    foundation_sync,
    foundations,
    foundations_api,
    funding,
    grants,
    profile,
    search,
)
from app.db.database import create_tables, get_db
from app.foundation.scheduler import init_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create FastAPI app
app = FastAPI(
    title="StipendieAssistenten Backend",
    version="1.0.0",
    description="Backend API for the Swedish Grant Assistant application",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],  # React dev server and frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(applications.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(foundations.router)
app.include_router(grants.router)
app.include_router(foundation_sync.router)
app.include_router(funding.router)
app.include_router(search.router)
app.include_router(admin_router.router)
app.include_router(foundations_api.router)
app.include_router(admin_password_reset.router)


@app.on_event("startup")
def startup_event():
    """Create database tables on startup and initialize scheduler"""
    try:
        create_tables()
        logging.info("Database tables created successfully")

        # Initialize the foundation sync scheduler
        init_scheduler()
        logging.info("Foundation sync scheduler initialized")
    except Exception as e:
        logging.error(f"Failed to initialize startup tasks: {e}")
        raise


@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "StipendieAssistenten Backend API", "version": "1.0.0"}


@app.get("/health")
@app.head("/health")
def health_check():
    """Health check endpoint with database connectivity test"""
    try:
        # Test database connectivity
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
