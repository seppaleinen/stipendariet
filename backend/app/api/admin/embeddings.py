"""
Admin embedding endpoints for foundation embedding generation
"""

import logging
import threading
import uuid

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def trigger_bulk_embedding_generation_endpoint():
    """
    Endpoint to trigger bulk embedding generation for all foundations.
    Generates embeddings for foundations with translated purposes but no embeddings.
    """
    try:
        logger.info("Admin triggered bulk embedding generation")

        # Create a task ID for tracking
        task_id = str(uuid.uuid4())

        # Create task in task manager
        from app.foundation.task_manager import create_task
        create_task(task_id, task_name="bulk_embeddings")

        # Run in background thread
        def run_bulk_embeddings():
            from app.db import models
            from app.db.database import get_db
            from app.foundation.task_manager import get_task
            from app.services.embedding_service import ollama_embedding_service

            db = next(get_db())
            try:
                # Get foundations with translated_purpose but no embedding
                foundations = db.query(models.Foundation).filter(
                    models.Foundation.translated_purpose.isnot(None),
                    models.Foundation.purpose_embedding.is_(None)
                ).all()

                total = len(foundations)
                logger.info(f"Generating embeddings for {total} foundations")

                task = get_task(task_id)
                if task:
                    task.update_status("running")
                    task.update_progress(0, 0, 0, total)

                completed = 0
                failed = 0

                for foundation in foundations:
                    try:
                        embedding = ollama_embedding_service.generate_embedding(
                            foundation.translated_purpose
                        )

                        if embedding:
                            foundation.purpose_embedding = embedding
                            db.commit()
                            completed += 1
                        else:
                            failed += 1
                            logger.warning(f"Failed to generate embedding for foundation {foundation.id}")
                    except Exception as e:
                        failed += 1
                        logger.error(f"Error generating embedding for foundation {foundation.id}: {e}")

                    if task:
                        task.update_progress(completed, failed, 0, total)

                if task:
                    task.set_result({
                        "status": "completed",
                        "completed": completed,
                        "failed": failed,
                        "total": total
                    })

                logger.info(f"Bulk embedding generation completed: {completed} completed, {failed} failed")

            except Exception as e:
                logger.error(f"Error in bulk embedding generation: {e}")
                if task:
                    task.set_error(str(e))
            finally:
                db.close()

        thread = threading.Thread(target=run_bulk_embeddings)
        thread.start()

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Bulk embedding generation started in background"
        }

    except Exception as e:
        logger.error(f"Error starting bulk embedding generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start bulk embedding generation: {str(e)}"
        )


def generate_single_embedding_endpoint(foundation_id: int):
    """
    Generate embedding for a single foundation by ID.
    Useful for testing the embedding service.
    """
    try:
        logger.info(f"Admin triggered embedding generation for foundation ID: {foundation_id}")

        from app.db import models
        from app.db.database import get_db
        from app.services.embedding_service import ollama_embedding_service

        db = next(get_db())
        try:
            foundation = db.query(models.Foundation).filter(
                models.Foundation.id == foundation_id
            ).first()

            if not foundation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Foundation with ID {foundation_id} not found"
                )

            text_to_embed = foundation.translated_purpose or foundation.purpose

            if not text_to_embed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Foundation has no purpose text to embed"
                )

            embedding = ollama_embedding_service.generate_embedding(text_to_embed)

            if embedding is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Embedding generation failed - service unavailable"
                )

            # Save the embedding
            foundation.purpose_embedding = embedding
            db.commit()
            db.refresh(foundation)

            return {
                "status": "success",
                "foundation_id": foundation_id,
                "name": foundation.name,
                "embedding_dimension": len(embedding),
                "text_embedded": text_to_embed[:200] + "..." if len(text_to_embed) > 200 else text_to_embed
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating embedding for foundation {foundation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding: {str(e)}"
        )
