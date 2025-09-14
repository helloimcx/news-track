"""
Tests for the main application flow.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from app.main import run_pipeline
from app.models import Article, ProcessedArticle, Digest
from app.config import settings

class TestMainAppFlow:

    @pytest.fixture
    def sample_articles(self):
        """Fixture to create sample Article instances."""
        return [
            Article(title=f"Article {i}", url=f"https://example.com/{i}", 
                    content=f"Content of article {i}.", source="Test RSS")
            for i in range(1, 4) # 3 articles
        ]

    @pytest.fixture
    def sample_processed_articles(self, sample_articles):
        """Fixture to create sample ProcessedArticle instances."""
        return [
            ProcessedArticle(
                original_article=article,
                summary=f"Summary of article {article.title}.",
                key_points=[f"Point A{i}", f"Point B{i}"],
                sentiment=0.1 * i,
                tags=[f"tag{i}a", f"tag{i}b"]
            )
            for i, article in enumerate(sample_articles, 1)
        ]

    @pytest.mark.asyncio
    async def test_run_pipeline_success(self, sample_articles, sample_processed_articles):
        """Test the main pipeline runs successfully with all components working."""
        
        # Mock the RSSCollector.collect method
        mock_collector = AsyncMock()
        mock_collector.collect.return_value = sample_articles

        # Mock the LLMProcessor.process method
        mock_processor = AsyncMock()
        mock_processor.process.side_effect = sample_processed_articles
        
        # Mock the EmailNotifier.send_digest method
        mock_notifier = AsyncMock()
        mock_notifier.send_digest = AsyncMock() # Ensure it's an async mock

        # Patch the constructors to return our mocks
        with patch('app.main.RSSCollector', return_value=mock_collector), \
             patch('app.main.LLMProcessor', return_value=mock_processor), \
             patch('app.main.EmailNotifier', return_value=mock_notifier):

            # Mock settings to provide necessary config for EmailNotifier and RSS
            mock_settings_dict = {
                "email": {
                    "smtp_server": "smtp.test.com",
                    "smtp_port": 587,
                    "username": "test_user",
                    "password": "test_pass",
                    "sender_email": "sender@test.com",
                    "recipient_emails": "recipient@test.com"
                }
            }
            
            # This approach directly replaces the settings instance attributes
            # which is a bit of a hack for testing, but works for this isolated test.
            # A more robust way would be to pass settings as a dependency or use a factory.
            original_email_config = settings.email
            original_search_config = settings.search
            
            # Create a temporary EmailConfig-like object for the mock
            from app.config import EmailConfig, SearchConfig
            temp_email_config = EmailConfig(**mock_settings_dict["email"])
            temp_search_config = SearchConfig(
                rss_feed_urls=["https://example.com/feed.xml"],
                topic=None,  # No topic specified, will use RSS
                num_results=5
            )
            settings.email = temp_email_config
            settings.search = temp_search_config

            try:
                result_digest = await run_pipeline()
                
                # Assertions
                # 1. Collector.collect was called
                mock_collector.collect.assert_called_once()
                
                # 2. Processor.process was called for each article
                assert mock_processor.process.call_count == len(sample_articles)
                for article in sample_articles:
                    mock_processor.process.assert_any_call(article)
                
                # 3. Notifier.send_digest was called once with a Digest
                mock_notifier.send_digest.assert_called_once()
                called_with_digest = mock_notifier.send_digest.call_args[0][0] # First positional arg
                assert isinstance(called_with_digest, Digest)
                assert len(called_with_digest.articles) == len(sample_processed_articles)
                assert called_with_digest.title.startswith("News Digest - ") or called_with_digest.title.startswith("test topic - ")
                
                # 4. The returned digest is the same one that was sent
                assert result_digest is called_with_digest
                
            finally:
                # Restore original settings
                settings.email = original_email_config
                settings.search = original_search_config


    @pytest.mark.asyncio
    async def test_run_pipeline_collector_failure(self):
        """Test pipeline handles collector failure gracefully."""
        mock_google_collector = AsyncMock()
        mock_google_collector.fetch_articles.side_effect = Exception("Google Search Error")
        
        mock_processor = AsyncMock()
        mock_notifier = AsyncMock()

        with patch('app.main.GoogleSearchCollector', return_value=mock_google_collector), \
             patch('app.main.LLMProcessor', return_value=mock_processor), \
             patch('app.main.EmailNotifier', return_value=mock_notifier):

            # Mock settings for EmailNotifier and Search
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
                topic="test topic",  # Topic specified, will use Google Search
                num_results=5
            )
            settings.email = temp_email_config
            settings.search = temp_search_config

            try:
                # Should return None when Google Search fails
                result = await run_pipeline()
                assert result is None
                    
                # Assert that processor and notifier were never called
                mock_processor.process.assert_not_called()
                mock_notifier.send_digest.assert_not_called()
                
            finally:
                settings.email = original_email_config
                settings.search = original_search_config

    @pytest.mark.asyncio
    async def test_run_pipeline_processor_failure(self, sample_articles):
        """Test pipeline handles processor failure."""
        mock_collector = AsyncMock()
        mock_collector.collect.return_value = sample_articles
        
        mock_processor = AsyncMock()
        mock_processor.process.side_effect = Exception("LLM Processing Error")
        
        mock_notifier = AsyncMock()

        with patch('app.main.RSSCollector', return_value=mock_collector), \
             patch('app.main.LLMProcessor', return_value=mock_processor), \
             patch('app.main.EmailNotifier', return_value=mock_notifier):

            # Mock settings for EmailNotifier and RSS
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
                topic="test topic",
                num_results=5
            )
            settings.email = temp_email_config
            settings.search = temp_search_config

            try:
                with pytest.raises(Exception, match="LLM Processing Error"):
                    await run_pipeline()
                    
                # Assert that notifier was never called
                mock_notifier.send_digest.assert_not_called()
                
            finally:
                settings.email = original_email_config
                settings.search = original_search_config

    # Note: Testing Notifier failure is similar and can be added if needed.
    # For now, we assume the Notifier's own tests cover its error handling.