"""
Web Search Collector for fetching articles using Google Custom Search and Playwright.
"""
import asyncio
import logging
from typing import List, Optional
from googleapiclient.discovery import build
from playwright.async_api import async_playwright
from app.models import Article
from app.config import settings

# Create a logger for this module
logger = logging.getLogger("NewsTracker.WebSearch")

class WebSearchCollector:
    """
    A collector that fetches articles by performing a web search and then
    extracting content from the resulting pages using a headless browser.
    """

    def __init__(self, topic: str, num_results: int = 5):
        """
        Initializes the Web Search collector.

        Args:
            topic: The search topic/query.
            num_results: The number of search results to process.
        """
        self.topic = topic
        self.num_results = num_results
        self.google_api_key = settings.websearch.google_api_key
        self.google_cse_id = settings.websearch.google_cse_id

        if not self.google_api_key or not self.google_cse_id:
            raise ValueError("Google API Key and CSE ID are required for WebSearchCollector.")

    async def fetch_articles(self) -> List[Article]:
        """
        Asynchronously fetches and parses articles based on the search topic.

        Returns:
            A list of Article objects parsed from the web pages.
        """
        logger.info(f"Starting web search for topic: '{self.topic}'")
        articles = []

        # 1. Perform Google Search
        search_results = await self._google_search(self.topic, self.num_results)
        if not search_results:
            logger.warning("Google search returned no results.")
            return articles

        # 2. Extract content from each search result page
        async with async_playwright() as p:
            # Launch browser
            # Note: Headless mode is default in newer Playwright versions
            # You might want to set headless=False for debugging
            browser = await p.chromium.launch(headless=True) 
            
            for item in search_results:
                title = item.get('title', 'No Title')
                link = item.get('link')
                snippet = item.get('snippet', '')
                
                if not link:
                    continue

                try:
                    logger.debug(f"Fetching content from: {link}")
                    content = await self._fetch_page_content(browser, link)
                    if content:
                        article = Article(
                            title=title,
                            url=link,
                            content=content, # Use extracted content
                            source="Web Search Result", # Generic source
                            # published_at is left as None as it's hard to extract reliably
                        )
                        articles.append(article)
                    else:
                        logger.warning(f"Failed to extract content from {link}")
                except Exception as e:
                    logger.error(f"Error processing search result {link}: {e}")

            # Close browser
            await browser.close()

        logger.info(f"Finished web search. Collected {len(articles)} articles.")
        return articles

    async def _google_search(self, query: str, num_results: int) -> List[dict]:
        """
        Performs a Google Custom Search.

        Args:
            query: The search query.
            num_results: Number of results to return (max 10 per request).

        Returns:
            A list of search result items.
        """
        try:
            service = build("customsearch", "v1", developerKey=self.google_api_key)
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: service.cse().list(
                    q=query,
                    cx=self.google_cse_id,
                    num=num_results
                ).execute()
            )
            return result.get('items', [])
        except Exception as e:
            logger.error(f"Google Custom Search API error: {e}")
            return []

    async def _fetch_page_content(self, browser, url: str) -> Optional[str]:
        """
        Fetches and extracts text content from a web page using Playwright.

        Args:
            browser: The Playwright browser instance.
            url: The URL of the page to fetch.

        Returns:
            The extracted text content, or None on failure.
        """
        try:
            page = await browser.new_page()
            # Set a timeout for page navigation and loading
            await page.goto(url, wait_until='networkidle', timeout=10000)
            
            # Simple content extraction: get all text from the body
            # This is a basic approach. For more sophisticated extraction,
            # you could use page.query_selector and target specific elements,
            # or use readability.js via page.add_script_tag and page.evaluate.
            content = await page.inner_text('body')
            await page.close()
            
            if content:
                # Basic cleaning: remove extra whitespace and limit length
                cleaned_content = ' '.join(content.split())[:5000] # Limit to 5000 chars
                return cleaned_content
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error fetching page content from {url}: {e}")
            return None