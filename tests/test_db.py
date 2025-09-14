import os
import unittest
from datetime import datetime

from app.models import Article, ProcessedArticle, Digest
from app.db.database import init_db, get_session
from app.db.services import ArticleService, ProcessedArticleService, DigestService


class TestDatabaseServices(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 使用测试数据库文件
        test_db_path = "test_news_tracker.db"
        # 如果测试数据库已存在，先删除
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        # 初始化测试数据库
        init_db(test_db_path)
        cls.test_db_path = test_db_path
    
    @classmethod
    def tearDownClass(cls):
        # 测试结束后删除测试数据库
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
    
    def test_article_service(self):
        # 创建测试文章
        article = Article(
            title="测试文章标题",
            url="https://example.com/test",
            content="这是一篇测试文章的内容",
            source="测试来源",
            published_at=datetime.now()
        )
        
        # 保存文章
        ArticleService.save_article(article)
        
        # 查询文章
        with get_session() as session:
            articles = ArticleService.get_articles_by_source("测试来源", session)
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].title, "测试文章标题")
            self.assertEqual(articles[0].url, "https://example.com/test")
    
    def test_processed_article_service(self):
        # 创建原始文章
        article = Article(
            title="测试文章标题",
            url="https://example.com/test2",
            content="这是另一篇测试文章的内容",
            source="测试来源",
            published_at=datetime.now()
        )
        
        # 创建处理后的文章
        processed_article = ProcessedArticle(
            original_article=article,
            summary="这是文章摘要",
            key_points=["要点1", "要点2"],
            sentiment="positive",
            tags=["标签1", "标签2"]
        )
        
        # 保存处理后的文章
        ProcessedArticleService.save_processed_article(processed_article)
        
        # 查询处理后的文章
        with get_session() as session:
            articles = ProcessedArticleService.get_recent_processed_articles(5, session)
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].summary, "这是文章摘要")
            self.assertEqual(articles[0].key_points, ["要点1", "要点2"])
            self.assertEqual(articles[0].sentiment, "positive")
    
    def test_digest_service(self):
        # 创建原始文章
        article1 = Article(
            title="摘要测试文章1",
            url="https://example.com/digest1",
            content="这是摘要测试文章1的内容",
            source="测试来源",
            published_at=datetime.now()
        )
        
        article2 = Article(
            title="摘要测试文章2",
            url="https://example.com/digest2",
            content="这是摘要测试文章2的内容",
            source="测试来源",
            published_at=datetime.now()
        )
        
        # 创建处理后的文章
        processed_article1 = ProcessedArticle(
            original_article=article1,
            summary="文章1摘要",
            key_points=["文章1要点1", "文章1要点2"],
            sentiment="positive",
            tags=["标签1"]
        )
        
        processed_article2 = ProcessedArticle(
            original_article=article2,
            summary="文章2摘要",
            key_points=["文章2要点1", "文章2要点2"],
            sentiment="neutral",
            tags=["标签2"]
        )
        
        # 创建摘要
        digest = Digest(
            title="测试摘要标题",
            articles=[processed_article1, processed_article2],
            overall_summary="这是一个总体摘要"
        )
        
        # 保存摘要
        DigestService.save_digest(digest)
        
        # 查询摘要
        with get_session() as session:
            digests = DigestService.get_recent_digests(5, session)
            self.assertEqual(len(digests), 1)
            self.assertEqual(digests[0].title, "测试摘要标题")
            self.assertEqual(digests[0].overall_summary, "这是一个总体摘要")
            self.assertEqual(len(digests[0].articles), 2)


if __name__ == "__main__":
    unittest.main()