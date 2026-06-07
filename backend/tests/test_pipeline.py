import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.pipeline.discovery import discover_candidate_urls
from app.pipeline.validation import validate_candidate_url
from app.pipeline.extraction import extract_data_from_content

# Mock DDGS for Discovery
@pytest.mark.asyncio
@patch('app.pipeline.discovery.DDGS')
async def test_discovery(mock_ddgs):
    mock_instance = MagicMock()
    # Return fake search results
    mock_instance.text.return_value = [
        {"href": "https://www.test-foundation.se", "title": "Test Foundation", "body": "Welcome"}
    ]
    mock_ddgs.return_value.__enter__.return_value = mock_instance
    
    candidates = await discover_candidate_urls("Test Foundation", "123456")
    assert len(candidates) == 1
    assert candidates[0]["url"] == "https://www.test-foundation.se"


# Mock Requests for Validation (Ollama)
@pytest.mark.asyncio
@patch('app.pipeline.validation.requests.post')
async def test_validation(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '{"is_match": true, "confidence": 0.98}'
    }
    mock_post.return_value = mock_response
    
    candidate = {"url": "https://www.test.se", "title": "Test", "snippet": "..."}
    res = await validate_candidate_url(candidate, "Test", "123")
    
    assert res["is_match"] is True
    assert res["confidence"] == 0.98


# Mock Extractor (Ollama)
@pytest.mark.asyncio
@patch('app.pipeline.extraction.requests.post')
async def test_extraction(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '{"application_deadline": "31 mars 2024", "application_open": "1 januari"}'
    }
    mock_post.return_value = mock_response
    
    res = await extract_data_from_content("Deadline is 31 mars 2024", "Test Foundation")
    assert res is not None
    assert res.application_deadline == "31 mars 2024"
    assert res.application_open == "1 januari"
