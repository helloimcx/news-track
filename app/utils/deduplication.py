"""
Article deduplication service for detecting and filtering duplicate articles.
"""
import hashlib
import logging
from typing import List, Set, Dict, Tuple
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.models import Article

logger = logging.getLogger("NewsTracker.Deduplication")


class ArticleDeduplicator:
    """
    Service for detecting and filtering duplicate articles by comparing with database records.
    """
    
    def __init__(self, url_similarity_threshold: float = 0.95, content_similarity_threshold: float = 0.85):
        """
        Initialize the deduplicator.
        
        Args:
            url_similarity_threshold: Threshold for URL similarity (0.0-1.0)
            content_similarity_threshold: Threshold for content similarity (0.0-1.0)
        """
        self.url_similarity_threshold = url_similarity_threshold
        self.content_similarity_threshold = content_similarity_threshold
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing query parameters that don't affect content.
        
        Args:
            url: Original URL
            
        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url.lower().strip())
            
            # Remove common tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'ref', 'source', 'from', '_t', 'share'
            }
            
            query_params = parse_qs(parsed.query)
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in tracking_params
            }
            
            # Rebuild query string
            new_query = urlencode(filtered_params, doseq=True)
            
            # Reconstruct URL
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))
            
            return normalized
        except Exception as e:
            logger.warning(f"Failed to normalize URL '{url}': {e}")
            return url.lower().strip()
    
    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate a hash of the article content for exact duplicate detection.
        
        Args:
            content: Article content
            
        Returns:
            SHA-256 hash of normalized content
        """
        # Normalize content: remove extra whitespace, convert to lowercase
        normalized_content = ' '.join(content.lower().strip().split())
        return hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
    
    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content strings.
        
        Args:
            content1: First content string
            content2: Second content string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not content1 or not content2:
            return 0.0
        
        # Normalize content for comparison
        norm1 = ' '.join(content1.lower().strip().split())
        norm2 = ' '.join(content2.lower().strip().split())
        
        # Use SequenceMatcher for similarity calculation
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def calculate_url_similarity(self, url1: str, url2: str) -> float:
        """
        Calculate similarity between two URLs.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not url1 or not url2:
            return 0.0
        
        norm_url1 = self.normalize_url(url1)
        norm_url2 = self.normalize_url(url2)
        
        if norm_url1 == norm_url2:
            return 1.0
        
        return SequenceMatcher(None, norm_url1, norm_url2).ratio()
    
    def is_duplicate_by_url(self, article: Article) -> Tuple[bool, str]:
        """
        Check if article is duplicate based on URL by querying the database.
        
        Args:
            article: Article to check
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        try:
            from app.db.services import ArticleService
            from app.config import settings
            
            if not settings.database.enabled:
                return False, "Database not enabled"
            
            normalized_url = self.normalize_url(article.url)
            
            # Check for exact URL match in database
            existing_article = ArticleService.check_article_exists_by_url(article.url)
            if existing_article:
                return True, f"Exact URL match in database: {article.url}"
            
            # Check for normalized URL match
            if article.url != normalized_url:
                existing_article = ArticleService.check_article_exists_by_url(normalized_url)
                if existing_article:
                    return True, f"Normalized URL match in database: {normalized_url}"
            
            return False, ""
            
        except Exception as e:
            logger.warning(f"Failed to check URL duplication in database: {e}")
            return False, "Database check failed"
    
    def is_duplicate_by_content(self, article: Article) -> Tuple[bool, str]:
        """
        Check if article is duplicate based on content by comparing with database.
        
        Args:
            article: Article to check
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        try:
            from app.db.services import ArticleService
            from app.config import settings
            
            if not settings.database.enabled:
                return False, "Database not enabled"
            
            # Get recent articles for content comparison
            recent_articles = ArticleService.get_recent_articles(days=7, limit=1000)
            
            content_hash = self.calculate_content_hash(article.content)
            
            # Check for similar content against recent articles
            for existing_article in recent_articles:
                # Check exact content hash match
                existing_hash = self.calculate_content_hash(existing_article.content)
                if content_hash == existing_hash:
                    return True, f"Exact content match in database (hash: {content_hash[:8]}...)"
                
                # Check content similarity
                similarity = self.calculate_content_similarity(article.content, existing_article.content)
                if similarity >= self.content_similarity_threshold:
                    return True, f"Similar content in database (similarity: {similarity:.2f}) to: {existing_article.title[:50]}..."
            
            return False, ""
            
        except Exception as e:
            logger.warning(f"Failed to check content duplication in database: {e}")
            return False, "Database check failed"
    
    def is_duplicate(self, article: Article) -> Tuple[bool, str]:
        """
        Check if article is duplicate based on all criteria.
        
        Args:
            article: Article to check
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        # Check URL duplication
        url_duplicate, url_reason = self.is_duplicate_by_url(article)
        if url_duplicate:
            return True, f"URL duplicate: {url_reason}"
        
        # Check content duplication
        content_duplicate, content_reason = self.is_duplicate_by_content(article)
        if content_duplicate:
            return True, f"Content duplicate: {content_reason}"
        
        return False, ""
    
    def deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """
        Remove duplicate articles from a list by comparing with database.
        
        Args:
            articles: List of articles to deduplicate
            
        Returns:
            List of unique articles
        """
        unique_articles = []
        duplicates_found = 0
        
        logger.info(f"Starting deduplication of {len(articles)} articles...")
        
        for article in articles:
            is_dup, reason = self.is_duplicate(article)
            
            if is_dup:
                duplicates_found += 1
                logger.info(f"Skipping duplicate article: {article.title[:50]}... - {reason}")
            else:
                unique_articles.append(article)
                logger.debug(f"Added unique article: {article.title[:50]}...")
        
        logger.info(f"Deduplication complete: {len(unique_articles)} unique articles, {duplicates_found} duplicates removed")
        return unique_articles
    



# Global deduplicator instance
_global_deduplicator = None

def get_deduplicator() -> ArticleDeduplicator:
    """
    Get the global deduplicator instance.
    
    Returns:
        Global ArticleDeduplicator instance
    """
    global _global_deduplicator
    if _global_deduplicator is None:
        _global_deduplicator = ArticleDeduplicator()
    return _global_deduplicator