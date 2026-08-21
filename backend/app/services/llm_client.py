"""
Shared OpenAI-compatible chat-completion client for LiteLLM.

All LLM calls go through the LiteLLM proxy:
  POST {LITELLM_URL}/chat/completions
  Authorization: Bearer {LITELLM_API_KEY}   (only if key is set)
  Body: {"model": ..., "messages": [...], "stream": false}
Response content is read from choices[0].message.content.
"""
import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_LITELLM_URL = "http://litellm.litellm.svc.cluster.local:4000"
DEFAULT_LITELLM_TEXT_MODEL = "gemma-4-12b"


def litellm_url() -> str:
    return getattr(settings, 'LITELLM_URL', DEFAULT_LITELLM_URL)


def litellm_text_model() -> str:
    return getattr(settings, 'LITELLM_TEXT_MODEL', DEFAULT_LITELLM_TEXT_MODEL)


def litellm_headers() -> dict:
    """Build request headers, including auth only if an API key is configured."""
    headers = {"Content-Type": "application/json"}
    api_key = getattr(settings, 'LITELLM_API_KEY', '')
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def chat_completion(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float | None = None,
    timeout: int = 120,
) -> str | None:
    """
    Call LiteLLM chat completions and return the message content.

    Returns choices[0].message.content stripped, or None on any failure.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model or litellm_text_model(),
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        response = requests.post(
            f"{litellm_url()}/chat/completions",
            json=payload,
            headers=litellm_headers(),
            timeout=timeout,
        )
        if response.status_code != 200:
            logger.error(f"LiteLLM chat error {response.status_code}: {response.text[:300]}")
            return None
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            logger.error("LiteLLM chat returned no choices")
            return None
        content = (choices[0].get('message') or {}).get('content', '')
        return content.strip()
    except Exception as e:
        logger.error(f"LiteLLM chat call failed: {e}")
        return None


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences that models sometimes wrap JSON in."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    return cleaned.strip()
