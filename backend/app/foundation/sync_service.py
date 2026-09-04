import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.crud import crud
from app.db import models
from app.db.database import get_db
from app.foundation.foundation_api import poll_foundations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_and_refine_foundation_data(
    raw_foundation: dict[str, Any], last_updated: str
) -> dict[str, Any]:
    """
    Extract and refine foundation data by processing the raw data with a local LLM.
    This function would typically call your local LLM to understand and structure the data.
    For now, we'll implement a smart version that extracts summaries and key information.
    """
    # Convert Pydantic model to dict if necessary
    if hasattr(raw_foundation, "dict"):
        # If it's a Pydantic model, convert it to dict with aliases for proper field names
        foundation_dict = raw_foundation.dict(by_alias=True)
    elif hasattr(raw_foundation, "model_dump"):
        # For Pydantic v2 compatibility, use model_dump
        foundation_dict = raw_foundation.model_dump(by_alias=True)
    elif hasattr(raw_foundation, "__dict__"):
        # If it has __dict__, use that
        foundation_dict = raw_foundation.__dict__
    else:
        # Otherwise, assume it's already a dict
        foundation_dict = raw_foundation

    # Extract the purpose text to create a summary
    # The Foundation model stores purpose in 'andamal' field with alias 'ändamålet'
    purpose_text = foundation_dict.get(
        "andamal",
        foundation_dict.get(
            "ändamålet",
            foundation_dict.get("Andamal", foundation_dict.get("ANDAMAL", ""))
        )
    )

    # NOTE: Translation is NOT done here anymore.
    # Foundations are persisted quickly without translation.
    # Use the "Översätt Alla Ändamål" job to translate purposes afterwards.
    translated_purpose = None

    # Create a better summary by extracting key information from the purpose (use translated if available)
    summary = ""
    purpose_for_summary = translated_purpose if translated_purpose else purpose_text

    if purpose_for_summary:
        # Clean up the purpose text to make a better summary, but preserve paragraph breaks
        # Replace multiple newlines with paragraph markers, then normalize spaces
        clean_purpose = purpose_for_summary.replace("\n\n", "  \n  \n")  # Keep paragraph breaks for markdown
        clean_purpose = " ".join(clean_purpose.split())

        # Try to extract first meaningful sentence (up to first period) or first 200 chars
        first_sentence_end = clean_purpose.find(".")
        if first_sentence_end > 0 and first_sentence_end < 200:
            summary = clean_purpose[:first_sentence_end + 1]
        else:
            # Just take first 200 characters and add ellipsis if needed
            summary = clean_purpose[:197] + "..." if len(clean_purpose) > 200 else clean_purpose

    # Extract key information like target groups, funding areas from the purpose text
    target_groups = []
    funding_areas = []

    purpose_lower = purpose_for_summary.lower() if purpose_for_summary else ""

    # Identify common target groups
    if any(
        word in purpose_lower
        for word in ["barn", "ungdom", "student", "utbildning", "skola", "elev"]
    ):
        target_groups.append("Barn och ungdom")
    if any(word in purpose_lower for word in ["äldre", "ålderstigna", "vård"]):
        target_groups.append("Äldre")
    if any(
        word in purpose_lower for word in ["sjuka", "lytta", "behövande", "nödställda"]
    ):
        target_groups.append("Sjuka eller behövande")
    if any(word in purpose_lower for word in ["idrott", "sport", "motion"]):
        target_groups.append("Idrott")
    if any(word in purpose_lower for word in ["kultur", "musik", "teater", "konst"]):
        target_groups.append("Kultur")
    if any(word in purpose_lower for word in ["forskning", "vetenskap"]):
        target_groups.append("Forskning")

    # Identify funding areas
    if any(
        word in purpose_lower
        for word in ["studie", "utbildning", "utbildnings", "läro", "skolarbete"]
    ):
        funding_areas.append("Utbildning")
    if any(word in purpose_lower for word in ["boende", "bostad", "hustru"]):
        funding_areas.append("Boende")
    if any(word in purpose_lower for word in ["resor", "studieresa", "utbytes"]):
        funding_areas.append("Resor")
    if any(word in purpose_lower for word in ["ekonomisk", "ekonomiskt", "stöd"]):
        funding_areas.append("Ekonomiskt stöd")

    # Combine target groups and funding areas for tags
    all_tags = target_groups + funding_areas
    if "Stiftelse" not in all_tags:
        all_tags.append("Stiftelse")

    # Extract city for location tag if available
    postort = foundation_dict.get(
        "postort", foundation_dict.get("Postort", foundation_dict.get("ORT", ""))
    )
    if postort and postort not in all_tags:
        all_tags.append(postort)

    # Extract the additional fields from foundation data
    county_code = foundation_dict.get("county_code") or foundation_dict.get("LANKOD")
    municipality_code = foundation_dict.get("municipality_code") or foundation_dict.get("KOMMUNKOD")
    phone = foundation_dict.get("phone") or foundation_dict.get("TELEFON", "")
    co_address = foundation_dict.get("co_address") or foundation_dict.get("COADRESS", "")
    foundation_type = foundation_dict.get("type") or foundation_dict.get("TYP", None)
    signature = foundation_dict.get("signature") or foundation_dict.get("FIRMATECKNING", "")
    roles = foundation_dict.get("roles") or foundation_dict.get("ROLLER", [])
    business_entities = foundation_dict.get("business_entities") or foundation_dict.get("FIRMOR", [])

    # Extract raw data
    refined_data = {
        "foundation_id": foundation_dict.get("id", foundation_dict.get("ID", 0)),
        "name": foundation_dict.get(
            "namn", foundation_dict.get("fNamn", foundation_dict.get("NAMN", ""))
        ),
        "orgnr": foundation_dict.get(
            "orgnrNoMinus",
            foundation_dict.get(
                "Organisationsnummer", foundation_dict.get("ORGNR", "")
            ),
        ),
        "purpose": purpose_text,
        "translated_purpose": translated_purpose,
        "summary": (
            summary if summary else "Information om stiftelsens ändamål är tillgänglig"
        ),
        "address": foundation_dict.get(
            "adress", foundation_dict.get("fAdr", foundation_dict.get("ADRESS", ""))
        ),
        "postnr": foundation_dict.get(
            "postnr", foundation_dict.get("fPnr", foundation_dict.get("POSTNR", ""))
        ),
        "postort": foundation_dict.get(
            "postort", foundation_dict.get("fPna", foundation_dict.get("ORT", ""))
        ),
        "county_code": county_code,
        "municipality_code": municipality_code,
        "phone": phone,
        "co_address": co_address,
        "type": foundation_type,
        "signature": signature,
        "roles": roles,
        "business_entities": business_entities,
        "last_updated": last_updated,
        "target_groups": target_groups,
        "funding_areas": funding_areas,
        "raw_data": json.dumps(foundation_dict),
    }

    # Add the tags as a combined list for the database field
    refined_data["tags"] = all_tags

    # In a real implementation, you would call your local LLM here to:
    # 1. Parse and understand the purpose text (which is often in Swedish)
    # 2. Extract key information like target groups, funding areas, etc.
    # 3. Clean up the address information
    # 4. Potentially extract keywords/tags

    # Placeholder for LLM processing (to be implemented)
    logger.info(f"Processing foundation: {foundation_dict.get('namn', 'unknown')}")

    return refined_data


