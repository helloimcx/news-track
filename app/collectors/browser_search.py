"""
Browser Search Collector for fetching articles by controlling a real browser
to perform searches and extract content.
"""
import logging
import urllib.parse
from typing import List
from playwright.async_api import async_playwright, Page, TimeoutError
from app.models import Article
from app.config import settings

# Create a logger for this module
logger = logging.getLogger("NewsTracker.BrowserSearch")

class BrowserSearchCollector:
    """
    A collector that uses Playwright to control a browser, perform a search on a
    specified search engine, and then extract content from the resulting pages.
    """

    def __init__(self, topic: str, num_results: int = 5):
        """
        Initializes the Browser Search collector.

        Args:
            topic: The search topic/query.
            num_results: The number of search results to process.
        """
        self.topic = topic
        self.num_results = num_results
        self.search_engine_url = settings.websearch.search_engine_url

    async def fetch_articles(self) -> List[Article]:
        """
        Asynchronously fetches and parses articles by controlling a browser.

        Returns:
            A list of Article objects parsed from the web pages.
        """
        logger.info(f"Starting browser-based search for topic: '{self.topic}' on '{self.search_engine_url}'")
        articles = []

        async with async_playwright() as p:
            # 1. Launch browser
            # Note: headless=False can be useful for debugging
            browser = await p.chromium.launch(headless=True) 
            page = await browser.new_page()
            
            try:
                # 2. Navigate to the search engine or construct search URL
                search_engine = urllib.parse.urlparse(self.search_engine_url).netloc.lower()
                
                if "google." in search_engine:
                    # For Google, construct the search URL directly
                    search_url = f"{self.search_engine_url}?q={urllib.parse.quote(self.topic)}"
                    logger.debug(f"Navigating directly to Google search: {search_url}")
                    await page.goto(search_url, wait_until='networkidle', timeout=10000)
                elif "duckduckgo.com" in search_engine:
                    # For DuckDuckGo, construct the search URL directly
                    search_url = f"{self.search_engine_url}/?q={urllib.parse.quote(self.topic)}"
                    logger.debug(f"Navigating directly to DuckDuckGo search: {search_url}")
                    await page.goto(search_url, wait_until='networkidle', timeout=10000)
                else:
                    # For other search engines, navigate to homepage first
                    logger.debug(f"Navigating to search engine: {self.search_engine_url}")
                    await page.goto(self.search_engine_url, wait_until='networkidle', timeout=10000)
                    
                    # 3. Perform the search
                    await self._perform_search(page, self.topic)

                # 4. Extract search result links
                logger.debug("Extracting search result links...")
                search_result_links = await self._extract_search_links(page, self.num_results)
                logger.info(f"Found {len(search_result_links)} search results.")

                # 5. Visit each link and extract article content
                for i, link in enumerate(search_result_links):
                    try:
                        logger.debug(f"Fetching content from result {i+1}/{len(search_result_links)}: {link}")
                        article = await self._fetch_and_parse_article(page, link)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"Error processing search result link {link}: {e}")
                        
            except Exception as e:
                logger.error(f"An error occurred during the browser search workflow: {e}")
            finally:
                # 6. Close browser
                await page.close()
                await browser.close()

        logger.info(f"Finished browser-based search. Collected {len(articles)} articles.")
        return articles

    async def _perform_search(self, page: Page, query: str):
        """
        Performs the search on the current page. This method needs to be adapted
        for different search engines by identifying their input field and submit mechanism.

        Args:
            page: The current Playwright page object.
            query: The search query string.
        """
        # --- Generic Search Logic ---
        # This is a simplified heuristic that works for many search engines.
        # It looks for an input field that might be the search box and a button that might submit the search.
        # It's not foolproof but covers common cases like Google, Bing, Baidu, DuckDuckGo.

        search_engine = urllib.parse.urlparse(self.search_engine_url).netloc.lower()

        # --- Specific logic for common search engines ---
        # We can add more specific selectors for better reliability.
        if "baidu.com" in search_engine:
            logger.debug("Detected Baidu, using specific selectors.")
            # Baidu's main search box - try multiple selectors
            search_input_selector = "input#kw, input[name='wd'], input[placeholder*='搜索'], input[type='text']:first-of-type"
            search_button_selector = "input#su, input[value='百度一下'], button[type='submit']"
        elif "google." in search_engine and "google." != search_engine:
             # Matches google.com, google.co.uk, etc. but not just 'google.'
            logger.debug("Detected Google, using specific selectors.")
            search_input_selector = "textarea[name='q']" # Newer Google uses textarea
            search_button_selector = "input[name='btnK']" # Or we can just press Enter
        elif "duckduckgo.com" in search_engine:
            logger.debug("Detected DuckDuckGo, using specific selectors.")
            # DuckDuckGo 的前端偶尔会调整，这里同时尝试多种可能的选择器以提高鲁棒性
            search_input_selector = "input#search_form_input_homepage, input[name='q'], input[type='search']"
            search_button_selector = "input#search_button_homepage, button[type='submit']"
        else:
            logger.debug("Using generic selectors for search engine.")
            # Fallback to generic selectors
            search_input_selector = "input[type='text'], input[type='search'], textarea"
            search_button_selector = "input[type='submit'], button[type='submit'], button:has-text('Search')"

        # Fill the search box
        logger.debug(f"Looking for search input with selector: {search_input_selector}")
        try:
            await page.wait_for_selector(search_input_selector, timeout=5000)
            await page.fill(search_input_selector, query)
            logger.info(f"Filled search box with query: '{query}'")
        except TimeoutError:
            logger.warning(f"Timeout waiting for search input element '{search_input_selector}'. Falling back to generic selector.")
            generic_selector = "input[type='text'], input[type='search'], textarea"
            try:
                await page.wait_for_selector(generic_selector, timeout=5000)
                await page.fill(generic_selector, query)
                search_input_selector = generic_selector  # 更新为已成功定位的选择器，后续按此提交搜索
                logger.info("Filled search box with query using generic selector.")
            except Exception as e_generic:
                logger.error(f"Failed to fill search box with generic selector: {e_generic}")
                # Try to get page content for debugging
                content = await page.content()
                logger.debug(f"Page content when search input was not found:\n{content[:1000]}...")
                raise
        except Exception as e:
            logger.error(f"Failed to fill search box: {e}")
            raise

        # Submit the search
        # Option 1: Click the search button
        try:
            logger.debug(f"Looking for search button with selector: {search_button_selector}")
            await page.wait_for_selector(search_button_selector, timeout=5000)
            await page.click(search_button_selector, timeout=5000)
            logger.info("Clicked search button.")
        except TimeoutError:
            logger.warning("Search button not found or not clickable within timeout. Trying to press Enter.")
            # Option 2: Press Enter in the search box
            try:
                await page.press(search_input_selector, 'Enter')
                logger.info("Pressed Enter in search box.")
            except Exception as e:
                logger.error(f"Failed to press Enter in search box: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to click search button: {e}")
            raise

        # Wait for results to load
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
            logger.info("Page loaded after search submission.")
        except TimeoutError:
            logger.warning("Timeout waiting for page to load after search. Proceeding anyway.")


    async def _extract_search_links(self, page: Page, num_results: int) -> List[str]:
        """
        Extracts the URLs of the top search results from the current page.

        Args:
            page: The current Playwright page object (should be on the search results page).
            num_results: The maximum number of links to extract.

        Returns:
            A list of unique URLs.
        """
        # --- DEBUG: Save page content for offline analysis ---
        # Uncomment the following lines if you need to inspect the HTML structure.
        # import os
        # debug_dir = "debug"
        # os.makedirs(debug_dir, exist_ok=True)
        # page_content = await page.content()
        # with open(os.path.join(debug_dir, "search_results_page.html"), "w", encoding="utf-8") as f:
        #     f.write(page_content)
        # logger.debug(f"Saved search results page HTML to debug/search_results_page.html")
        # --- END DEBUG ---

        # --- Generic Link Extraction Logic ---
        # This is also a heuristic. Search results are often in <a> tags with href attributes.
        # They are often within <div> or <li> elements that have some identifying class or attribute.
        # The challenge is finding a selector that works across different search engines.
        
        # A common pattern is links in search result containers.
        # Let's try a few common CSS selectors, ordered from more specific to more generic.
        # Updated selectors for current search engines
        
        search_engine = urllib.parse.urlparse(self.search_engine_url).netloc.lower()
        
        if "duckduckgo.com" in search_engine:
            # DuckDuckGo specific selectors
            link_selectors = [
                "article h3 a[href]",       # DuckDuckGo main results
                "div[data-testid='result'] h3 a",  # DuckDuckGo newer format
                "div.result h3 a",          # DuckDuckGo classic format
                "a[data-testid='result-title-a']",  # DuckDuckGo title links
                "h3 a:not([href*='duckduckgo.com'])",  # Generic h3 links excluding DDG
            ]
        else:
            # Google and other search engines
            link_selectors = [
                "div.g h3 a",               # Google main search results
                "div.g a[href]:not([href*='google.com']):not([href*='youtube.com']):not([href*='maps.google'])",  # Google result links excluding Google services
                "div[data-ved] h3 a",       # Google result with data-ved attribute
                "div.yuRUbf a",             # Google newer result container
                "h3 a:not([href*='google.com'])",  # Classic selector excluding Google links
                "div.result h3 a",          # Other engines
                "div.web-result h3 a",      # Alternative result container
            ]

        links = []
        for selector in link_selectors:
            try:
                logger.debug(f"Trying to extract links with selector: {selector}")
                # Find up to num_results elements matching the selector
                link_elements = await page.query_selector_all(selector)
                logger.debug(f"Found {len(link_elements)} elements with selector '{selector}'")
                
                if not link_elements:
                    logger.debug(f"No elements found with selector '{selector}', trying next selector")
                    continue
                    
                for i, elem in enumerate(link_elements[:num_results * 2]): # Get a few more in case of duplicates/non-relevant links
                    try:
                        outer_html = await elem.evaluate("e => e.outerHTML")
                        logger.debug(f"Element {i} HTML snippet: {outer_html[:200]}...")
                        href = await elem.get_attribute('href')
                        logger.debug(f"Element {i} href attribute: {href}")
                        if href and href.startswith('http'): # Basic validation
                            # Resolve relative URLs
                            full_url = urllib.parse.urljoin(page.url, href)
                            logger.debug(f"Resolved URL: {full_url}")
                            
                            # Additional filtering to exclude unwanted URLs
                            excluded_domains = ['google.com', 'youtube.com', 'maps.google', 'baidu.com', 'duckduckgo.com', 'bing.com']
                            excluded_paths = ['/search', '/url?', '/imgres?', '/maps', '/shopping']
                            
                            # Check if URL should be excluded
                            should_exclude = False
                            for domain in excluded_domains:
                                if domain in full_url:
                                    should_exclude = True
                                    break
                            
                            if not should_exclude:
                                for path in excluded_paths:
                                    if path in full_url:
                                        should_exclude = True
                                        break
                            
                            if not should_exclude and full_url not in links: # Avoid duplicates
                                links.append(full_url)
                                logger.debug(f"Added valid search result URL: {full_url}")
                            elif should_exclude:
                                logger.debug(f"Excluded URL: {full_url}")
                            
                            if len(links) >= num_results:
                                logger.debug(f"Reached desired number of links ({num_results}). Stopping.")
                                break
                    except Exception as e:
                        logger.warning(f"Error processing element {i} with selector '{selector}': {e}")
                if links:
                    logger.debug(f"Successfully extracted {len(links)} links with selector '{selector}'")
                    break # If we found links, stop trying other selectors
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
        
        if not links:
            logger.warning("No search result links found with any selector.")
            # Save page content for debugging
            content = await page.content()
            logger.debug(f"Page content when no links found:\n{content[:2000]}...")
            
            # Try to find any links on the page for debugging
            all_links = await page.query_selector_all("a[href]")
            logger.debug(f"Total links found on page: {len(all_links)}")
            if all_links:
                sample_links = []
                for i, link in enumerate(all_links[:5]):  # Show first 5 links
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        sample_links.append(f"{i+1}. {href} - '{text[:50]}'")
                    except Exception as e:
                        sample_links.append(f"{i+1}. Error getting link info: {e}")
                logger.debug(f"Sample links found:\n" + "\n".join(sample_links))
            return []
        
        logger.info(f"Total unique links extracted: {len(links)}")
        # Limit to the requested number of results
        final_links = links[:num_results]
        logger.debug(f"Returning top {len(final_links)} links: {final_links}")
        return final_links


    async def _fetch_and_parse_article(self, page: Page, url: str) -> Article | None:
        """
        Navigates to a URL and extracts the article title and content.

        Args:
            page: The current Playwright page object.
            url: The URL of the article to fetch.

        Returns:
            An Article object if successful, None otherwise.
        """
        try:
            logger.debug(f"Navigating to article page: {url}")
            await page.goto(url, wait_until='networkidle', timeout=15000)
            
            # --- Generic Content Extraction ---
            # This is a very basic approach. For production, consider using libraries
            # like readability.js (can be injected via Playwright) or newspaper3k.
            
            # 1. Extract Title
            # Try common title selectors
            title_selectors = [
                "h1",           # Most common
                "title",        # HTML title tag
                "h2",           # Sometimes the main heading is h2
                "h3"            # Less likely but possible
            ]
            title = "No Title Found"
            for selector in title_selectors:
                try:
                    title_element = await page.query_selector(selector)
                    if title_element:
                        title = await title_element.inner_text()
                        title = title.strip()
                        if title:
                            break
                except:
                    pass
            
            # 2. Extract Content
            # Try to find the main content area. This is highly heuristic.
            content_selectors = [
                "article",              # Semantic HTML5 tag
                "main",                 # Semantic HTML5 tag
                ".content",             # Common class name
                ".post-content",        # Common class name
                "#content",             # Common ID
                ".entry-content",       # Common class name (e.g., WordPress)
                "div[itemprop='articleBody']", # Schema.org
                "body"                  # Ultimate fallback (very noisy)
            ]
            content = ""
            for selector in content_selectors:
                try:
                    content_element = await page.query_selector(selector)
                    if content_element:
                        # inner_text() gets all text, which might be enough for our LLM processor
                        content = await content_element.inner_text()
                        content = ' '.join(content.split()) # Clean up whitespace
                        content = content[:5000] # Limit size
                        if content and len(content) > 100: # Basic sanity check
                            break
                except:
                    pass
            
            if not content:
                logger.warning(f"Could not extract meaningful content from {url}")
                return None

            logger.debug(f"Successfully extracted article: '{title[:50]}...' from {url}")
            return Article(
                title=title,
                url=url,
                content=content,
                source=f"Browser Search Result ({urllib.parse.urlparse(url).netloc})"
            )

        except Exception as e:
            logger.error(f"Error fetching or parsing article from {url}: {e}")
            return None