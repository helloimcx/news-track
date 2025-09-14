import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from app.collectors.rss import RSSCollector
from app.models import Article

# Sample RSS feed XML content for mocking
SAMPLE_RSS_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test News Feed</title>
<link>https://test-news.com</link>
<description>A feed for testing.</description>
<item>
    <title>Test Article 1</title>
    <link>https://test-news.com/article1</link>
    <description>This is the first test article.</description>
    <pubDate>Fri, 27 Oct 2023 10:00:00 GMT</pubDate>
    <source url="https://test-news.com">Test News</source>
</item>
<item>
    <title>Test Article 2</title>
    <link>https://test-news.com/article2</link>
    <description>This is the second test article.</description>
    <pubDate>Sat, 28 Oct 2023 11:00:00 GMT</pubDate>
    <source url="https://test-news.com">Test News</source>
</item>
</channel>
</rss>
"""

class TestRSSCollector:
    
    @pytest.fixture
    def collector_single_url(self):
        """Fixture to create an RSSCollector instance with a single URL."""
        return RSSCollector(feed_url="https://test-news.com/rss")

    @pytest.fixture
    def collector_multiple_urls(self):
        """Fixture to create an RSSCollector instance with multiple URLs."""
        return RSSCollector(feed_urls=["https://test-news.com/rss1", "https://test-news.com/rss2"])

    @pytest.mark.asyncio
    async def test_fetch_articles_success_single_url(self, collector_single_url):
        """Test successful fetching and parsing of articles with a single URL."""
        
        # Create a mock response object
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=SAMPLE_RSS_CONTENT)
        mock_response.raise_for_status = MagicMock()

        # Create a mock for the context manager returned by session.get()
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock()

        # Create a mock session
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # Patch aiohttp.ClientSession constructor
        with patch('app.collectors.rss.aiohttp.ClientSession', return_value=mock_session):
            articles = await collector_single_url.fetch_articles()
            
            # Assertions
            assert len(articles) == 2
            assert isinstance(articles[0], Article)
            assert articles[0].title == "Test Article 1"
            # ... (other assertions remain the same)

    @pytest.mark.asyncio
    async def test_fetch_articles_success_multiple_urls(self, collector_multiple_urls):
        """Test successful fetching and parsing of articles with multiple URLs."""
        # We expect two calls to _fetch_from_single_feed, each returning the sample articles
        sample_articles = [
            Article(title="Article A", url="http://a.com", content="Content A", source="Source A"),
            Article(title="Article B", url="http://b.com", content="Content B", source="Source B")
        ]
        
        collector_multiple_urls._fetch_from_single_feed = AsyncMock(side_effect=[sample_articles, sample_articles])
        
        articles = await collector_multiple_urls.fetch_articles()
        
        assert len(articles) == 4 # 2 articles * 2 feeds
        assert collector_multiple_urls._fetch_from_single_feed.call_count == 2
        # Assert calls were made with correct URLs
        collector_multiple_urls._fetch_from_single_feed.assert_any_call("https://test-news.com/rss1")
        collector_multiple_urls._fetch_from_single_feed.assert_any_call("https://test-news.com/rss2")


    @pytest.mark.asyncio
    async def test_fetch_articles_http_error(self, collector_single_url):
        """Test handling of HTTP errors during fetch."""
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
        mock_get_context.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('app.collectors.rss.aiohttp.ClientSession', return_value=mock_session):
            articles = await collector_single_url.fetch_articles()
            assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_articles_invalid_xml(self, collector_single_url):
        """Test handling of invalid XML response."""
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="<invalid>xml</invalid>")
        mock_response.raise_for_status = MagicMock()

        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('app.collectors.rss.aiohttp.ClientSession', return_value=mock_session):
            articles = await collector_single_url.fetch_articles()
            assert articles == [] # Our implementation returns an empty list on ParseError

    def test_init_no_urls_provided(self):
        """Test initializing RSSCollector without any URLs."""
        with pytest.raises(ValueError, match="Either 'feed_urls' .* or 'feed_url' .* must be provided."):
            RSSCollector()

    def test_init_empty_feed_urls_list(self):
        """Test initializing RSSCollector with an empty feed_urls list."""
        with pytest.raises(ValueError, match="'feed_urls' must be a non-empty list.*"):
            RSSCollector(feed_urls=[])

    def test_init_feed_urls_with_non_string(self):
        """Test initializing RSSCollector with a list containing non-string."""
        with pytest.raises(ValueError, match="'feed_urls' must be a non-empty list.*"):
            RSSCollector(feed_urls=["http://valid.com", None])

