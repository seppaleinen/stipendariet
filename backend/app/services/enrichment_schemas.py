"""
Pydantic schemas for enrichment data validation.
Used to validate LLM output before persisting to database.
"""


class EnrichmentStatus:
    """Enum-like constants for enrichment job status."""
    UNPROCESSED = "UNPROCESSED"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_CANDIDATES = "NO_CANDIDATES"   # discovery returned zero URLs
    NO_DATA = "NO_DATA"               # matched sites found but all extractions returned null
    NO_VALID_SITE = "no_valid_site"   # validation rejected every candidate
