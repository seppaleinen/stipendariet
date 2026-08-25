"""
Shared OpenAI-compatible chat-completion client for LiteLLM.

All LLM calls go through the LiteLLM proxy:
  POST {LITELLM_URL}/chat/completions
  Authorization: Bearer {LITELLM_API_KEY}   (only if key is set)
  Body: {"model": ..., "messages": [...], "stream": false}
Response content is read from choices[0].message.content.
"""
import logging
import time

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_LITELLM_URL = "http://litellm.litellm.svc.cluster.local:4000"
DEFAULT_LITELLM_TEXT_MODEL = "gemma-4-12b"


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    Retry a callable with exponential backoff on transient errors.

    Retries on:
    - HTTP 429 (rate limited): uses Retry-After header, falls back to exponential
    - ConnectionError: network connectivity issues
    - Timeout: request timed out

    Args:
        func: Callable to retry (no arguments)
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 1.0)

    Returns:
        The return value of func on success

    Raises:
        The last exception if all retries are exhausted
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            last_exception = e
            if e.response is not None and e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except (ValueError, TypeError):
                        delay = base_delay * (2 ** attempt)
                else:
                    delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Rate limited (429), retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(delay)
            else:
                raise
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exception = e
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"Request failed ({type(e).__name__}), retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
            time.sleep(delay)

    logger.error(f"All {max_retries + 1} attempts failed, giving up")
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("All retries exhausted with no captured exception")


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

    def _do_request():
        response = requests.post(
            f"{litellm_url()}/chat/completions",
            json=payload,
            headers=litellm_headers(),
            timeout=timeout,
        )
        # Raise for 429 so retry_with_backoff can handle it
        if response.status_code == 429:
            error = requests.exceptions.HTTPError(response=response)
            raise error
        response.raise_for_status()
        return response

    try:
        response = retry_with_backoff(_do_request)
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
