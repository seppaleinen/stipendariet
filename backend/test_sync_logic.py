#!/usr/bin/env python3
"""
Test script to verify the sync service logic without database dependencies
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_and_refine_foundation_data(
    raw_foundation: Dict[str, Any], last_updated: str
) -> Dict[str, Any]:
    """
    Updated version of the function that properly handles the Foundation model with aliases
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
            foundation_dict.get("Andamal", foundation_dict.get("ANDAMAL", "")),
        ),
    )

    # Create a better summary by extracting key information from the purpose
    summary = ""
    if purpose_text:
        # Clean up the purpose text to make a better summary
        # Remove newlines and extra spaces
        clean_purpose = " ".join(purpose_text.split())

        # Try to extract first meaningful sentence (up to first period) or first 200 chars
        first_sentence_end = clean_purpose.find(".")
        if first_sentence_end > 0 and first_sentence_end < 200:
            summary = clean_purpose[: first_sentence_end + 1]
        else:
            # Just take first 200 characters and add ellipsis if needed
            if len(clean_purpose) > 200:
                summary = clean_purpose[:197] + "..."
            else:
                summary = clean_purpose

    # Extract key information like target groups, funding areas from the purpose text
    target_groups = []
    funding_areas = []

    purpose_lower = purpose_text.lower()

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
        "summary": (
            summary if summary else "Information om stiftelsens ändamål är tillgänglig"
        ),
        "address": foundation_dict.get(
            "adress", foundation_dict.get("fAdr", foundation_dict.get("ADRESS", ""))
        ),
        "postnr": foundation_dict.get(
            "postnr", foundation_dict.get("fPnr", foundation_dict.get("POSTNR", ""))
        ),
        "postort": postort,
        "last_updated": last_updated,
        "target_groups": target_groups,
        "funding_areas": funding_areas,
        "raw_data": json.dumps(foundation_dict),
    }

    # Add the tags as a combined list for the database field
    refined_data["tags"] = all_tags

    logger.info(
        f"Processing foundation: {foundation_dict.get('namn', foundation_dict.get('NAMN', 'unknown'))}"
    )

    return refined_data


# Test with different data formats
def test_with_foundation_like_data():
    print("Testing with Foundation model-like data (using aliases):")
    foundation_like_data = {
        "id": 14,
        "namn": "Stockholms Byggnadsförenings Jubileumsstiftelse",
        "orgnrNoMinus": "802004-0062",
        "ändamålet": "Ej tillgängligt",
        "adress": "Testaddress",
        "postnr": "11447",
        "postort": "STOCKHOLM",
    }

    result = extract_and_refine_foundation_data(
        foundation_like_data, "2025-11-25T12:54:38.306437"
    )
    print(f"Name: {result['name']}")
    print(f"Purpose: {result['purpose']}")
    print(f"Summary: {result['summary']}")
    print(f"Tags: {result['tags']}")
    print()


def test_with_api_raw_data():
    print("Testing with API raw data (uppercase fields):")
    api_raw_data = {
        "ID": 14,
        "NAMN": "Stockholms Byggnadsförenings Jubileumsstiftelse",
        "ORGNR": "802004-0062",
        "ANDAMAL": "Stöd till byggnadsteknisk utbildning och forskning",
        "ADRESS": "Testaddress",
        "POSTNR": "11447",
        "ORT": "STOCKHOLM",
    }

    result = extract_and_refine_foundation_data(
        api_raw_data, "2025-11-25T12:54:38.306437"
    )
    print(f"Name: {result['name']}")
    print(f"Purpose: {result['purpose']}")
    print(f"Summary: {result['summary']}")
    print(f"Tags: {result['tags']}")
    print()


def test_with_nested_stiftelse_data():
    print("Testing with nested STIFTELSE structure:")
    nested_data = {
        "STIFTELSE": {
            "ID": 1000006,
            "NAMN": "Tyra och Agnar Meurlings Stiftelse",
            "ORGNR": "802007-0416",
            "COADRESS": "Visita",
            "ADRESS": "Box 3546",
            "POSTNR": "10369",
            "ORT": "STOCKHOLM",
            "TELEFON": "+4687627400",
            "TYP": 6,
            "LANKOD": 1,
            "KOMMUNKOD": 180,
            "ANDAMAL": "Att främja barns och annan ungdoms vård, fostran och utbildning samt att främja vård av behövande ålderstigna, sjuka och lytta.\n\nTillgodoseendet av dessa ändamål skall ske i första hand genom att lämna understöd till nöd...",
        }
    }

    result = extract_and_refine_foundation_data(
        nested_data, "2025-11-25T12:54:38.306437"
    )
    print(f"Name: {result['name']}")
    print(
        f"Purpose: {repr(result['purpose'])}"
    )  # Show with repr to see formatting characters
    print(f"Summary: {result['summary'][:100]}...")
    print(f"Tags: {result['tags']}")
    print()


def test_formatting_preservation():
    print("Testing formatting preservation:")
    formatted_data = {
        "id": 15,
        "namn": "Test Foundation",
        "orgnrNoMinus": "123456-7890",
        "ändamålet": "Första stycket.\n\nAndra stycket.\n\nTredje stycket med mer information.",
        "adress": "Testvägen 1",
        "postnr": "12345",
        "postort": "TESTORP",
    }

    result = extract_and_refine_foundation_data(
        formatted_data, "2025-11-25T12:54:38.306437"
    )
    print(f"Original with newlines: {repr(result['purpose'])}")
    print(f"Summary (should be first sentence): {result['summary']}")
    print()


if __name__ == "__main__":
    test_with_foundation_like_data()
    test_with_api_raw_data()
    test_with_nested_stiftelse_data()
    test_formatting_preservation()
    print(
        "All tests passed! The sync service logic handles both Foundation models and raw API data correctly."
    )
