"""
Simple integration test for the main application flow.
This test uses real components but mocks external dependencies like HTTP requests.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
import asyncio

# Import the real components
from app.main import run_pipeline
from app.collectors.rss import RSSCollector
from app.processors.llm import LLMProcessor
from app.notifiers.email import EmailNotifier
from app.models import Article, ProcessedArticle
from app.config import settings

class TestMainAppIntegration:

    @pytest.mark.asyncio
    async def test_run_pipeline_integration_basic_flow(self):
        """
        Integration test for the main pipeline with real components and mocked external calls.
        This test verifies that the components are wired together correctly.
        """
        # --- Setup Mock Data ---
        mock_rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
            <title>Test RSS Feed</title>
            <item>
                <title>Integration Test Article</title>
                <link>https://example.com/integration-test</link>
                <description>This is a test article for integration.</description>
            </item>
        </channel>
        </rss>
        """
        
        mock_llm_response_text = """
        {
            "summary": "This is a summary from the mock LLM.",
            "key_points": ["Point 1", "Point 2"],
            "sentiment": 0.7,
            "tags": ["integration", "test"]
        }
        """

        # --- Mock External Dependencies ---
        # Mock aiohttp.ClientSession.get for RSSCollector
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock response for RSS feed
            mock_response = AsyncMock()
            mock_response.text.return_value = mock_rss_content
            mock_response.raise_for_status = Mock()  # Use Mock instead of AsyncMock
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Mock the LLM API call for LLMProcessor
            with patch('app.processors.llm.aiohttp.ClientSession.post') as mock_post:
                # Mock response for LLM API
                mock_llm_response = AsyncMock()
                mock_llm_response.text.return_value = mock_llm_response_text
                mock_llm_response.raise_for_status = Mock()  # Use Mock instead of AsyncMock
                mock_post.return_value.__aenter__.return_value = mock_llm_response
                
                # Mock aiosmtplib.send for EmailNotifier
                with patch('app.notifiers.email.aiosmtplib.send') as mock_send:
                    mock_send.return_value = (None, None) # Successful send
                    
                    # --- Mock settings for EmailNotifier and Search ---
                    # We need to ensure settings.email is not None for the EmailNotifier to initialize
                    original_email_config = settings.email
                    original_search_config = settings.search
                    
                    from app.config import EmailConfig, SearchConfig
                    temp_email_config = EmailConfig(
                        smtp_server="smtp.test.com", smtp_port=587,
                        username="test_user", password="test_pass",
                        sender_email="sender@test.com", recipient_emails="recipient@test.com"
                    )
                    temp_search_config = SearchConfig(
                        rss_feed_urls=["https://example.com/feed.xml"],
                        topic=None,  # No topic, will use RSS
                        num_results=5
                    )
                    settings.email = temp_email_config
                    settings.search = temp_search_config

                    try:
                        # --- Run the Pipeline ---
                        result_digest = await run_pipeline()
                        
                        # --- Assertions ---
                        # 1. Check that external calls were made
                        mock_get.assert_called_once() # RSS fetch
                        mock_post.assert_called_once() # LLM call
                        mock_send.assert_called_once() # Email send
                        
                        # 2. Check the result
                        assert result_digest is not None
                        assert len(result_digest.articles) == 1
                        processed_article = result_digest.articles[0]
                        assert processed_article.summary == "This is a summary from the mock LLM."
                        assert processed_article.key_points == ["Point 1", "Point 2"]
                        
                    finally:
                        # Restore original settings
                        settings.email = original_email_config
                        settings.search = original_search_config