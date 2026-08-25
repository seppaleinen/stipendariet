"""
Unit tests for services — embedding, scraping, translation
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

# =============================================================================
# Embedding Service Tests
# =============================================================================

class TestOllamaEmbeddingService:
    """Tests for OllamaEmbeddingService"""

    def test_generate_embedding_success(self):
        """Returns embedding vector on successful API call"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}]}

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embedding("test text")
            assert result == [0.1, 0.2, 0.3]

    def test_generate_embedding_empty_text(self):
        """Returns None for empty text"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        result = service.generate_embedding("")
        assert result is None

    def test_generate_embedding_whitespace_text(self):
        """Returns None for whitespace-only text"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        result = service.generate_embedding("   ")
        assert result is None

    def test_generate_embedding_empty_result(self):
        """Returns None when API returns empty embeddings"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embedding("test text")
            assert result is None

    def test_generate_embedding_non_200(self):
        """Returns None when API returns non-200"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embedding("test text")
            assert result is None

    def test_generate_embedding_request_exception(self):
        """Returns None when request fails"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        with patch('app.services.embedding_service.requests.post', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.generate_embedding("test text")
            assert result is None

    def test_generate_embedding_429_retry_success(self):
        """Retries on 429 and succeeds on second attempt"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": [{"embedding": [0.5, 0.6, 0.7], "index": 0}]}

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limited_error
            return success_response

        with patch('app.services.embedding_service.requests.post', side_effect=mock_post), \
             patch('app.services.embedding_service.time.sleep'):
            result = service.generate_embedding("test text")
            assert result == [0.5, 0.6, 0.7]
            assert call_count == 2

    def test_generate_embedding_429_max_retries_exceeded(self):
        """Returns None after max retries exhausted on 429"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        with patch('app.services.embedding_service.requests.post', side_effect=rate_limited_error), \
             patch('app.services.embedding_service.time.sleep'):
            result = service.generate_embedding("test text")
            assert result is None

    def test_generate_embeddings_batch_success(self):
        """Returns aligned embeddings for batch input"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2], "index": 0},
                {"embedding": [0.3, 0.4], "index": 1},
            ]
        }

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embeddings_batch(["text one", "text two"])
            assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_generate_embeddings_batch_empty_input(self):
        """Returns empty list for empty input"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        result = service.generate_embeddings_batch([])
        assert result == []

    def test_generate_embeddings_batch_with_empty_texts(self):
        """Returns None at indices for empty/whitespace texts"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.5, 0.6], "index": 0},
            ]
        }

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embeddings_batch(["valid text", "", "  ", "another valid"])
            assert result[0] == [0.5, 0.6]
            assert result[1] is None
            assert result[2] is None
            assert result[3] is None  # Only one valid text sent, so only one embedding returned

    def test_generate_embeddings_batch_all_empty(self):
        """Returns all None when all texts are empty"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        result = service.generate_embeddings_batch(["", "  ", ""])
        assert result == [None, None, None]

    def test_generate_embeddings_batch_api_failure(self):
        """Returns all None when API call fails"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with patch('app.services.embedding_service.requests.post', return_value=mock_response):
            result = service.generate_embeddings_batch(["text one", "text two"])
            assert result == [None, None]

    def test_generate_embeddings_batch_429_retry_success(self):
        """Retries batch on 429 and succeeds"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "data": [
                {"embedding": [0.7, 0.8], "index": 0},
                {"embedding": [0.9, 1.0], "index": 1},
            ]
        }

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limited_error
            return success_response

        with patch('app.services.embedding_service.requests.post', side_effect=mock_post), \
             patch('app.services.embedding_service.time.sleep'):
            result = service.generate_embeddings_batch(["text a", "text b"])
            assert result == [[0.7, 0.8], [0.9, 1.0]]
            assert call_count == 2

    def test_health_check_available(self):
        """Returns True when model is available"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "nomic-embed-text-v2", "object": "model"}]
        }

        with patch('app.services.embedding_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is True

    def test_health_check_not_available(self):
        """Returns False when model is not available"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch('app.services.embedding_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is False

    def test_health_check_request_exception(self):
        """Returns False when request fails"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        with patch('app.services.embedding_service.requests.get', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.health_check()
            assert result is False


# =============================================================================
# Retry Logic Tests
# =============================================================================

class TestRetryWithBackoff:
    """Tests for the retry_with_backoff helper"""

    def test_retry_llm_client_429_then_success(self):
        """LLM client retries on 429 then succeeds"""
        from app.services.llm_client import retry_with_backoff

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limited_error
            return "success"

        with patch('app.services.llm_client.time.sleep'):
            result = retry_with_backoff(func)
            assert result == "success"
            assert call_count == 2

    def test_retry_llm_client_429_max_retries(self):
        """LLM client gives up after max retries on 429"""
        from app.services.llm_client import retry_with_backoff

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        with patch('app.services.llm_client.time.sleep'), \
             pytest.raises(requests.exceptions.HTTPError) as exc_info:
            retry_with_backoff(lambda: (_ for _ in ()).throw(rate_limited_error), max_retries=2)
        assert exc_info.value.response.status_code == 429

    def test_retry_llm_client_429_with_retry_after_header(self):
        """Uses Retry-After header for delay"""
        from app.services.llm_client import retry_with_backoff

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "5"}
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limited_error
            return "ok"

        with patch('app.services.llm_client.time.sleep') as mock_sleep:
            result = retry_with_backoff(func)
            assert result == "ok"
            mock_sleep.assert_called_once_with(5.0)

    def test_retry_on_connection_error(self):
        """Retries on ConnectionError"""
        from app.services.llm_client import retry_with_backoff

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.ConnectionError("refused")
            return "connected"

        with patch('app.services.llm_client.time.sleep'):
            result = retry_with_backoff(func)
            assert result == "connected"

    def test_retry_on_timeout(self):
        """Retries on Timeout"""
        from app.services.llm_client import retry_with_backoff

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.Timeout("timed out")
            return "timely"

        with patch('app.services.llm_client.time.sleep'):
            result = retry_with_backoff(func)
            assert result == "timely"

    def test_no_retry_on_non_retryable_error(self):
        """Does not retry on non-retryable HTTP errors"""
        from app.services.llm_client import retry_with_backoff

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 500
        rate_limited_error = requests.exceptions.HTTPError(response=rate_limited_response)

        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            retry_with_backoff(lambda: (_ for _ in ()).throw(rate_limited_error))
        assert exc_info.value.response.status_code == 500


