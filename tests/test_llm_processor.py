import pytest
from unittest.mock import AsyncMock, patch
import aiohttp
from app.processors.llm import LLMProcessor
from app.models import Article, ProcessedArticle

# Mock response from the LLM API - ensure it's a valid JSON string
MOCK_LLM_RESPONSE_JSON = '{"summary": "This is a summary of the article.", "key_points": ["Point 1", "Point 2"], "sentiment": 0.7, "tags": ["tech", "AI"]}'

class TestLLMProcessor:

    @pytest.fixture
    def processor(self):
        """Fixture to create an LLMProcessor instance."""
        return LLMProcessor(api_key="test-api-key", model="test-model")

    @pytest.fixture
    def sample_article(self):
        """Fixture to create a sample Article instance."""
        return Article(
            title="Sample Article",
            url="https://example.com/sample",
            content="This is the content of the sample article. It has multiple sentences.",
            source="Sample Source"
        )

    @pytest.mark.asyncio
    async def test_process_article_success(self, processor, sample_article):
        """Test successful processing of an article."""
        # Mock the internal _call_llm_api method to return our mock response
        with patch.object(processor, '_call_llm_api', new=AsyncMock(return_value=MOCK_LLM_RESPONSE_JSON)):
            processed_article = await processor.process_article(sample_article)

            # Assertions
            assert isinstance(processed_article, ProcessedArticle)
            assert processed_article.original_article.id == sample_article.id
            assert processed_article.summary == "This is a summary of the article."
            assert processed_article.key_points == ["Point 1", "Point 2"]
            assert processed_article.sentiment == 0.7
            assert processed_article.tags == ["tech", "AI"]


    @pytest.mark.asyncio
    async def test_process_article_http_error(self, processor, sample_article):
        """Test handling of HTTP errors from the LLM API."""
        # Mock _call_llm_api to raise an aiohttp.ClientError
        with patch.object(processor, '_call_llm_api', new=AsyncMock(side_effect=aiohttp.ClientError("API Unavailable"))):
            with pytest.raises(aiohttp.ClientError):
                await processor.process_article(sample_article)


    @pytest.mark.asyncio
    async def test_process_article_invalid_json_response(self, processor, sample_article):
        """Test handling of invalid JSON response from the LLM API."""
        # Mock _call_llm_api to return invalid JSON
        invalid_json = '{"summary": "Missing quotes}'
        with patch.object(processor, '_call_llm_api', new=AsyncMock(return_value=invalid_json)):
            with pytest.raises(ValueError):
                await processor.process_article(sample_article)
