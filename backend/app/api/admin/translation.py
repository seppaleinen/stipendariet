"""
Admin translation endpoints for foundation purpose translation
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def trigger_bulk_purpose_translation_endpoint(force: bool = False):
    """
    Endpoint to trigger translation of all existing foundation purposes as a background task.

    Args:
        force: If True, retranslate all foundations even if already translated
    """
    try:
        logger.info(f"Admin triggered bulk translation of all foundation purposes (force={force})")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Create a task record in the task manager
        from app.foundation.task_manager import create_task
        create_task(task_id, task_name="bulk_translation")

        # Start the translation as a background task
        from app.foundation.sync_service import background_translate_all_foundations_purposes

        def run_background_task():
            try:
                background_translate_all_foundations_purposes(task_id, force_retranslate=force)
            except Exception as e:
                logger.error(f"Background task {task_id} failed: {e}")
                from app.foundation.task_manager import get_task
                task = get_task(task_id)
                if task:
                    task.set_error(str(e))

        # Run the background task in a separate thread
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(run_background_task)
        # Don't wait for the executor to finish

        return {
            "status": "started",
            "message": "Bulk foundation purpose translation started",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Error starting bulk foundation purpose translation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start bulk foundation purpose translation: {str(e)}"
        )


def get_translation_task_status_endpoint(task_id: str):
    """
    Endpoint to get the status of a bulk foundation purpose translation task
    """
    try:
        logger.info(f"Admin requested status for translation task: {task_id}")

        # Validate task ID format
        try:
            uuid.UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task ID format"
            )

        # Get task from the task manager
        from app.foundation.task_manager import get_task
        task = get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Return task status
        return {
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "progress": task.progress,
            "total": task.total,
            "completed": task.completed,
            "failed": task.failed,
            "skipped": task.skipped,
            "estimated_remaining_seconds": task.estimated_remaining_seconds,
            "result": task.result,
            "error": task.error
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error getting translation task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get translation task status: {str(e)}"
        )


def translate_single_foundation_endpoint(foundation_id: int, model: str = None, custom_prompt: str = None):
    """
    Endpoint to translate a single foundation's purpose and save to database.
    Useful for testing the translation before running bulk translation.

    Args:
        foundation_id: The ID of the foundation to translate
        model: Optional LLM model to use (defaults to configured model)
        custom_prompt: Optional custom prompt template (use {purpose} as placeholder)
    """
    try:
        logger.info(f"Admin triggered translation for foundation ID: {foundation_id} (model={model})")

        from app.db import models
        from app.db.database import get_db
        from app.services.ollama_translation_service import ollama_translation_service

        # Get a database session
        db = next(get_db())
        try:
            # Fetch the foundation
            foundation = db.query(models.Foundation).filter(
                models.Foundation.id == foundation_id
            ).first()

            if not foundation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Foundation with ID {foundation_id} not found"
                )

            if not foundation.purpose:
                return {
                    "status": "skipped",
                    "message": "Foundation has no purpose to translate",
                    "foundation_id": foundation_id,
                    "name": foundation.name
                }

            # Check if already translated
            original_purpose = foundation.purpose
            existing_translation = foundation.translated_purpose

            # Translate the purpose with optional overrides
            translated_purpose = ollama_translation_service.translate_purpose(
                original_purpose,
                model=model,
                custom_prompt=custom_prompt
            )

            if translated_purpose is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Translation failed - Ollama service unavailable"
                )

            # Save the translated purpose
            foundation.translated_purpose = translated_purpose
            db.commit()
            db.refresh(foundation)

            return {
                "status": "success",
                "foundation_id": foundation_id,
                "name": foundation.name,
                "original_purpose": original_purpose,
                "translated_purpose": translated_purpose,
                "had_existing_translation": existing_translation is not None,
                "model_used": model or ollama_translation_service.get_default_model()
            }

        finally:
            db.close()

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error translating foundation {foundation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to translate foundation: {str(e)}"
        )


def get_translation_defaults_endpoint():
    """
    Get the default translation model and prompt template.
    Useful for populating the UI fields with current defaults.
    """
    from app.services.ollama_translation_service import ollama_translation_service

    return {
        "model": ollama_translation_service.get_default_model(),
        "prompt_template": ollama_translation_service.get_default_prompt_template()
    }
