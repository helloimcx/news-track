import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.collectors.google_search import GoogleSearchCollector
from app.models import Article


class TestGoogleSearchCollector:
    """测试Google搜索收集器"""
    
    def test_init(self):
        """测试初始化"""
        collector = GoogleSearchCollector("test topic", num_results=10)
        assert collector.topic == "test topic"
        assert collector.num_results == 10
        
        # 测试默认参数
        collector_default = GoogleSearchCollector("test topic")
        assert collector_default.num_results == 5
    
    @pytest.mark.asyncio
    @patch('app.collectors.google_search.search')
    @patch('aiohttp.ClientSession')
    async def test_fetch_articles_success(self, mock_session, mock_search):
        """测试成功获取文章"""
        # 模拟Google搜索结果
        mock_search.return_value = [
            'https://example1.com',
            'https://example2.com'
        ]
        
        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = AsyncMock(return_value='''
            <html>
                <head><title>Test Article</title></head>
                <body>
                    <div class="content">
                        <p>This is a test article with enough content to pass the minimum length requirement. 
                        It contains multiple sentences and provides substantial information about the topic.</p>
                    </div>
                </body>
            </html>
        ''')
        
        mock_session_instance = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session_instance.get = Mock(return_value=mock_response)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        collector = GoogleSearchCollector("test topic", num_results=2)
        articles = await collector.fetch_articles()
        
        assert len(articles) == 2
        assert all(isinstance(article, Article) for article in articles)
        assert all(article.title == "Test Article" for article in articles)
        
    @pytest.mark.asyncio
    @patch('app.collectors.google_search.search')
    async def test_fetch_articles_no_results(self, mock_search):
        """测试没有搜索结果的情况"""
        mock_search.return_value = []
        
        collector = GoogleSearchCollector("test topic")
        articles = await collector.fetch_articles()
        
        assert articles == []
    
    @pytest.mark.asyncio
    @patch('app.collectors.google_search.search')
    @patch('aiohttp.ClientSession')
    async def test_fetch_articles_with_failures(self, mock_session, mock_search):
        """测试部分文章获取失败的情况"""
        mock_search.return_value = [
            'https://example1.com',
            'https://example2.com',
            'https://example3.com'
        ]
        
        # 模拟第一个成功，第二个失败，第三个成功
        response1 = Mock(
             raise_for_status=Mock(),
             text=AsyncMock(return_value='''
                 <html><head><title>Success 1</title></head>
                 <body><p>This is successful content with enough text to pass validation. This content needs to be longer than 100 characters to pass the minimum content length requirement in the GoogleSearchCollector implementation.</p></body></html>
             ''')
         )
        response1.__aenter__ = AsyncMock(return_value=response1)
        response1.__aexit__ = AsyncMock(return_value=None)
        
        response2 = Mock(raise_for_status=Mock(side_effect=Exception("HTTP Error")))
        response2.__aenter__ = AsyncMock(return_value=response2)
        response2.__aexit__ = AsyncMock(return_value=None)
        
        response3 = Mock(
             raise_for_status=Mock(),
             text=AsyncMock(return_value='''
                 <html><head><title>Success 2</title></head>
                 <body><p>This is another successful content with enough text to pass validation. This content also needs to be longer than 100 characters to pass the minimum content length requirement in the GoogleSearchCollector implementation.</p></body></html>
             ''')
         )
        response3.__aenter__ = AsyncMock(return_value=response3)
        response3.__aexit__ = AsyncMock(return_value=None)
        
        responses = [response1, response2, response3]
        
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(side_effect=responses)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        collector = GoogleSearchCollector("test topic", num_results=3)
        articles = await collector.fetch_articles()
        
        # 应该只有2篇成功的文章
        assert len(articles) == 2
        assert articles[0].title == "Success 1"
        assert articles[1].title == "Success 2"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_and_parse_article_insufficient_content(self, mock_session):
        """测试内容不足的文章被过滤"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = AsyncMock(return_value='''
            <html>
                <head><title>Short Article</title></head>
                <body><p>Too short</p></body>
            </html>
        ''')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(return_value=mock_response)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        
        collector = GoogleSearchCollector("test topic")
        article = await collector._fetch_and_parse_article(mock_session_instance, "https://example.com")
        
        assert article is None
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_and_parse_article_timeout(self, mock_session):
        """测试请求超时的情况"""
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(side_effect=asyncio.TimeoutError())
        
        collector = GoogleSearchCollector("test topic")
        article = await collector._fetch_and_parse_article(mock_session_instance, "https://example.com")
        
        assert article is None
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_and_parse_article_content_truncation(self, mock_session):
        """测试长内容被截断"""
        long_content = "A" * 6000  # 超过5000字符的内容
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = AsyncMock(return_value=f'''
            <html>
                <head><title>Long Article</title></head>
                <body><p>{long_content}</p></body>
            </html>
        ''')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(return_value=mock_response)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        
        collector = GoogleSearchCollector("test topic")
        article = await collector._fetch_and_parse_article(mock_session_instance, "https://example.com")
        
        assert article is not None
        assert len(article.content) <= 5003  # 5000 + "..."
        assert article.content.endswith("...")
    
    def test_article_model_validation(self):
        """测试Article模型字段验证"""
        # 测试正确的Article创建
        article = Article(
            title="Test Title",
            content="Test content",
            url="https://example.com",
            source="https://example.com"
        )
        
        assert article.title == "Test Title"
        assert article.content == "Test content"
        assert article.url == "https://example.com"
        assert article.source == "https://example.com"
        assert article.id is not None
        assert article.created_at is not None
        
        # 测试缺少必需字段时的验证错误
        with pytest.raises(Exception):  # Pydantic validation error
            Article(
                title="Test Title",
                content="Test content",
                url="https://example.com"
                # 缺少source字段
            )