import pytest
from datetime import datetime
from app.models import Article, ProcessedArticle, Digest

class TestArticle:
    def test_article_creation(self):
        """Test creating an Article instance with valid data."""
        data = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": "This is the content of the article.",
            "source": "Test Source",
            "published_at": datetime(2023, 10, 27, 10, 0, 0)
        }
        article = Article(**data)
        
        assert article.title == data["title"]
        assert article.url == data["url"]
        assert article.content == data["content"]
        assert article.source == data["source"]
        assert article.published_at == data["published_at"]
        # id and created_at should be auto-generated
        assert isinstance(article.id, str)
        assert isinstance(article.created_at, datetime)

    def test_article_id_is_unique(self):
        """Test that each Article instance gets a unique ID."""
        data = {"title": "Title", "url": "http://a.com", "content": "Content", "source": "Source"}
        article1 = Article(**data)
        article2 = Article(**data)
        
        assert article1.id != article2.id

class TestProcessedArticle:
    def test_processed_article_creation(self):
        """Test creating a ProcessedArticle instance."""
        original_article = Article(
            title="Original", url="http://orig.com", content="Orig content", source="Orig Source"
        )
        
        processed_data = {
            "original_article": original_article,
            "summary": "This is a summary.",
            "key_points": ["Point 1", "Point 2"],
            "sentiment": 0.5,
            "tags": ["tech", "ai"]
        }
        processed_article = ProcessedArticle(**processed_data)
        
        assert processed_article.original_article.id == original_article.id
        assert processed_article.summary == processed_data["summary"]
        assert processed_article.key_points == processed_data["key_points"]
        assert processed_article.sentiment == processed_data["sentiment"]
        assert processed_article.tags == processed_data["tags"]
        # id and processed_at should be auto-generated
        assert isinstance(processed_article.id, str)
        assert isinstance(processed_article.processed_at, datetime)

class TestDigest:
    def test_digest_creation(self):
        """Test creating a Digest instance."""
        # Create a couple of processed articles
        article1 = Article(title="A1", url="http://a1.com", content="C1", source="S1")
        pa1 = ProcessedArticle(original_article=article1, summary="Sum1")
        
        article2 = Article(title="A2", url="http://a2.com", content="C2", source="S2")
        pa2 = ProcessedArticle(original_article=article2, summary="Sum2")
        
        digest_data = {
            "title": "Weekly Digest",
            "articles": [pa1, pa2],
            "generated_at": datetime(2023, 10, 27, 12, 0, 0)
        }
        digest = Digest(**digest_data)
        
        assert digest.title == digest_data["title"]
        assert len(digest.articles) == 2
        assert digest.articles[0].id == pa1.id
        assert digest.articles[1].id == pa2.id
        assert digest.generated_at == digest_data["generated_at"]
        # id should be auto-generated
        assert isinstance(digest.id, str)
