import logging
from datetime import datetime
from typing import Any

import requests

from app.foundation.foundation_schemas import FoundationSearchResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the base URL for the foundation endpoint
FOUNDATION_OPENDATA_URL = "https://stiftelser.lansstyrelsen.se/Öppendata/Json"


def fetch_foundation_opendata() -> list[dict[str, Any]] | None:
    """
    Fetch foundation data from the Öppendata endpoint which provides richer information.

    Returns:
        A list of foundation data dictionaries or None if the request fails.
    """
    try:
        # Send GET request to the Öppendata endpoint
        response = requests.get(
            url=FOUNDATION_OPENDATA_URL,
            headers={"User-Agent": "StipendieAssistenten/1.0.0"},
            timeout=30,  # 30 second timeout
        )

        # Check if the request was successful
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        logger.info(
            f"Raw response type: {type(data)}, length/content: {len(data) if isinstance(data, (list, dict)) else 'N/A'}"
        )
        logger.info(
            f"Raw response keys (if dict): {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
        )

        # Check if data is a single object wrapped in a property or if it's an array
        if isinstance(data, dict):
            # If it's a single object, look for common property names that might contain the array
            possible_keys = [
                "data",
                "stiftelser",
                "result",
                "foundations",
                "values",
                "response",
                "d",
                "STIFTELSER",
            ]
            for key in possible_keys:
                if key in data and isinstance(data[key], list):
                    logger.info(
                        f"Successfully fetched foundation data from Öppendata. Found {len(data[key])} foundations in key '{key}'"
                    )
                    return data[key]

            # If no array found in common keys, log the content for debugging
            logger.info(
                f"No array found in common keys. Single object content: {str(data)[:500]}..."
            )
            # This might be a special case - return empty array if it's not the right structure
            return []
        elif isinstance(data, list):
            # If it's already a list, return it
            logger.info(
                f"Successfully fetched foundation data from Öppendata. Found {len(data)} foundations"
            )
            return data
        else:
            # Unexpected data type
            logger.error(f"Unexpected data type from Öppendata: {type(data)}")
            return []

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Error fetching foundation data from {FOUNDATION_OPENDATA_URL}: {e}"
        )
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response from {FOUNDATION_OPENDATA_URL}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error fetching foundation data from {FOUNDATION_OPENDATA_URL}: {e}"
        )
        return None