# Regex patterns for parsing saved_grants.grant_id values, mirroring the
# issue #19 migration (abc123def456_rewrite_saved_grant_foundation_ids.py).
_FOUNDATION_GRANT_ID_RE = re.compile(r"^foundation-(\d+)$")
_GRANT_GRANT_ID_RE = re.compile(r"^grant-(\d+)$")


def _cleanup_orphan_saved_grants(db: Session) -> tuple[int, int]:
    """Delete SavedGrant rows whose grant_id no longer resolves to a live row.

    An "orphan" is one of:
      * `foundation-N` where no Foundation row has `foundation_id = N`
      * `grant-N`       where no Grant row has `id = N`

    Rows whose grant_id does not match either pattern are LEFT ALONE — they
    represent valid saved grants in some other format we don't manage here.

    Returns a (foundation_orphans_deleted, grant_orphans_deleted) tuple.
    Safe to call when there are zero orphans (no-op).
    """
    foundation_orphans = 0
    grant_orphans = 0

    # --- foundation-{N} orphans ----------------------------------------------
    # Build the set of currently-live foundation_ids (a small int list in
    # practice). Matched in Python so we don't depend on Postgres-specific
    # regex-on-text behaviour.
    live_foundation_ids = {
        fid for (fid,) in db.execute(
            text("SELECT foundation_id FROM foundations")
        ).fetchall()
    }

    foundation_candidate_rows = db.execute(
        text("SELECT id, grant_id FROM saved_grants")
    ).fetchall()

    foundation_orphan_ids = []
    for saved_id, grant_id in foundation_candidate_rows:
        if not isinstance(grant_id, str):
            continue
        m = _FOUNDATION_GRANT_ID_RE.match(grant_id)
        if not m:
            continue
        foundation_id = int(m.group(1))
        if foundation_id not in live_foundation_ids:
            foundation_orphan_ids.append(saved_id)

    if foundation_orphan_ids:
        foundation_orphans = len(foundation_orphan_ids)
        # Bind the list as a tuple of ints; SQLAlchemy expands it into
        # `IN (...)` parameters.
        db.execute(
            text("DELETE FROM saved_grants WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": foundation_orphan_ids},
        )

    # --- grant-{N} orphans ---------------------------------------------------
    # Re-read: the previous DELETE hasn't been committed yet so the second
    # SELECT still sees foundation-prefix rows that survived (live ones).
    # Grant-prefix rows are unaffected.
    live_grant_ids = {
        gid for (gid,) in db.execute(
            text("SELECT id FROM grants")
        ).fetchall()
    }

    grant_candidate_rows = db.execute(
        text("SELECT id, grant_id FROM saved_grants")
    ).fetchall()

    grant_orphan_ids = []
    for saved_id, grant_id in grant_candidate_rows:
        if not isinstance(grant_id, str):
            continue
        m = _GRANT_GRANT_ID_RE.match(grant_id)
        if not m:
            continue
        grant_id_int = int(m.group(1))
        if grant_id_int not in live_grant_ids:
            grant_orphan_ids.append(saved_id)

    if grant_orphan_ids:
        grant_orphans = len(grant_orphan_ids)
        db.execute(
            text("DELETE FROM saved_grants WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": grant_orphan_ids},
        )

    db.commit()

    logger.info(
        f"Cleaned up orphan SavedGrant rows: {foundation_orphans} foundation orphans, "
        f"{grant_orphans} grant orphans"
    )
    return foundation_orphans, grant_orphans


