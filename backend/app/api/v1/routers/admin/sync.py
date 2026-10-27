"""
Admin sync endpoints for foundation and grant synchronization
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def trigger_foundation_sync_endpoint():
    """
    Endpoint to trigger foundation synchronization as a background task.
    Returns immediately with a task_id for progress polling.
    """
    try:
        logger.info("Admin triggered manual foundation synchronization")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Create a task record in the task manager
        from app.foundation.task_manager import create_task
        create_task(task_id, task_name="sync_foundations")

        # Start the sync as a background task
        from app.foundation.sync_service import sync_foundations

        def run_background_task():
            try:
                sync_foundations(task_id=task_id)
            except Exception as e:
                logger.error(f"Background sync task {task_id} failed: {e}")
                from app.foundation.task_manager import get_task
                task = get_task(task_id)
                if task:
                    task.set_error(str(e))

        # Run the background task in a separate thread
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(run_background_task)

        return {
            "status": "started",
            "message": "Foundation sync started",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Error starting foundation sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Foundation sync failed to start: {str(e)}"
        )


def get_sync_status_endpoint(task_id: str):
    """
    Endpoint to get the status of a foundation sync task
    """
    try:
        # Validate task ID format
        try:
            uuid.UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task ID format"
            )

        from app.foundation.task_manager import get_task
        task = get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

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
        raise
    except Exception as e:
        logger.error(f"Error getting sync task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync task status: {str(e)}"
        )


def trigger_grant_sync_endpoint():
    """
    Endpoint to trigger grant synchronization manually (placeholder)
    """
    try:
        logger.info("Admin triggered manual grant synchronization (not implemented)")

        return {
            "status": "success",
            "message": "Grant sync is not implemented - only foundations are currently available",
            "details": "This is a placeholder function"
        }
    except Exception as e:
        logger.error(f"Error in admin grant sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grant sync failed: {str(e)}"
        )
