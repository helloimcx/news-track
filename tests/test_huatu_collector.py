import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.collectors.huatu import HuatuCollector
from app.models import Article


class TestHuatuCollector:
    """测试华图教育网收集器"""
    
    def test_init(self):
        """测试初始化"""
        collector = HuatuCollector(num_results=10)
        assert collector.url == "https://www.huatu.com/gdgwy/zhaokao/gg/"
        assert collector.num_results == 10

        # 测试默认参数
        collector_default = HuatuCollector()
        assert collector_default.num_results == 5
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_articles_success(self, mock_session):
        """测试成功获取文章"""
        # 创建模拟导航页响应，包含指定的CSS结构和文章链接
        mock_nav_response = Mock()
        mock_nav_response.raise_for_status = Mock()
        mock_nav_response.text = AsyncMock(return_value='''
            <html>
                <head><title>华图教育网招考公告</title></head>
                <body>
                    <div class="articleBox">
                        <div class="Width">
                            <div class="artBox_left">
                                <div class="fxlist_Conday">
                                    <a href="/gdgwy/zhaokao/gg/20240101.html">2024年广东公务员招考公告</a>
                                    <a href="/gdgwy/zhaokao/gg/20240102.html">2024年深圳市考试公告</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
        ''')
        mock_nav_response.__aenter__ = AsyncMock(return_value=mock_nav_response)
        mock_nav_response.__aexit__ = AsyncMock(return_value=None)

        # 创建模拟文章内容响应
        mock_article_response = Mock()
        mock_article_response.raise_for_status = Mock()
        mock_article_response.text = AsyncMock(return_value='''
            <html>
                <head><title>2024年广东公务员招考公告</title></head>
                <body>
                    <div class="main-content">
                        <h1>2024年广东公务员招考公告</h1>
                        <div class="article-content">
                            广东公务员考试网提供2024年广东公务员招考信息，2024年广东公务员考试公告，
                            广东公务员考试职位表，考试大纲，考试时间，报名时间等欢迎关注本页面。
                            这是一个足够长的内容，用来确保通过内容长度检查。
                        </div>
                    </div>
                </body>
            </html>
        ''')
        mock_article_response.__aenter__ = AsyncMock(return_value=mock_article_response)
        mock_article_response.__aexit__ = AsyncMock(return_value=None)

        # 创建模拟会话
        mock_session_instance = Mock()
        # 第一次调用返回导航页，后续调用返回文章内容
        mock_session_instance.get = Mock(side_effect=[mock_nav_response, mock_article_response])
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance

        collector = HuatuCollector(num_results=1)  # 只获取1篇文章
        articles = await collector.fetch_articles()

        assert len(articles) == 1
        assert isinstance(articles[0], Article)
        assert articles[0].title == "2024年广东公务员招考公告"
        assert "广东公务员考试网提供" in articles[0].content
        assert articles[0].source == "华图教育网"
        assert articles[0].url == "https://www.huatu.com/gdgwy/zhaokao/gg/20240101.html"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_articles_no_content(self, mock_session):
        """测试没有足够内容的情况"""
        # 创建模拟导航页响应，包含指定的CSS结构但内容很短
        mock_nav_response = Mock()
        mock_nav_response.raise_for_status = Mock()
        mock_nav_response.text = AsyncMock(return_value='''
            <html>
                <head><title>华图教育网招考公告</title></head>
                <body>
                    <div class="articleBox">
                        <div class="Width">
                            <div class="artBox_left">
                                <div class="fxlist_Conday">
                                    <a href="/gdgwy/zhaokao/gg/20240101.html">短文章</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
        ''')
        mock_nav_response.__aenter__ = AsyncMock(return_value=mock_nav_response)
        mock_nav_response.__aexit__ = AsyncMock(return_value=None)

        # 创建模拟文章内容响应，内容很短
        mock_article_response = Mock()
        mock_article_response.raise_for_status = Mock()
        mock_article_response.text = AsyncMock(return_value='''
            <html>
                <head><title>华图教育网招考公告</title></head>
                <body>
                    <div class="main-content">
                        <div class="article-content">
                            很短的内容
                        </div>
                    </div>
                </body>
            </html>
        ''')
        mock_article_response.__aenter__ = AsyncMock(return_value=mock_article_response)
        mock_article_response.__aexit__ = AsyncMock(return_value=None)

        # 创建模拟会话
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(side_effect=[mock_nav_response, mock_article_response])
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance

        collector = HuatuCollector()
        articles = await collector.fetch_articles()

        assert articles == []
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_fetch_articles_http_error(self, mock_session):
        """测试HTTP错误的情况"""
        # 创建模拟会话，模拟HTTP错误
        mock_session_instance = Mock()
        mock_session_instance.get = Mock(side_effect=asyncio.TimeoutError())
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        collector = HuatuCollector()
        articles = await collector.fetch_articles()
        
        assert articles == []