def sync_foundations(task_id: str = None):
    """
    Main function to sync foundations from the external API to the database.
    This function polls the API, processes the data, and persists it to the database.

    Args:
        task_id: Optional task ID for progress tracking via task_manager
    """
    logger.info("Starting foundation synchronization...")

    # Helper to update task progress
    def _update_task(completed: int, failed: int, skipped: int, total: int):
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.update_progress(completed, failed, skipped, total)

    def _set_task_running():
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.update_status("running")

    def _set_task_result(result):
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.set_result(result)

    def _set_task_error(error_msg):
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.set_error(error_msg)

    try:
        _set_task_running()

        # Get fresh data from the external API
        foundation_response = poll_foundations()
        if not foundation_response:
            logger.error("Failed to poll foundations from external API")
            _set_task_error("Failed to poll foundations from external API")
            return False

        raw_count = len(foundation_response.stiftelser)
        logger.info(f"Successfully polled {raw_count} foundations")

        # Process each foundation with LLM understanding (mocked for now)
        refined_foundations = []
        process_failed = 0
        for i, raw_foundation in enumerate(foundation_response.stiftelser):
            try:
                refined_data = extract_and_refine_foundation_data(
                    raw_foundation, foundation_response.uppdaterad
                )
                refined_foundations.append(refined_data)
            except Exception as e:
                # Extract foundation ID for error logging
                try:
                    if hasattr(raw_foundation, "dict"):
                        foundation_id = raw_foundation.dict().get("id", "unknown")
                    elif hasattr(raw_foundation, "id"):
                        foundation_id = raw_foundation.id
                    else:
                        foundation_id = "unknown"
                except Exception:
                    foundation_id = "unknown"
                logger.error(f"Error processing foundation {foundation_id}: {e}")
                process_failed += 1
                continue

            # Report progress during processing phase
            _update_task(len(refined_foundations), process_failed, 0, raw_count)

        logger.info(f"Refined {len(refined_foundations)} foundations")

        # Validate we have data before proceeding
        if len(refined_foundations) == 0:
            logger.error("No foundations returned from API - aborting sync to protect existing data")
            _set_task_error("No foundations returned from API")
            return False

        # Persist to database using safe upsert (no delete!)
        db = next(get_db())
        try:
            # Use upsert approach - this will update existing foundations and create new ones
            # WITHOUT deleting anything first, preserving translations and embeddings
            batch_size = crud.get_foundation_batch_size()
            total = len(refined_foundations)
            created_total = 0
            updated_total = 0
            persisted_total = 0

            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                batch = refined_foundations[start:end]

                # Count existing vs new for this batch
                for foundation_data in batch:
                    existing = crud.get_foundation(db, foundation_data.get("foundation_id"))
                    if existing:
                        updated_total += 1
                    else:
                        created_total += 1

                # The batch function already does upsert (update if exists, create if not)
                crud.create_foundations_batch(db, batch)
                persisted_total += len(batch)
                logger.info(f"Processed batch {start}-{end}")

                # Report progress during persist phase
                _update_task(persisted_total, process_failed, 0, total)

            logger.info(f"Sync complete: {created_total} new, {updated_total} updated (total: {total})")

            # Garbage-collect orphan SavedGrant rows now that the foundations
            # table reflects the current API state. A failure here is logged
            # but does NOT fail the sync — the cleanup is defence-in-depth
            # and will run again on the next sync.
            try:
                _cleanup_orphan_saved_grants(db)
            except Exception as cleanup_err:
                logger.error(
                    f"Orphan SavedGrant cleanup failed (sync still succeeded): {cleanup_err}"
                )

            # Categorize newly created / uncategorized foundations immediately,
            # so they don't sit uncategorized until the weekly job.
            categorized_count = 0
            try:
                from app.foundation.categorization.categorize_foundations import (
                    FoundationCategorizer,
                )
                categorizer = FoundationCategorizer()
                categorized_count = categorizer.categorize_foundations_in_db(
                    task_id=task_id
                )
                logger.info(
                    f"Sync-time categorization: {categorized_count} foundations categorized"
                )
            except Exception as e:
                logger.error(
                    f"Post-sync categorization failed (non-fatal): {e}"
                )
                # Do NOT fail the sync — sync success is independent of categorization.

            result = {
                "status": "completed",
                "created": created_total,
                "updated": updated_total,
                "failed": process_failed,
                "total": total,
                "categorized": categorized_count,
            }
            _set_task_result(result)

            return True
        except Exception as e:
            # Rollback on error - no data loss since we didn't delete first
            db.rollback()
            logger.error(f"Error persisting foundations: {e}")
            _set_task_error(f"Error persisting foundations: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error during foundation synchronization: {e}")
        _set_task_error(str(e))
        return False


