import json
import logging

from app.pipeline.prompts import VALIDATION_SYSTEM_PROMPT, VALIDATION_USER_PROMPT
from app.services.llm_client import chat_completion, strip_code_fences

logger = logging.getLogger(__name__)


async def validate_candidate_url(
    candidate: dict,
    foundation_name: str,
    orgnr: str,
    custom_system_prompt: str = None,
    custom_user_prompt: str = None
) -> dict:
    """
    Validates if a candidate URL is likely the official website using an LLM.
    Returns {is_match, confidence, raw_llm_response, prompt_used}
    """
    sys_prompt = custom_system_prompt or VALIDATION_SYSTEM_PROMPT
    usr_prompt = custom_user_prompt or VALIDATION_USER_PROMPT

    prompt = sys_prompt + "\n" + usr_prompt.format(
        name=foundation_name,
        orgnr=orgnr or "Okänt",
        title=candidate.get("title", ""),
        snippet=candidate.get("snippet", ""),
        url=candidate.get("url", "")
    )

    try:
        raw_response = chat_completion(prompt, temperature=0.1)
        if raw_response:
            data = json.loads(strip_code_fences(raw_response))
            logger.debug(f"Validation for {candidate.get('url')}: is_match={data.get('is_match')} confidence={data.get('confidence')}")
            return {
                "is_match": bool(data.get("is_match", False)),
                "confidence": float(data.get("confidence", 0.0)),
                "raw_llm_response": raw_response,
                "prompt_used": prompt[:800] + "..." if len(prompt) > 800 else prompt,
            }
    except Exception as e:
        logger.error(f"Validation LLM failed for {candidate.get('url')}: {e}")
        return {
            "is_match": False,
            "confidence": 0.0,
            "raw_llm_response": None,
            "error": str(e),
            "prompt_used": prompt[:800] + "..." if len(prompt) > 800 else prompt,
        }

    return {"is_match": False, "confidence": 0.0, "raw_llm_response": None}
