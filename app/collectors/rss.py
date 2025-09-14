"""
RSS Collector for fetching articles from RSS feeds.
"""
import aiohttp
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import List
from app.models import Article

class RSSCollector:
    """
    A collector that fetches articles from one or more RSS feeds.
    """

    def __init__(self, feed_urls: List[str] | None = None, feed_url: str | None = None):
        """
        Initializes the RSS collector.

        Args:
            feed_urls: A list of RSS feed URLs to fetch. Takes precedence over feed_url.
            feed_url: A single RSS feed URL to fetch (for backward compatibility).
        """
        if feed_urls is not None:
            if not feed_urls or not all(isinstance(url, str) and url for url in feed_urls):
                 raise ValueError("'feed_urls' must be a non-empty list of non-empty strings.")
            self.feed_urls = feed_urls
        elif feed_url:
            self.feed_urls = [feed_url]
        else:
            # This should ideally be handled by config validation
            raise ValueError("Either 'feed_urls' (list) or 'feed_url' (string) must be provided.")

    async def fetch_articles(self) -> List[Article]:
        """
        Asynchronously fetches and parses articles from all configured RSS feeds.

        Returns:
            A list of Article objects parsed from the RSS feeds.
            Returns an empty list if fetching or parsing fails for all feeds.
        """
        all_articles = []
        for url in self.feed_urls:
            articles_from_feed = await self._fetch_from_single_feed(url)
            all_articles.extend(articles_from_feed)
        return all_articles

    async def collect(self) -> List[Article]:
        """
        Alias for fetch_articles to match test expectations.
        """
        return await self.fetch_articles()

    async def _fetch_from_single_feed(self, feed_url: str) -> List[Article]:
        """
        Fetches and parses articles from a single RSS feed URL.

        Args:
            feed_url: The URL of the single RSS feed.

        Returns:
            A list of Article objects from this feed, or an empty list on failure.
        """
        rss_content = ""
        try:
            # Set a common User-Agent to avoid being blocked by some servers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(feed_url) as response:
                    response.raise_for_status() # This will raise aiohttp.ClientError for bad status
                    rss_content = await response.text()
        except aiohttp.ClientError as e:
            # Handle HTTP/client errors
            print(f"HTTP error fetching RSS feed {feed_url}: {e}")
            return [] # Return empty list on HTTP error
        except Exception as e:
            # Handle other unexpected errors during fetch
            print(f"Unexpected error fetching RSS feed {feed_url}: {e}")
            return []
            
        # If we got here, fetching was successful, now parse
        return self._parse_rss(rss_content)

    def _parse_rss(self, rss_content: str) -> List[Article]:
        """
        Parses RSS XML content into a list of Article objects.

        Args:
            rss_content: The raw XML string of the RSS feed.

        Returns:
            A list of Article objects.
        """
        articles = []
        try:
            root = ET.fromstring(rss_content)
            
            # Find all <item> elements
            for item in root.findall('.//item'): # .//item finds items anywhere in the tree
                title_elem = item.find('title')
                link_elem = item.find('link')
                description_elem = item.find('description')
                pub_date_elem = item.find('pubDate')
                source_elem = item.find('source')
                
                # Basic validation: title and link are usually required
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text or ""
                    link = link_elem.text or ""
                    description = description_elem.text or "" if description_elem is not None else ""
                    
                    # Parse publication date if available
                    published_at = None
                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            published_at = parsedate_to_datetime(pub_date_elem.text)
                        except (ValueError, TypeError):
                            # If date parsing fails, leave it as None
                            pass
                    
                    # Get source name, fallback to feed title if item source is missing
                    source_name = ""
                    if source_elem is not None and source_elem.text:
                        source_name = source_elem.text
                    elif root.find('.//channel/title') is not None:
                        channel_title_elem = root.find('.//channel/title')
                        source_name = channel_title_elem.text or "" if channel_title_elem is not None else ""
                    
                    article = Article(
                        title=title,
                        url=link,
                        content=description,
                        source=source_name,
                        published_at=published_at
                    )
                    articles.append(article)
                    
        except ET.ParseError as e:
            # In a production environment, you would log the error
            print(f"Error parsing RSS XML: {e}")
            # For simplicity in this TDD example, we return an empty list
            # A more robust approach might be to raise a custom exception
        
        return articles