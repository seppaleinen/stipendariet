import json
import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

from app.pipeline.prompts import VALIDATION_SYSTEM_PROMPT, VALIDATION_USER_PROMPT


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

    ollama_url = getattr(settings, 'OLLAMA_URL', 'https://ollama.labb.site')
    model = getattr(settings, 'ENRICHMENT_LLM_MODEL', 'phi3:14b')

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        if response.status_code == 200:
            result = response.json()
            raw_response = result.get("response", "{}")
            data = json.loads(raw_response)
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
