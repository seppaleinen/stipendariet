"""
Embedding service for generating vector embeddings via LiteLLM.
Uses nomic-embed-text-v2 model for semantic search functionality.
"""
import logging
import time

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Embedding dimension for nomic-embed-text-v2
EMBEDDING_DIMENSION = 768

# Default similarity threshold for matching (0-1, higher = more similar)
SIMILARITY_THRESHOLD = 0.5


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


class OllamaEmbeddingService:
    """
    Service to generate embeddings using LiteLLM's OpenAI-compatible embedding API.
    Uses nomic-embed-text-v2 model by default.
    """

    def __init__(self):
        self.litellm_url = getattr(settings, 'LITELLM_URL', 'http://litellm.litellm.svc.cluster.local:4000')
        self.model = getattr(settings, 'LITELLM_EMBEDDING_MODEL', 'nomic-embed-text-v2')
        self.api_key = getattr(settings, 'LITELLM_API_KEY', '')
        self.timeout = 30  # seconds
        self.batch_size = getattr(settings, 'EMBEDDING_BATCH_SIZE', 100)

    def _headers(self) -> dict:
        """Build request headers, including auth if api_key is set."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector, or None if failed
        """
        if not text or not text.strip():
            return None

        def _do_request():
            response = requests.post(
                f"{self.litellm_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": text
                },
                headers=self._headers(),
                timeout=self.timeout
            )
            if response.status_code == 429:
                error = requests.exceptions.HTTPError(response=response)
                raise error
            response.raise_for_status()
            return response

        try:
            response = retry_with_backoff(_do_request)
            result = response.json()
            # OpenAI-compatible returns {"data": [{"embedding": [...], "index": 0}]}
            data = result.get('data', [])
            if data and len(data) > 0:
                return data[0].get('embedding')
            else:
                logger.warning(f"Empty embedding returned for text: {text[:100]}...")
                return None

        except Exception as e:
            logger.error(f"Error calling LiteLLM embedding API: {e}")
            return None

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float] | None]:
        """
        Generate embedding vectors for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors aligned with input indices.
            None at index i if that text failed or was empty/whitespace.
        """
        if not texts:
            return []

        # Track which indices have valid text
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [None] * len(texts)

        def _do_request():
            response = requests.post(
                f"{self.litellm_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": valid_texts
                },
                headers=self._headers(),
                timeout=self.timeout
            )
            if response.status_code == 429:
                error = requests.exceptions.HTTPError(response=response)
                raise error
            response.raise_for_status()
            return response

        try:
            response = retry_with_backoff(_do_request)
            result = response.json()

            # Initialize result list with None for all inputs
            embeddings: list[list[float] | None] = [None] * len(texts)

            # Parse response — data items have "embedding" and "index" fields
            data = result.get('data', [])
            for item in data:
                idx = item.get('index')
                embedding = item.get('embedding')
                if idx is not None and embedding is not None and idx < len(valid_indices):
                    # Map back to original index
                    embeddings[valid_indices[idx]] = embedding

            return embeddings

        except Exception as e:
            logger.error(f"Error calling LiteLLM batch embedding API: {e}")
            return [None] * len(texts)

    def health_check(self) -> bool:
        """
        Check if the LiteLLM service is accessible and the embedding model is available.

        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            response = requests.get(
                f"{self.litellm_url}/v1/models",
                headers=self._headers(),
                timeout=10
            )
            if response.status_code == 200:
                models_data = response.json().get('data', [])
                model_ids = [m.get('id', '') for m in models_data]
                return any(self.model in mid for mid in model_ids)
            return False
        except Exception:
            return False


# Create a global instance
ollama_embedding_service = OllamaEmbeddingService()