def poll_foundations() -> FoundationSearchResponse | None:
    """
    Poll the foundation API from Öppendata endpoint for the latest foundation data.
    This function now only uses the Öppendata endpoint which contains all necessary information.

    Returns:
        A FoundationSearchResponse containing the response data or None if the request fails.
    """
    try:
        # Get data from the Öppendata endpoint (richer data)
        opendata_foundations = fetch_foundation_opendata()

        if opendata_foundations is not None and len(opendata_foundations) > 0:
            # Process the data to match the FoundationSearchResponse format
            processed_foundations = []
            for foundation in opendata_foundations:
                # Ensure foundation is a dict, not a string
                if isinstance(foundation, str):
                    logger.error(f"Skipping foundation as it's a string: {foundation}")
                    continue

                # Handle nested STIFTELSE structure if present
                foundation_data = foundation
                if "STIFTELSE" in foundation and isinstance(
                    foundation["STIFTELSE"], dict
                ):
                    foundation_data = foundation["STIFTELSE"]

                # Extract additional fields from the JSON data
                fid = foundation_data.get("ID") or foundation_data.get("id", 0)
                fnamn = foundation_data.get("NAMN") or foundation_data.get("namn", "")
                forg_nr = foundation_data.get("ORGNR") or foundation_data.get("orgnrNoMinus", "")
                fandamal = foundation_data.get("ANDAMAL") or foundation_data.get("ändamål", "")
                fadress = foundation_data.get("ADRESS") or foundation_data.get("adress", "")
                fpostnr = foundation_data.get("POSTNR") or foundation_data.get("postnr", "")
                fpostort = foundation_data.get("ORT") or foundation_data.get("postort", "")

                # Extract the additional fields from the foundation data
                county_code = foundation_data.get("LANKOD")  # County code
                municipality_code = foundation_data.get("KOMMUNKOD")  # Municipality code
                phone = foundation_data.get("TELEFON") or foundation_data.get("phone", "")
                co_address = foundation_data.get("COADRESS") or foundation_data.get("coAdress", "")
                foundation_type = foundation_data.get("TYP") or foundation_data.get("type", None)
                signature = foundation_data.get("FIRMATECKNING") or foundation_data.get("signature", "")

                # Extract roles (ROLLER) - people associated with foundation
                # NOTE: ROLLER is at the same level as STIFTELSE, not inside it!
                roles_raw = foundation.get("ROLLER", []) if "STIFTELSE" in foundation else foundation_data.get("ROLLER", [])
                roles = []
                for role_item in roles_raw:
                    if isinstance(role_item, dict) and "ROLL" in role_item:
                        role_data = role_item["ROLL"]
                        role_entry = {
                            "type": role_data.get("TYP"),
                            "name": role_data.get("NAMN"),
                            "number": role_data.get("NUMMER"),
                            "address": role_data.get("POSTADRESS"),
                            "phone": role_data.get("TELEFON"),
                            "main_responsible": role_data.get("HUVUDANSVARIG")
                        }
                        roles.append(role_entry)

                # Extract business entities (FIRMOR) - if available
                # NOTE: FIRMOR is also at the same level as STIFTELSE
                business_entities_raw = foundation.get("FIRMOR", []) if "STIFTELSE" in foundation else foundation_data.get("FIRMOR", [])
                business_entities = []
                for entity_item in business_entities_raw:
                    if isinstance(entity_item, dict) and "FIRMA" in entity_item:
                        entity_data = entity_item["FIRMA"]
                        business_entities.append({
                            "name": entity_data.get("NAMN", ""),
                            "business_activity": entity_data.get("NARINGSVERKSAMHET", "")
                        })

                processed_foundation = {
                    "id": fid,
                    "namn": fnamn,
                    "orgnrNoMinus": forg_nr,
                    "ändamålet": fandamal,
                    "adress": fadress,
                    "postnr": fpostnr,
                    "postort": fpostort,
                    "county_code": county_code,
                    "municipality_code": municipality_code,
                    "phone": phone,
                    "co_address": co_address,
                    "type": foundation_type,
                    "signature": signature,
                    "roles": roles,
                    "business_entities": business_entities
                }
                processed_foundations.append(processed_foundation)

            # Create a response object similar to the original search response
            response_data = {
                "uppdaterad": datetime.now().isoformat(),
                "stiftelser": processed_foundations,
            }

            logger.info(
                f"Successfully processed {len(processed_foundations)} foundations from Öppendata out of {len(opendata_foundations)} received"
            )
            return FoundationSearchResponse(**response_data)
        else:
            logger.error("Failed to fetch foundation data from Öppendata endpoint")
            # Also try the search endpoint as fallback
            return None

    except Exception as e:
        logger.error(f"Unexpected error polling foundations from Öppendata: {e}")
        return None


def get_foundations_by_query(
    query: str | None = None,
) -> FoundationSearchResponse | None:
    """
    Poll the foundation API with an optional search query.
    This function now fetches all data and filters locally instead of using the API search.

    Args:
        query: Optional search query to filter foundations by name or purpose

    Returns:
        A FoundationSearchResponse containing the response data or None if the request fails.
    """
    try:
        # Get all foundations using the main poll function
        all_foundations_response = poll_foundations()
        if not all_foundations_response:
            return None

        # If a query is provided, filter the results locally
        if query:
            filtered_stiftelser = []
            query_lower = query.lower()
            for f in all_foundations_response.stiftelser:
                # Check if the query exists in name or purpose (handling potentially missing fields)
                name_match = (
                    query_lower in f.namn.lower()
                    if hasattr(f, "namn") and f.namn
                    else False
                )
                purpose_match = (
                    query_lower in (f.ändamålet or "").lower()
                    if hasattr(f, "ändamålet")
                    else False
                )
                # Also check with alternative field name
                alt_purpose_match = (
                    query_lower in (getattr(f, "ändamal", "") or "").lower()
                )

                if name_match or purpose_match or alt_purpose_match:
                    filtered_stiftelser.append(f)

            # Create a new response with filtered data
            response_data = {
                "uppdaterad": all_foundations_response.uppdaterad,
                "stiftelser": filtered_stiftelser,
            }

            foundation_response = FoundationSearchResponse(**response_data)
            logger.info(
                f"Successfully filtered foundations with query '{query}'. Found {len(filtered_stiftelser)} foundations"
            )
        else:
            foundation_response = all_foundations_response
            logger.info(
                f"Retrieved all foundations. Found {len(all_foundations_response.stiftelser)} foundations"
            )

        return foundation_response

    except Exception as e:
        logger.error(f"Error filtering foundations by query: {e}")
        return None
