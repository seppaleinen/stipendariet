import argparse
import asyncio
import json
import logging

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Foundation
from app.pipeline.orchestrator import run_foundation_pipeline_task

# Configure logging so you can see exactly where the LLM or crawler is failing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_tests(limit: int = 5, foundation_id: int = None):
    db: Session = SessionLocal()
    try:
        query = db.query(Foundation)
        if foundation_id:
            logger.info(f"Looking up specific foundation ID: {foundation_id}")
            query = query.filter(Foundation.id == foundation_id)
        else:
            logger.info(f"Fetching {limit} unprocessed foundation(s)...")
            # Pull foundations that haven't naturally succeeded yet
            query = query.filter(Foundation.enrichment_status != "COMPLETED").limit(limit)

        foundations = query.all()
        if not foundations:
            logger.warning("No foundations matched criteria. Check database connection or IDs.")
            return

        logger.info(f"Starting test run for {len(foundations)} foundation(s)...")

        for f in foundations:
            logger.info("\n" + "="*60)
            logger.info(f"TESTING PIPELINE FOR: {f.name} (Org: {f.orgnr}, ID: {f.id})")
            logger.info("="*60)

            # Run the actual orchestrator chronologically
            result = await run_foundation_pipeline_task({}, f.id)

            # Provide pretty-printed results for visual manual review!
            logger.info("\n=== FINAL OUTCOME ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            logger.info("="*60 + "\n")

    except Exception:
        logger.exception("A critical error interrupted the test runner.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test runner for the new foundation pipeline.")
    parser.add_argument("--limit", type=int, default=5, help="Number of unprocessed foundations to test")
    parser.add_argument("--id", type=int, default=None, help="Specific foundation ID to explicitly test")
    args = parser.parse_args()

    asyncio.run(run_tests(limit=args.limit, foundation_id=args.id))
