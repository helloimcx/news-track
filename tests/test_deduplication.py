"""
Tests for the article deduplication functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from app.models import Article
from app.utils.deduplication import ArticleDeduplicator


class TestArticleDeduplicator:
    """Test cases for ArticleDeduplicator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deduplicator = ArticleDeduplicator()
        
        # Sample articles for testing
        self.article1 = Article(
            title="广东公务员考试公告发布",
            url="https://example.com/article1.html",
            content="广东省2025年公务员考试公告已经发布，报名时间为2025年1月1日至1月15日。",
            source="测试源",
            published_at=datetime.now()
        )
        
        self.article2 = Article(
            title="广东公务员考试公告发布",
            url="https://example.com/article1.html?utm_source=social",  # Same URL with tracking params
            content="广东省2025年公务员考试公告已经发布，报名时间为2025年1月1日至1月15日。",
            source="测试源",
            published_at=datetime.now()
        )
        
        self.article3 = Article(
            title="深圳市教师招聘公告",
            url="https://different-domain.com/teacher-recruitment.html",  # Different domain
            content="深圳市2025年教师招聘公告，共招聘1000名教师。",
            source="测试源",
            published_at=datetime.now()
        )
        
        self.article4 = Article(
            title="广东公务员考试公告发布详情",
            url="https://example.com/article4.html",
            content="广东省 2025年 公务员考试公告 已经发布，报名时间为 2025年1月1日 至 1月15日。",  # Similar content with different spacing
            source="测试源",
            published_at=datetime.now()
        )
    
    def test_normalize_url(self):
        """Test URL normalization."""
        original_url = "https://example.com/article?utm_source=social&utm_medium=email&id=123"
        expected = "https://example.com/article?id=123"
        
        normalized = self.deduplicator.normalize_url(original_url)
        assert normalized == expected
    
    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        content1 = "广东省 2025年 公务员 考试 公告"
        content2 = "广东省  2025年   公务员  考试  公告"  # Different spacing
        content3 = "深圳市 教师 招聘 公告"
        
        hash1 = self.deduplicator.calculate_content_hash(content1)
        hash2 = self.deduplicator.calculate_content_hash(content2)
        hash3 = self.deduplicator.calculate_content_hash(content3)
        
        # Same content with different spacing should have same hash after normalization
        assert hash1 == hash2
        # Different content should have different hash
        assert hash1 != hash3
    
    def test_calculate_content_similarity(self):
        """Test content similarity calculation."""
        content1 = "广东省2025年公务员考试公告已经发布"
        content2 = "广东省 2025年 公务员考试公告 已经发布"  # Similar with different spacing
        content3 = "深圳市教师招聘公告"  # Different content
        
        similarity1 = self.deduplicator.calculate_content_similarity(content1, content2)
        similarity2 = self.deduplicator.calculate_content_similarity(content1, content3)
        
        # Similar content should have high similarity
        assert similarity1 > 0.9
        # Different content should have low similarity
        assert similarity2 < 0.5
    
    def test_calculate_url_similarity(self):
        """Test URL similarity calculation."""
        url1 = "https://example.com/article1.html"
        url2 = "https://example.com/article1.html?utm_source=social"  # Same URL with params
        url3 = "https://example.com/article2.html"  # Different URL
        
        similarity1 = self.deduplicator.calculate_url_similarity(url1, url2)
        similarity2 = self.deduplicator.calculate_url_similarity(url1, url3)
        
        # URLs that normalize to the same should have high similarity
        assert similarity1 > 0.9
        # Different URLs should have lower similarity
        assert similarity2 < similarity1
    
    @patch('app.db.services.ArticleService.check_article_exists_by_url')
    @patch('app.config.settings')
    def test_is_duplicate_by_url(self, mock_settings, mock_check_url):
        """Test URL-based duplicate detection."""
        # Configure mock settings
        mock_settings.database.enabled = True
        
        # Test case 1: No existing article
        mock_check_url.return_value = None
        is_duplicate, reason = self.deduplicator.is_duplicate_by_url(self.article1)
        assert not is_duplicate
        
        # Test case 2: Existing article with same URL
        mock_check_url.return_value = self.article1
        is_duplicate, reason = self.deduplicator.is_duplicate_by_url(self.article2)
        assert is_duplicate
        assert "URL match" in reason
    
    @patch('app.db.services.ArticleService.get_recent_articles')
    @patch('app.config.settings')
    def test_is_duplicate_by_content(self, mock_settings, mock_get_recent):
        """Test content-based duplicate detection."""
        # Configure mock settings
        mock_settings.database.enabled = True
        
        # Test case 1: No existing articles
        mock_get_recent.return_value = []
        is_duplicate, reason = self.deduplicator.is_duplicate_by_content(self.article1)
        assert not is_duplicate
        
        # Test case 2: Existing article with similar content
        mock_get_recent.return_value = [self.article1]
        is_duplicate, reason = self.deduplicator.is_duplicate_by_content(self.article4)
        assert is_duplicate
        assert "content" in reason.lower()
        
        # Test case 3: Existing article with different content
        mock_get_recent.return_value = [self.article1]
        is_duplicate, reason = self.deduplicator.is_duplicate_by_content(self.article3)
        assert not is_duplicate
    
    @patch('app.config.settings')
    def test_deduplicate_articles_simple(self, mock_settings):
        """Test basic article deduplication functionality."""
        # Test with database disabled (no actual database calls)
        mock_settings.database.enabled = False
        
        articles = [self.article1, self.article2, self.article3]
        unique_articles = self.deduplicator.deduplicate_articles(articles)
        
        # When database is disabled, all articles should be kept
        assert len(unique_articles) == 3
        
        # Test individual duplicate detection methods
        is_dup, reason = self.deduplicator.is_duplicate_by_url(self.article1)
        assert not is_dup
        assert "Database not enabled" in reason
    
    def test_database_disabled(self):
        """Test behavior when database is disabled."""
        with patch('app.config.settings') as mock_settings:
            mock_settings.database.enabled = False
            
            # Should return False for all duplicate checks
            is_duplicate, reason = self.deduplicator.is_duplicate_by_url(self.article1)
            assert not is_duplicate
            assert "Database not enabled" in reason
            
            is_duplicate, reason = self.deduplicator.is_duplicate_by_content(self.article1)
            assert not is_duplicate
            assert "Database not enabled" in reason


if __name__ == "__main__":
    pytest.main([__file__])