
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
    Generate an application text using the Ollama API.
    This endpoint acts as a proxy to the Ollama service to avoid CORS issues.
    """
    # List of models to try in order of preference - gemma3:12b is now the preferred model
    models_to_try = [
        "gemma3:12b",
        "qwen3:8b",
        "qwen3:14b",
        "llama3.1:latest",
        "llama3:latest",
        "mistral:latest",
    ]

    for model in models_to_try:
        try:
            # Call the Ollama API
            response = requests.post(
                "https://ollama.labb.site/api/generate",
                json={"model": model, "prompt": request.prompt, "stream": False},
                headers={"Content-Type": "application/json"},
                timeout=60,  # 60 second timeout
            )

            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                return {
                    "response": result.get("response", result.get("Response", "")),
                    "model_used": model,
                }

        except requests.exceptions.RequestException as e:
            # Log the error but try the next model
            print(f"Model {model} failed: {str(e)}")
            continue
        except Exception as e:
            # Log unexpected errors but try the next model
            print(f"Unexpected error with model {model}: {str(e)}")
            continue

    # If all models fail, return an error
    raise HTTPException(
        status_code=500, detail="All available Ollama models failed to generate content"
    )
