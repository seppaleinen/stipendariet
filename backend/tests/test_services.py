"""
Unit tests for services — embedding, scraping, translation
"""
from unittest.mock import MagicMock, patch

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
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

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
        mock_response.json.return_value = {"embeddings": []}

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

    def test_health_check_available(self):
        """Returns True when model is available"""
        from app.services.embedding_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "nomic-embed-text", "size": 1234}]
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
        mock_response.json.return_value = {"models": []}

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

class TestOllamaTranslationService:
    """Tests for OllamaTranslationService"""

    def test_translate_purpose_empty_text(self):
        """Returns original text for empty input"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        result = service.translate_purpose("")
        assert result == ""

    def test_translate_purpose_whitespace_text(self):
        """Returns original text for whitespace-only input"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        result = service.translate_purpose("   ")
        assert result == "   "

    def test_translate_purpose_success(self):
        """Returns translated text on success"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Modern Swedish translation"}

        with patch('app.services.ollama_translation_service.requests.post', return_value=mock_response):
            result = service.translate_purpose("Old legalese Swedish")
            assert result == "Modern Swedish translation"

    def test_translate_purpose_empty_response(self):
        """Returns original text when API returns empty response"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": ""}

        with patch('app.services.ollama_translation_service.requests.post', return_value=mock_response):
            result = service.translate_purpose("Original text")
            assert result == "Original text"

    def test_translate_purpose_non_200(self):
        """Returns None when API returns non-200"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with patch('app.services.ollama_translation_service.requests.post', return_value=mock_response):
            result = service.translate_purpose("Original text")
            assert result is None

    def test_translate_purpose_request_exception(self):
        """Returns None when request fails"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()

        with patch('app.services.ollama_translation_service.requests.post', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.translate_purpose("Original text")
            assert result is None

    def test_translate_purpose_custom_model(self):
        """Uses custom model when provided"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Translated"}

        with patch('app.services.ollama_translation_service.requests.post') as mock_post:
            mock_post.return_value = mock_response

            result = service.translate_purpose("Original", model="custom-model")

            # Verify custom model was used
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "custom-model"
            assert result == "Translated"

    def test_translate_purpose_custom_prompt(self):
        """Uses custom prompt when provided"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Translated"}

        with patch('app.services.ollama_translation_service.requests.post') as mock_post:
            mock_post.return_value = mock_response

            result = service.translate_purpose("Original", custom_prompt="Custom: {purpose}")

            # Verify custom prompt was used
            call_args = mock_post.call_args
            assert call_args[1]["json"]["prompt"] == "Custom: Original"
            assert result == "Translated"

    def test_get_default_model(self):
        """Returns default model"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        result = service.get_default_model()
        assert result == "phi3:14b"

    def test_get_default_prompt_template(self):
        """Returns default prompt template with placeholder"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        result = service.get_default_prompt_template()
        assert "{purpose}" in result
        assert "Du är en expert på äldre juridisk och formell svenska" in result

    def test_health_check_available(self):
        """Returns True when service is available"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('app.services.ollama_translation_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is True

    def test_health_check_unavailable(self):
        """Returns False when service is unavailable"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('app.services.ollama_translation_service.requests.get', return_value=mock_response):
            result = service.health_check()
            assert result is False

    def test_health_check_request_exception(self):
        """Returns False when request fails"""
        from app.services.ollama_translation_service import OllamaTranslationService

        service = OllamaTranslationService()

        with patch('app.services.ollama_translation_service.requests.get', side_effect=requests.exceptions.RequestException("timeout")):
            result = service.health_check()
            assert result is False
