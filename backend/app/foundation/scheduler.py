import logging
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.foundation.categorization.categorization_job import (
    init_categorization_scheduler,
)
from app.foundation.sync_service import sync_foundations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FoundationSyncScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Schedule the foundation sync to run daily at 6 AM
        self.scheduler.add_job(
            func=sync_foundations,
            trigger=CronTrigger(hour=6, minute=0),  # Daily at 6:00 AM
            id="foundation_sync_job",
            name="Sync foundations from external API",
            replace_existing=True,
        )

        # Initialize categorization scheduler as well
        init_categorization_scheduler()

        logger.info(
            "Foundation sync scheduler initialized. Job scheduled for daily at 6:00 AM"
        )
        logger.info("Foundation categorization scheduler also initialized.")

    def start_sync_manually(self):
        """Trigger a manual sync"""
        logger.info("Manual sync initiated")
        # Run in a separate thread to avoid blocking
        thread = threading.Thread(target=sync_foundations)
        thread.start()
        return True

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Foundation sync scheduler shutdown")


# Global scheduler instance
scheduler = None


def init_scheduler():
    """Initialize the scheduler"""
    global scheduler
    if scheduler is None:
        scheduler = FoundationSyncScheduler()
    return scheduler


def get_scheduler():
    """Get the scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = FoundationSyncScheduler()
    return scheduler
