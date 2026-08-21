
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import schemas
from app.db.database import get_db
from app.foundation.scheduler import get_scheduler
from app.foundation.sync_service import trigger_foundation_sync

router = APIRouter(prefix="/api/foundation-sync", tags=["foundation-sync"])


@router.post("/trigger-sync")
def trigger_foundation_sync_endpoint():
    """
    Trigger a manual foundation sync.
    This endpoint allows manually triggering the foundation sync process.
    """
    try:
        success = trigger_foundation_sync()
        if success:
            return {
                "message": "Foundation sync triggered successfully",
                "status": "success",
            }
        else:
            return {"message": "Foundation sync failed", "status": "error"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error triggering foundation sync: {str(e)}"
        )


@router.get("/foundations", response_model=list[schemas.Foundation])
def get_foundations(db: Session = Depends(get_db)):
    """
    Get all stored foundations from the database.
    """
    foundations = crud.get_foundations(db)
    return foundations


@router.get("/foundations/{foundation_id}", response_model=schemas.Foundation)
def get_foundation(foundation_id: int, db: Session = Depends(get_db)):
    """
    Get a specific foundation by ID.
    """
    foundation = crud.get_foundation(db, foundation_id)
    if not foundation:
        raise HTTPException(status_code=404, detail="Foundation not found")
    return foundation


@router.get("/status")
def get_sync_status():
    """
    Get the status of the foundation sync scheduler.
    """
    try:
        scheduler = get_scheduler()
        jobs = scheduler.scheduler.get_jobs()
        job_info = []
        for job in jobs:
            job_info.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": str(job.next_run_time),
                }
            )

        return {"status": "running", "scheduled_jobs": job_info}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting scheduler status: {str(e)}"
        )


from pydantic import BaseModel


class GenerationRequest(BaseModel):
    prompt: str


@router.post("/generate-application")
def generate_application(request: GenerationRequest):
    """
    Generate an application text using the LiteLLM OpenAI-compatible API.
    This endpoint acts as a proxy to the LLM service to avoid CORS issues.
    """
    from app.services.llm_client import chat_completion, litellm_text_model

    model = litellm_text_model()

    try:
        content = chat_completion(request.prompt, timeout=60)
        if content:
            return {
                "response": content,
                "model_used": model,
            }
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error with model {model}: {str(e)}")

    raise HTTPException(
        status_code=500, detail="LLM service failed to generate content"
    )