def trigger_foundation_sync():
    """
    Function to trigger foundation sync manually (for HTTP request handling)
    """
    logger.info("Manual foundation synchronization triggered")
    return sync_foundations()


def translate_all_foundations_purposes(task_id: str = None, force_retranslate: bool = False):
    """
    Function to translate all existing foundation purposes in the database.
    Uses ThreadPoolExecutor for concurrent translations with rate-limit awareness.

    Args:
        task_id: Optional task ID for progress tracking
        force_retranslate: If True, retranslate all foundations even if already translated
    """
    logger.info(f"Starting translation of all foundation purposes... (force={force_retranslate})")

    try:
        from app.core.config import settings
        from app.db.database import get_db
        from app.foundation.task_manager import get_task
        from app.services.llm_translation_service import llm_translation_service

        # Get database session
        db = next(get_db())

        try:
            # Get all foundations
            foundations = db.query(models.Foundation).all()
            total_foundations = len(foundations)
            logger.info(f"Found {total_foundations} foundations to translate")

            # Filter foundations that need translation
            to_translate = []
            skipped = 0
            for foundation in foundations:
                if not foundation.purpose:
                    skipped += 1
                    continue
                if not force_retranslate and foundation.translated_purpose:
                    skipped += 1
                    continue
                to_translate.append(foundation)

            logger.info(
                f"Queued {len(to_translate)} foundations for translation, "
                f"skipped {skipped}"
            )

            processed = 0
            failed = 0

            # Update task progress if a task_id is provided
            if task_id:
                task = get_task(task_id)
                if task:
                    task.update_status("running")
                    task.update_progress(0, 0, skipped, total_foundations)

            max_workers = settings.TRANSLATION_CONCURRENCY
            delay = settings.TRANSLATION_DELAY

            def _translate_one(foundation):
                """Translate a single foundation's purpose."""
                translated = llm_translation_service.translate_purpose(foundation.purpose)
                return foundation, translated

            # Submit all translation tasks with staggered delay
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i, foundation in enumerate(to_translate):
                    future = executor.submit(_translate_one, foundation)
                    futures[future] = foundation
                    # Stagger submissions to avoid bursting the API
                    if delay > 0 and i < len(to_translate) - 1:
                        time.sleep(delay)

                commit_batch_size = 10
                batch_count = 0

                # Process completed futures
                for future in as_completed(futures):
                    foundation = futures[future]
                    try:
                        _foundation, translated_purpose = future.result()
                        if translated_purpose:
                            _foundation.translated_purpose = translated_purpose
                            processed += 1
                        else:
                            failed += 1
                            logger.warning(
                                f"Failed to translate purpose for foundation "
                                f"{_foundation.id}"
                            )
                    except Exception as e:
                        failed += 1
                        logger.error(
                            f"Error translating foundation {foundation.id}: {e}"
                        )

                    batch_count += 1

                    # Commit and update progress periodically
                    if batch_count >= commit_batch_size:
                        db.commit()
                        batch_count = 0
                        if task_id:
                            task = get_task(task_id)
                            if task:
                                task.update_progress(
                                    processed, failed, skipped, total_foundations
                                )

                # Final commit for remaining changes
                if batch_count > 0:
                    db.commit()

            # Final progress update
            if task_id:
                task = get_task(task_id)
                if task:
                    task.update_progress(processed, failed, skipped, total_foundations)

            logger.info(
                f"Translation completed: {processed} processed, {failed} failed, "
                f"{skipped} skipped out of {total_foundations} total foundations"
            )

            result = {
                "status": "completed",
                "processed": processed,
                "failed": failed,
                "skipped": skipped,
                "total": total_foundations
            }

            # Update task with final result if a task_id is provided
            if task_id:
                task = get_task(task_id)
                if task:
                    task.set_result(result)

            return result

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error during bulk foundation purpose translation: {e}")
        error_result = {
            "status": "error",
            "error": str(e)
        }

        # Update task with error if a task_id is provided
        if task_id:
            from app.foundation.task_manager import get_task
            task = get_task(task_id)
            if task:
                task.set_error(str(e))

        return error_result


def background_translate_all_foundations_purposes(task_id: str, force_retranslate: bool = False):
    """
    Background function to translate all existing foundation purposes in the database
    """
    # Call the main translation function with the task ID to track progress
    return translate_all_foundations_purposes(task_id=task_id, force_retranslate=force_retranslate)


if __name__ == "__main__":
    sync_foundations()
