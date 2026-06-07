#!/usr/bin/env python3
"""
Foundation Categorization Job using Ollama

This script implements a periodic job to categorize foundations
using Ollama for AI-powered classification.
"""

import asyncio
import json
import logging

# Import database URL from environment variables instead of the database module
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import requests
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker

from app.db.database import create_engine_with_retry
from app.db.models import Foundation as DBFoundation
from app.foundation_categories import (
    CATEGORY_DEFINITIONS,
    FoundationCategory,
    get_all_keywords,
)

DATABASE_URL = f"postgresql://{os.getenv('DATABASE_USER', 'postgres')}:{os.getenv('DATABASE_PASSWORD', 'postgres')}@{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '5432')}/{os.getenv('DATABASE_NAME', 'stipendariet')}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Foundation:
    id: str
    name: str
    purpose: str
    category: str = ""
    subcategory: str = ""


def get_db_session():
    """Get a database session - for internal use"""
    from sqlalchemy.orm import sessionmaker

    engine = create_engine_with_retry()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


class FoundationCategorizer:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.categories = [cat.value for cat in FoundationCategory]

    def load_foundations_from_file(self, file_path: str) -> List[Foundation]:
        """Load foundations from JSON file"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        foundations = []
        for item in data.get("STIFTELSER", []):
            stiftelse = item.get("STIFTELSE", {})
            foundation = Foundation(
                id=str(stiftelse.get("ID", "")),
                name=stiftelse.get("NAMN", ""),
                purpose=stiftelse.get("ANDAMAL", ""),
            )
            foundations.append(foundation)

        logger.info(f"Loaded {len(foundations)} foundations from {file_path}")
        return foundations

    async def categorize_foundation(
        self, session: aiohttp.ClientSession, foundation: Foundation
    ) -> Foundation:
        """Categorize a single foundation using Ollama API"""
        try:
            # Prepare the prompt for Ollama with detailed category definitions
            categories_with_descriptions = []
            for cat_enum in FoundationCategory:
                desc = CATEGORY_DEFINITIONS[cat_enum]["description"]
                categories_with_descriptions.append(f"{cat_enum.value}: {desc}")

            prompt = f"""
            Categorize the following foundation based on its purpose:

            Name: {foundation.name}
            Purpose: {foundation.purpose}

            Available categories with descriptions:
            {chr(10).join(categories_with_descriptions)}

            Keywords that help identify categories: {', '.join(get_all_keywords())}

            Please return ONLY the most appropriate category name from the list above. Do not add any explanation or extra text.
            """

            payload = {
                "model": "llama2",  # You can change this to another model if needed
                "prompt": prompt,
                "stream": False,
            }

            async with session.post(
                f"{self.ollama_url}/api/generate", json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    category = result.get("response", "").strip()

                    # Validate the category
                    valid_categories = [cat.lower() for cat in self.categories]
                    if category.lower() in valid_categories:
                        foundation.category = category
                    else:
                        # If Ollama returned something not in our list, try to match closest
                        foundation.category = self._find_closest_category(category)

                    logger.info(
                        f"Categorized '{foundation.name[:50]}...' as '{foundation.category}'"
                    )
                else:
                    logger.error(
                        f"Ollama API request failed for {foundation.name} with status {response.status}"
                    )
                    foundation.category = "Uncategorized"

        except Exception as e:
            logger.error(f"Error categorizing foundation {foundation.name}: {str(e)}")
            foundation.category = "Uncategorized"

        return foundation

    def _find_closest_category(self, response: str) -> str:
        """Find the closest matching category from the model response"""
        response_lower = response.lower()
        for category in self.categories:
            if category.lower() in response_lower:
                return category
        # If no exact match, do keyword matching
        purpose_lower = response.lower()
        category_scores = {}
        for cat_enum in FoundationCategory:
            keywords = CATEGORY_DEFINITIONS[cat_enum]["keywords"]
            score = sum(1 for keyword in keywords if keyword in purpose_lower)
            category_scores[cat_enum.value] = score

        # Return the category with the highest keyword match
        if category_scores:
            return max(category_scores, key=category_scores.get)

        return "Specialiserade Områden"  # Swedish for "Specialized Fields" - Default category

    async def categorize_foundation_test(self, foundation: Foundation) -> Foundation:
        """Test categorization without using Ollama - for development/testing"""
        # Use the new category system with keyword matching
        purpose_lower = foundation.purpose.lower() if foundation.purpose else ""
        category_scores = {}

        # Score each category based on keyword matches
        for cat_enum in FoundationCategory:
            keywords = CATEGORY_DEFINITIONS[cat_enum]["keywords"]
            score = 0
            for keyword in keywords:
                if keyword in purpose_lower:
                    # Count multiple occurrences of key terms
                    occurrences = purpose_lower.count(keyword)
                    score += occurrences
            category_scores[cat_enum.value] = score

        # Return the category with the highest score
        if category_scores and any(score > 0 for score in category_scores.values()):
            best_category = max(category_scores, key=category_scores.get)
            foundation.category = best_category
        else:
            # If no specific category matches, try general Swedish keywords
            foundation.category = self._get_general_category(purpose_lower)

        logger.info(
            f"(Test mode) Categorized '{foundation.name[:50]}...' as '{foundation.category}'"
        )
        return foundation

    def _get_general_category(self, purpose_text: str) -> str:
        """Get a general category based on common Swedish terms"""
        # Look for specific indicators in the purpose text
        if any(word in purpose_text for word in ['utbildning', 'studier', 'skola', 'lärare', 'elev', 'student', 'utbildnings']):
            return "Utbildning och Forskning"
        elif any(word in purpose_text for word in ['hälsa', 'sjuk', 'vård', 'sjukvård', 'sjuksköterska', 'läkemedel', 'medicin']):
            return "Hälso- och Sjukvård samt Medicinsk Forskning"
        elif any(word in purpose_text for word in ['barn', 'ungdom', 'fostran', 'uppfostran', 'familj']):
            return "Socialt Stöd och Vård"
        elif any(word in purpose_text for word in ['äldre', 'ålderstigna', 'åldringsvård']):
            return "Socialt Stöd och Vård"
        elif any(word in purpose_text for word in ['idrott', 'sport', 'motion', 'fotboll', 'ishockey', 'tennis', 'golf', 'badminton']):
            return "Idrotts- och Fysiska Aktiviteter"
        elif any(word in purpose_text for word in ['kultur', 'konst', 'musik', 'teater', 'museum', 'bibliotek', 'litteratur']):
            return "Kulturella Aktiviteter och Konst"
        elif any(word in purpose_text for word in ['forskning', 'vetenskap', 'vetenskaplig']):
            return "Hälso- och Sjukvård samt Medicinsk Forskning"  # or could return "Utbildning och Forskning"
        elif any(word in purpose_text for word in ['religiös', 'kyrka', 'förkyrka', 'mission', 'gud', 'präst']):
            return "Religiösa Aktiviteter"
        elif any(word in purpose_text for word in ['miljö', 'natur', 'djur', 'klimat', 'klimatförändring', 'bevarande']):
            return "Miljövård och Naturskydd"
        elif any(word in purpose_text for word in ['ekonomi', 'näringsliv', 'företag', 'affär']):
            return "Ekonomiskt och Näringslivsstöd"
        elif any(word in purpose_text for word in ['boende', 'bostad', 'hus', 'hem']):
            return "Boendestöd och Bostadshjälp"
        elif any(word in purpose_text for word in ['integration', 'invandrar', 'flykting', 'mångfald']):
            return "Socialt Stöd och Vård"
        elif any(word in purpose_text for word in ['handikapp', 'funktionsnedsättning', 'lytta', 'tillgänglighet']):
            return "Stöd till Personer med Funktionsnedsättning"
        else:
            return "Specialiserade Områden"  # Swedish translation for "Specialized Fields"

    async def categorize_foundations(
        self, foundations: List[Foundation], max_concurrent: int = 5
    ) -> List[Foundation]:
        """Categorize all foundations using Ollama"""
        logger.info(f"Starting categorization for {len(foundations)} foundations")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_categorize(session, foundation):
            async with semaphore:
                return await self.categorize_foundation(session, foundation)

        async with aiohttp.ClientSession() as session:
            tasks = [bounded_categorize(session, f) for f in foundations]
            categorized_foundations = await asyncio.gather(
                *tasks, return_exceptions=True
            )

        # Filter out any exceptions in results
        valid_foundations = []
        for f in categorized_foundations:
            if isinstance(f, Foundation):
                valid_foundations.append(f)
            elif isinstance(f, Exception):
                logger.error(f"Task failed with exception: {f}")

        logger.info(
            f"Completed categorization for {len(valid_foundations)} foundations"
        )
        return valid_foundations

    def reset_categories_in_db(self) -> int:
        """Reset all category fields in the database to empty string"""
        logger.info("Resetting all foundation categories in database...")

        db = get_db_session()
        try:
            # Reset all categories to empty string
            updated_count = db.query(DBFoundation).update({DBFoundation.category: ""})
            db.commit()
            logger.info(f"Reset {updated_count} foundations to uncategorized")
            return updated_count
        except Exception as e:
            logger.error(f"Error during category reset: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def reset_categories_in_db(self) -> int:
        """Reset all foundation categories in the database to empty string"""
        logger.info("Resetting all foundation categories in database...")

        db = get_db_session()
        try:
            # Update all foundations to have empty category
            updated_count = db.query(DBFoundation).update({DBFoundation.category: ""})
            db.commit()
            logger.info(f"Reset {updated_count} foundations to uncategorized")
            return updated_count
        except Exception as e:
            logger.error(f"Error during category reset: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def categorize_foundations_in_db(self, max_concurrent: int = 5, batch_size: int = 100, task_id: str = None) -> int:
        """Categorize all foundations stored in the database in small batches to avoid memory issues.
        
        Args:
            max_concurrent: Maximum number of concurrent categorization tasks
            batch_size: Number of foundations to process in each batch
            task_id: Optional task ID for progress tracking via task_manager
        """
        logger.info("Starting categorization of database-stored foundations...")

        # Get task for progress updates if task_id provided
        task = None
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.update_status("running")

        db = get_db_session()
        try:
            # Count uncategorized foundations
            uncategorized_count = (
                db.query(DBFoundation.id)
                .filter(
                    or_(DBFoundation.category.is_(None), DBFoundation.category == "")
                )
                .count()
            )
            logger.info(
                f"Found {uncategorized_count} uncategorized foundations in database"
            )

            if uncategorized_count == 0:
                logger.info("No foundations need categorization")
                if task:
                    task.set_result({"status": "completed", "completed": 0, "total": 0, "message": "No foundations needed categorization"})
                return 0

            # Initialize progress tracking
            if task:
                task.update_progress(0, 0, 0, uncategorized_count)

            # Process in small batches to avoid memory issues
            total_updated = 0
            failed = 0
            
            while True:
                # Fetch only the columns we need (avoid loading huge raw_data and embedding columns)
                foundations_batch = (
                    db.query(
                        DBFoundation.id,
                        DBFoundation.foundation_id,
                        DBFoundation.name,
                        DBFoundation.purpose
                    )
                    .filter(
                        or_(DBFoundation.category.is_(None), DBFoundation.category == "")
                    )
                    .limit(batch_size)
                    .all()
                )
                
                if not foundations_batch:
                    break
                    
                logger.info(f"Processing batch of {len(foundations_batch)} foundations...")

                # Convert to Foundation objects for categorization
                foundations_to_process = []
                foundation_id_to_db_id = {}  # Map foundation_id to db id for updates
                
                for row in foundations_batch:
                    db_id, foundation_id, name, purpose = row
                    foundation_id_to_db_id[foundation_id] = db_id
                    foundation = Foundation(
                        id=str(foundation_id),
                        name=(name[:100] + "..." if name and len(name) > 100 else name or ""),
                        purpose=purpose or "",
                    )
                    foundations_to_process.append(foundation)

                # Use asyncio to process foundations with test categorization
                import asyncio

                categorized_foundations = asyncio.run(
                    self._categorize_foundations_internal(
                        foundations_to_process, max_concurrent
                    )
                )

                # Update the database with categories using raw SQL for efficiency
                batch_updated = 0
                for foundation in categorized_foundations:
                    try:
                        foundation_id = int(foundation.id)
                        if foundation_id in foundation_id_to_db_id:
                            db_id = foundation_id_to_db_id[foundation_id]
                            db.query(DBFoundation).filter(DBFoundation.id == db_id).update(
                                {DBFoundation.category: foundation.category},
                                synchronize_session=False
                            )
                            batch_updated += 1
                    except Exception as e:
                        logger.error(f"Error updating foundation {foundation.id}: {e}")
                        failed += 1

                # Commit this batch
                db.commit()
                total_updated += batch_updated
                
                logger.info(f"Batch complete: {batch_updated} updated, {total_updated} total so far")
                
                # Update task progress
                if task:
                    task.update_progress(total_updated, failed, 0, uncategorized_count)

            logger.info(
                f"Successfully updated {total_updated} foundations with categories in database"
            )
            
            # Set final result
            if task:
                task.set_result({
                    "status": "completed",
                    "completed": total_updated,
                    "failed": failed,
                    "total": uncategorized_count
                })
                
            return total_updated

        except Exception as e:
            logger.error(
                f"Error during database categorization: {str(e)}", exc_info=True
            )
            db.rollback()
            raise  # Re-raise the exception so caller knows there was an error
        finally:
            db.close()

    async def _categorize_foundations_internal(
        self, foundations: List[Foundation], max_concurrent: int = 5
    ) -> List[Foundation]:
        """Internal method to categorize foundations using test mode (keyword matching)"""
        logger.info(
            f"Starting internal categorization for {len(foundations)} foundations"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_categorize_test(foundation):
            async with semaphore:
                return await self.categorize_foundation_test(foundation)

        tasks = [bounded_categorize_test(f) for f in foundations]
        categorized_foundations = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions in results
        valid_foundations = []
        for f in categorized_foundations:
            if isinstance(f, Foundation):
                valid_foundations.append(f)
            elif isinstance(f, Exception):
                logger.error(f"Task failed with exception: {f}")

        logger.info(
            f"Completed internal categorization for {len(valid_foundations)} foundations"
        )
        return valid_foundations

    def get_category_statistics(self, foundations: List[Foundation]) -> Dict[str, int]:
        """Get statistics about categories"""
        stats = {}
        for f in foundations:
            cat = f.category
            stats[cat] = stats.get(cat, 0) + 1

        return stats

    def save_results(self, foundations: List[Foundation], output_path: str):
        """Save categorized foundations to a JSON file"""
        results = []
        for f in foundations:
            results.append(
                {
                    "id": f.id,
                    "name": f.name,
                    "purpose": f.purpose,
                    "category": f.category,
                }
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved categorized foundations to {output_path}")


async def run_categorization_job(use_test_mode: bool = False):
    """Main function to run the categorization job"""
    logger.info(
        f"Starting foundation categorization job... (test mode: {use_test_mode})"
    )

    # Initialize categorizer
    categorizer = FoundationCategorizer()

    # First, categorize foundations stored in DB
    try:
        categorizer.categorize_foundations_in_db()
        logger.info("Completed database foundation categorization")
    except Exception as e:
        logger.error(f"Error in database categorization: {e}")

    # Load foundations from file
    input_file = "/Users/daveri/workspace/personal/stipendariet/backend/stiftelser_2025-11-26_1657.json"
    foundations = categorizer.load_foundations_from_file(input_file)

    if use_test_mode:
        # Use simple keyword-based categorization for testing
        logger.info("Using test mode (keyword-based categorization)")
        semaphore = asyncio.Semaphore(10)  # Allow more concurrent for test mode

        async def bounded_categorize_test(foundation):
            async with semaphore:
                return await categorizer.categorize_foundation_test(foundation)

        tasks = [
            bounded_categorize_test(f) for f in foundations[:50]
        ]  # Test with first 50
        categorized_foundations = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions in results
        valid_foundations = []
        for f in categorized_foundations:
            if isinstance(f, Foundation):
                valid_foundations.append(f)
            elif isinstance(f, Exception):
                logger.error(f"Task failed with exception: {f}")
    else:
        # Use Ollama for AI-based categorization
        categorized_foundations = await categorizer.categorize_foundations(
            foundations[:10]
        )  # Limit for testing
        valid_foundations = categorized_foundations

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/daveri/workspace/personal/stipendariet/backend/categorized_foundations_{timestamp}.json"
    categorizer.save_results(valid_foundations, output_file)

    # Print statistics
    stats = categorizer.get_category_statistics(valid_foundations)
    logger.info("Category statistics:")
    for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {category}: {count}")

    logger.info("Categorization job completed!")
