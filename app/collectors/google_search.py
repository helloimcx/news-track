import logging
import asyncio
from typing import List
from googlesearch import search
import aiohttp
from bs4 import BeautifulSoup
from app.models import Article
from app.config import settings

logger = logging.getLogger("NewsTracker.GoogleSearch")

class GoogleSearchCollector:
    """
    A collector that uses the googlesearch-python library to search Google
    and fetch articles from the search results.
    """
    
    def __init__(self, topic: str, num_results: int = 5):
        """
        Initialize the Google Search collector.
        
        Args:
            topic: The search topic/query.
            num_results: Number of search results to fetch and process.
        """
        self.topic = topic
        self.num_results = num_results
        logger.info(f"Initialized GoogleSearchCollector for topic: '{topic}' with {num_results} results")
    
    async def fetch_articles(self) -> List[Article]:
        """
        Fetch articles by searching Google and parsing the result pages.
        
        Returns:
            A list of Article objects parsed from the search results.
        """
        logger.info(f"Starting Google search for topic: '{self.topic}'")
        articles = []
        
        try:
            # Get search results using googlesearch-python
            logger.debug(f"Searching Google for: {self.topic}")
            search_results = list(search(self.topic, num_results=self.num_results, lang="zh-cn", region="cn"))
            logger.info(f"Found {len(search_results)} search results")
            
            # Fetch and parse each result
            async with aiohttp.ClientSession() as session:
                for i, url in enumerate(search_results):
                    try:
                        logger.debug(f"Fetching content from result {i+1}/{len(search_results)}: {url}")
                        article = await self._fetch_and_parse_article(session, url)
                        if article:
                            articles.append(article)
                            logger.debug(f"Successfully parsed article: {article.title}")
                        else:
                            logger.warning(f"Failed to parse article from: {url}")
                    except Exception as e:
                        logger.error(f"Error processing search result {url}: {e}")
                        
        except Exception as e:
            logger.error(f"Error during Google search: {e}")
            
        logger.info(f"Finished Google search. Collected {len(articles)} articles.")
        return articles
    
    async def _fetch_and_parse_article(self, session: aiohttp.ClientSession, url: str) -> Article | None:
        """
        Fetch and parse an article from a given URL.
        
        Args:
            session: The aiohttp session to use for requests.
            url: The URL to fetch.
            
        Returns:
            An Article object if successful, None otherwise.
        """
        try:
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()  # This is not an async method
                content = await response.text()
                
                # Parse the HTML content
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract title
                title_elem = soup.find('title')
                title = title_elem.get_text().strip() if title_elem else "Untitled"
                
                # Extract main content
                # Try multiple selectors for content extraction
                content_selectors = [
                    'article',
                    'main',
                    '.content',
                    '.article-content',
                    '.post-content',
                    '.entry-content',
                    '#content',
                    '.main-content',
                    'div[role="main"]',
                    'body'
                ]
                
                content_text = ""
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # Remove script and style elements
                        for script in content_elem(["script", "style", "nav", "header", "footer", "aside"]):
                            script.decompose()
                        
                        content_text = content_elem.get_text(separator=' ', strip=True)
                        if len(content_text) > 200:  # Only use if we got substantial content
                            break
                
                if not content_text or len(content_text) < 100:
                    logger.warning(f"Insufficient content extracted from {url}")
                    return None
                
                # Limit content length
                if len(content_text) > 5000:
                    content_text = content_text[:5000] + "..."
                
                return Article(
                    title=title,
                    content=content_text,
                    url=url,
                    source=url,  # Use URL as source
                    published_at=None  # We don't extract date in this simple implementation
                )
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching article from {url}")
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP error fetching article from {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching article from {url}: {e}")
            
        return None