"""
Arq worker entrypoint.

This worker processes background tasks from the Redis/Dragonfly queue.
Run with: arq app.workers.enrichment_worker.WorkerSettings
"""
import logging
from arq.connections import RedisSettings

from app.core.config import settings
from app.pipeline.orchestrator import run_foundation_pipeline_task

logger = logging.getLogger(__name__)

def parse_redis_url(url: str) -> RedisSettings:
    """Parse Redis URL into ArqRedisSettings."""
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0) if parsed.path else 0,
    )

class WorkerSettings:
    """Arq worker configuration."""
    
    functions = [run_foundation_pipeline_task]
    
    redis_settings = parse_redis_url(
        getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
    )
    
    # Worker settings
    max_jobs = 5  # Max concurrent jobs
    job_timeout = 300  # 5 minutes per job
    
    # Retry settings — arq retries when the task raises an exception
    max_tries = 3
    retry_delay = 60  # 1 minute between retries
    
    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Reset any foundations stuck in PROCESSING (e.g. from a previous worker crash)."""
        logger.info("Enrichment worker started")
        try:
            from datetime import datetime, timedelta
            from app.db.database import SessionLocal
            from app.db.models import Foundation

            cutoff = datetime.utcnow() - timedelta(minutes=30)
            with SessionLocal() as db:
                stuck = (
                    db.query(Foundation)
                    .filter(
                        Foundation.enrichment_status == "PROCESSING",
                        Foundation.enrichment_last_run < cutoff,
                    )
                    .all()
                )
                if stuck:
                    for f in stuck:
                        f.enrichment_status = "UNPROCESSED"
                        f.enrichment_error = "Reset by worker startup: previous run stalled"
                    db.commit()
                    logger.warning(f"Reset {len(stuck)} stalled PROCESSING foundations to UNPROCESSED")
                else:
                    logger.info("No stalled PROCESSING foundations found")
        except Exception as e:
            logger.error(f"Error during startup PROCESSING reset: {e}")
    
    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Called when worker shuts down."""
        logger.info("Enrichment worker shutting down")
