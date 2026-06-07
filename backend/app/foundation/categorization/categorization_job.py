"""
Categorization job scheduler
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CategorizationJobScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Schedule the foundation categorization to run weekly on Sundays at 2 AM
        self.scheduler.add_job(
            func=self.run_categorization_job,
            trigger=CronTrigger(
                day_of_week="sun", hour=2, minute=0
            ),  # Weekly on Sunday at 2:00 AM
            id="foundation_categorization_job",
            name="Categorize foundations using Ollama",
            replace_existing=True,
        )

        logger.info(
            "Foundation categorization scheduler initialized. Job scheduled for weekly on Sundays at 2:00 AM"
        )

    def run_categorization_job(self):
        """Run the foundation categorization job"""
        logger.info("Starting foundation categorization job...")
        try:
            # Import here to avoid circular imports
            from app.foundation.categorization.categorize_foundations import (
                run_categorization_job,
            )

            # Run the categorization job synchronously
            asyncio.run(run_categorization_job())
            logger.info("Foundation categorization job completed successfully")
        except Exception as e:
            logger.error(f"Error in foundation categorization job: {str(e)}")

    def trigger_categorization_now(self):
        """Trigger categorization immediately"""
        logger.info("Manual categorization job initiated")
        # Run in a separate thread to avoid blocking
        import threading

        thread = threading.Thread(target=self.run_categorization_job)
        thread.start()
        return True

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Foundation categorization scheduler shutdown")


# Global scheduler instance
categorization_scheduler = None


def init_categorization_scheduler():
    """Initialize the categorization scheduler"""
    global categorization_scheduler
    if categorization_scheduler is None:
        categorization_scheduler = CategorizationJobScheduler()
    return categorization_scheduler


def get_categorization_scheduler():
    """Get the categorization scheduler instance"""
    global categorization_scheduler
    if categorization_scheduler is None:
        categorization_scheduler = CategorizationJobScheduler()
    return categorization_scheduler
