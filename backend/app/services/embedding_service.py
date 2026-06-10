"""
Embedding service for generating vector embeddings using Ollama.
Uses nomic-embed-text model for semantic search functionality.
"""
import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Embedding dimension for nomic-embed-text
EMBEDDING_DIMENSION = 768

# Default similarity threshold for matching (0-1, higher = more similar)
SIMILARITY_THRESHOLD = 0.5


class OllamaEmbeddingService:
    """
    Service to generate embeddings using Ollama's embedding API.
    Uses nomic-embed-text model by default.
    """

    def __init__(self):
        self.ollama_url = getattr(settings, 'OLLAMA_URL', 'https://ollama.labb.site')
        self.model = getattr(settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
        self.timeout = 30  # seconds

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
                f"{self.ollama_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                # Ollama returns embeddings in the 'embeddings' field (list of embeddings)
                embeddings = result.get('embeddings', [])
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]  # Return the first embedding
                else:
                    logger.warning(f"Empty embedding returned for text: {text[:100]}...")
                    return None
            else:
                logger.error(f"Ollama embedding API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama embedding API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during embedding generation: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if the Ollama service is accessible and nomic-embed-text is available.

        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                return any('nomic-embed-text' in name for name in model_names)
            return False
        except Exception:
            return False


# Create a global instance
ollama_embedding_service = OllamaEmbeddingService()