# =============================================================================
# Scraper Service Tests
# =============================================================================

class TestScraperService:
    """Tests for smart_scrape and helper functions"""

    def test_is_valid_content_empty(self):
        """Returns False for empty content"""
        from app.services.scraper_service import _is_valid_content
        assert _is_valid_content(None) is False
        assert _is_valid_content("") is False

    def test_is_valid_content_too_short(self):
        """Returns False for content shorter than MIN_CONTENT_LENGTH (500)"""
        from app.services.scraper_service import _is_valid_content
        short_content = "x" * 499
        assert _is_valid_content(short_content) is False

    def test_is_valid_content_valid(self):
        """Returns True for valid content"""
        from app.services.scraper_service import _is_valid_content
        valid_content = "x" * 500
        assert _is_valid_content(valid_content) is True

    def test_is_valid_content_js_indicator(self):
        """Returns False when JS indicator found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "enable javascript"
        assert _is_valid_content(content) is False

    def test_is_valid_content_swedish_js_indicator(self):
        """Returns False when Swedish JS indicator found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "aktivera javascript"
        assert _is_valid_content(content) is False

    def test_is_valid_content_loading_indicator(self):
        """Returns False when loading indicator found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "loading..."
        assert _is_valid_content(content) is False

    def test_is_valid_content_swedish_loading(self):
        """Returns False when Swedish loading indicator found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "laddar..."
        assert _is_valid_content(content) is False

    def test_is_valid_content_please_wait(self):
        """Returns False when 'please wait' found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "please wait"
        assert _is_valid_content(content) is False

    def test_is_valid_content_vanta(self):
        """Returns False when 'vänta' found"""
        from app.services.scraper_service import _is_valid_content
        content = "x" * 500 + "vänta"
        assert _is_valid_content(content) is False


# =============================================================================
# Translation Service Tests

# =============================================================================

def _openai_response(content):
    """Build an OpenAI-compatible chat completion response mock."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock_response


class TestLLMTranslationService:
    """Tests for LLMTranslationService (LiteLLM backend)"""

    def test_translate_purpose_empty_text(self):
        """Returns original text for empty input"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        result = service.translate_purpose("")
        assert result == ""

    def test_translate_purpose_whitespace_text(self):
        """Returns original text for whitespace-only input"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        result = service.translate_purpose("   ")
        assert result == "   "

    def test_translate_purpose_success(self):
        """Returns translated text on success"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_client.requests.post', return_value=_openai_response("Modern Swedish translation")):
            result = service.translate_purpose("Old legalese Swedish")
            assert result == "Modern Swedish translation"

    def test_translate_purpose_empty_response(self):
        """Returns original text when API returns empty response"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_client.requests.post', return_value=_openai_response("")):
            result = service.translate_purpose("Original text")
            assert result == "Original text"

    def test_translate_purpose_non_200(self):
        """Returns None when API returns non-200"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)

        with patch('app.services.llm_client.requests.post', return_value=mock_response):
            result = service.translate_purpose("Original text")
            assert result is None

    def test_translate_purpose_request_exception(self):
        """Returns None when request fails"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_client.requests.post', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.translate_purpose("Original text")
            assert result is None

    def test_translate_purpose_custom_model(self):
        """Uses custom model when provided"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_client.requests.post') as mock_post:
            mock_post.return_value = _openai_response("Translated")

            result = service.translate_purpose("Original", model="custom-model")

            # Verify custom model was used
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "custom-model"
            assert result == "Translated"

    def test_translate_purpose_custom_prompt(self):
        """Uses custom prompt when provided"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_client.requests.post') as mock_post:
            mock_post.return_value = _openai_response("Translated")

            result = service.translate_purpose("Original", custom_prompt="Custom: {purpose}")

            # Verify custom prompt was used as user message content
            call_args = mock_post.call_args
            assert call_args[1]["json"]["messages"][0]["content"] == "Custom: Original"
            assert call_args[1]["json"]["stream"] is False
            assert result == "Translated"

    def test_get_default_model(self):
        """Returns default model from settings"""
        from app.core.config import settings
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        result = service.get_default_model()
        expected = getattr(settings, 'LITELLM_TEXT_MODEL', 'gemma-4-12b')
        assert result == expected

    def test_get_default_prompt_template(self):
        """Returns default prompt template with placeholder"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        result = service.get_default_prompt_template()
        assert "{purpose}" in result
        assert "Du är en expert på äldre juridisk och formell svenska" in result

    def test_health_check_available(self):
        """Returns True when the configured model is served"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": f"ollama/{service.model}"}]}

        with patch('app.services.llm_translation_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is True

    def test_health_check_unavailable(self):
        """Returns False when service is unavailable"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('app.services.llm_translation_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is False

    def test_health_check_request_exception(self):
        """Returns False when request fails"""
        from app.services.llm_translation_service import LLMTranslationService

        service = LLMTranslationService()

        with patch('app.services.llm_translation_service.requests.get', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.health_check()
            assert result is False
