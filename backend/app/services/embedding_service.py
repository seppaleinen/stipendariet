"""
Embedding service for generating vector embeddings via LiteLLM.
Uses nomic-embed-text-v2 model for semantic search functionality.
"""
import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Embedding dimension for nomic-embed-text-v2
EMBEDDING_DIMENSION = 768

# Default similarity threshold for matching (0-1, higher = more similar)
SIMILARITY_THRESHOLD = 0.5


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

        try:
            response = requests.post(
                f"{self.litellm_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": text
                },
                headers=self._headers(),
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                # OpenAI-compatible returns {"data": [{"embedding": [...], "index": 0}]}
                data = result.get('data', [])
                if data and len(data) > 0:
                    return data[0].get('embedding')
                else:
                    logger.warning(f"Empty embedding returned for text: {text[:100]}...")
                    return None
            else:
                logger.error(f"LiteLLM embedding API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LiteLLM embedding API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during embedding generation: {e}")
            return None

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
