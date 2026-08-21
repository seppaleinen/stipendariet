import json
import logging

from pydantic import BaseModel, ValidationError

from app.pipeline.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.services.llm_client import chat_completion, strip_code_fences

logger = logging.getLogger(__name__)

class ExtractedFoundationData(BaseModel):
    contact_email: str | None = None
    contact_phone: str | None = None
    application_open: str | None = None
    application_deadline: str | None = None
    who_can_apply: str | None = None
    how_to_apply: str | None = None
    notes: str | None = None




async def extract_data_from_content(
    content: str,
    foundation_name: str,
    custom_system_prompt: str = None,
    custom_user_prompt: str = None
) -> ExtractedFoundationData | None:
    if len(content) > 6000:
        content = content[:6000] + "..."

    sys_prompt = custom_system_prompt or EXTRACTION_SYSTEM_PROMPT
    usr_prompt = custom_user_prompt or EXTRACTION_USER_PROMPT

    prompt = sys_prompt.format(foundation_name=foundation_name) + "\n" + usr_prompt.format(content=content)

    try:
        raw_response = chat_completion(prompt, temperature=0.1)
        if raw_response:
            logger.info(f"Extraction LLM raw response for {foundation_name}: {raw_response}")
            data = json.loads(strip_code_fences(raw_response))

            # Filter to only known fields to avoid Pydantic validation errors
            known_fields = ExtractedFoundationData.model_fields.keys()
            filtered_data = {k: v for k, v in data.items() if k in known_fields}

            extracted = ExtractedFoundationData(**filtered_data)

            # Check if we actually got anything useful
            values = [v for v in filtered_data.values() if v]
            if not values:
                logger.warning(f"Extraction returned all-null result for {foundation_name}")
                return None

            logger.info(f"Extracted {len(values)} fields for {foundation_name}: {filtered_data}")
            return extracted

    except json.JSONDecodeError as e:
        logger.error(f"Extraction LLM returned invalid JSON for {foundation_name}: {e}")
    except ValidationError as e:
        logger.error(f"Extraction data failed validation for {foundation_name}: {e}")
    except Exception as e:
        logger.error(f"Extraction LLM failed for {foundation_name}: {e}")

    return None
