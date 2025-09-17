"""华图教育网收集器，用于获取考公信息。"""
import logging
import asyncio
from typing import List
import aiohttp
from bs4 import BeautifulSoup, Tag
from app.models import Article
from app.config import settings

logger = logging.getLogger("NewsTracker.HuatuCollector")

class HuatuCollector:
    """
    华图教育网收集器，用于获取考公信息。
    """
    
    def __init__(self, num_results: int = 5, topic: str | None = None, max_articles: int = 10):
        """
        初始化华图教育网收集器。

        Args:
            num_results: 要获取的结果数量。
            topic: 订阅主题，例如"广东考公"。
            max_articles: 最大处理文章数量。
        """
        self.base_url = "https://www.huatu.com"
        self.topic = topic

        # 使用新的招考公告URL
        self.url = "https://www.huatu.com/gdgwy/zhaokao/gg/"

        self.num_results = num_results
        self.max_articles = max_articles
        logger.info(f"初始化华图教育网收集器，主题：{topic or '招考公告'}, 获取 {num_results} 条结果，最大处理 {max_articles} 篇文章")
    
    async def fetch_articles(self) -> List[Article]:
        """
        从华图教育网获取考公信息文章。
        
        Returns:
            包含文章信息的Article对象列表。
        """
        logger.info(f"开始从华图教育网获取考公信息")
        articles = []
        
        try:
            # 创建HTTP会话
            async with aiohttp.ClientSession() as session:
                # 首先获取导航页上的文章链接
                article_urls = await self._extract_article_urls(session)
                logger.info(f"华图教育网收集器找到 {len(article_urls)} 个文章链接")
                
                # 限制获取的文章数量
                article_urls = article_urls[:self.num_results]
                
                # 获取每篇文章的详细内容
                for url in article_urls:
                    article = await self._fetch_article_content(session, url)
                    if article:
                        articles.append(article)
                        logger.debug(f"成功解析文章: {article.title}")
                    else:
                        logger.warning(f"无法从链接解析文章: {url}")
                        
        except Exception as e:
            logger.error(f"获取华图教育网信息时出错: {e}")
            
        logger.info(f"完成华图教育网信息获取。收集了 {len(articles)} 篇文章。")
        return articles
        
    async def _extract_article_urls(self, session: aiohttp.ClientSession) -> List[str]:
        """
        从导航页提取文章链接

        Args:
            session: 用于请求的aiohttp会话。

        Returns:
            文章URL列表
        """
        article_urls = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }

            async with session.get(self.url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                # 尝试使用不同的编码方式解析内容
                try:
                    content = await response.text()
                except UnicodeDecodeError:
                    # 如果默认编码失败，尝试使用 GB2312 或 GBK 编码
                    raw_content = await response.read()
                    try:
                        content = raw_content.decode('gb2312', errors='ignore')
                    except UnicodeDecodeError:
                        content = raw_content.decode('gbk', errors='ignore')

                # 解析HTML内容
                soup = BeautifulSoup(content, 'html.parser')
                logger.debug(f"获取到页面内容长度: {len(content)}")

                # 基于实际页面结构查找招考公告链接
                # 使用用户指定的精确CSS选择器
                target_container = soup.select_one('body > div.articleBox > div.Width > div.artBox_left > div.fxlist_Conday')
                
                if target_container:
                    # 从指定容器中提取所有链接
                    links = target_container.find_all('a', href=True)
                    logger.debug(f"在指定容器中找到 {len(links)} 个链接")
                    
                    for link in links:
                        if not isinstance(link, Tag):
                            continue
                        href = link.get('href')
                        if not href or not isinstance(href, str):
                            continue
                            
                        link_text = link.get_text(strip=True)
                        
                        # 跳过明显的导航和无关链接
                        if href.startswith('#') or href.startswith('javascript:'):
                            continue
                        
                        # 跳过外部链接和非内容链接
                        if (href.startswith('http') and 'huatu.com' not in href) or \
                           any(skip_word in href.lower() for skip_word in ['login', 'register', 'member', 'course', 'book', 'weixin', 'app']):
                            continue
                        
                        # 处理相对URL
                        if href.startswith('//'):
                            article_url = 'https:' + href
                        elif href.startswith('/'):
                            article_url = self.base_url + href
                        elif not href.startswith('http'):
                            article_url = self.base_url + '/' + href
                        else:
                            article_url = href
                        
                        # 避免重复
                        if article_url not in article_urls:
                            article_urls.append(article_url)
                            logger.debug(f"从指定容器找到链接: {link_text[:50]}... -> {article_url}")
                else:
                    logger.warning("未找到指定的容器: div.fxlist_Conday")
                
                logger.info(f"从指定容器提取到 {len(article_urls)} 个文章链接")
                
        except Exception as e:
            logger.error(f"提取文章链接时出错: {e}")

        return article_urls
        
    async def _fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> Article | None:
        """
        获取文章内容

        Args:
            session: 用于请求的aiohttp会话。
            url: 文章URL

        Returns:
            如果成功，返回Article对象，否则返回None。
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }

            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                # 尝试使用不同的编码方式解析内容
                try:
                    content = await response.text()
                except UnicodeDecodeError:
                    # 如果默认编码失败，尝试使用 GB2312 或 GBK 编码
                    raw_content = await response.read()
                    try:
                        content = raw_content.decode('gb2312', errors='ignore')
                    except UnicodeDecodeError:
                        content = raw_content.decode('gbk', errors='ignore')

                # 解析HTML内容
                soup = BeautifulSoup(content, 'html.parser')

                # 提取标题 - 尝试多种可能的选择器
                title_selectors = [
                    'title',
                    'h1.article-title',
                    'h1.news-title',
                    '.title h1',
                    'h1'
                ]
                title = "华图教育网招考公告"
                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break

                # 尝试获取文章主体内容
                article_content = ""
                # 尝试多种可能的内容区域选择器
                content_selectors = [
                    '.article-content',
                    '.content',
                    '.news-content',
                    '.zhaokao-content',
                    '.main-content',
                    'article',
                    '.article-body',
                    '.news-body'
                ]

                for selector in content_selectors:
                    content_div = soup.select_one(selector)
                    if content_div:
                        # 移除脚本、样式和其他不需要的元素
                        for unwanted in content_div.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                            unwanted.decompose()
                        for unwanted in content_div.find_all(class_=["ad", "advertisement"]):
                            unwanted.decompose()
                        article_content = content_div.get_text(separator="\n", strip=True)
                        if len(article_content) > 100:  # 确保有足够的内容
                            break

                # 如果没有找到特定的内容区域，则获取整个body的文本
                if not article_content:
                    body = soup.find('body')
                    if body and isinstance(body, Tag):
                        # 移除脚本、样式和其他不需要的元素
                        for unwanted in body.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                            unwanted.decompose()
                        for unwanted in body.find_all(class_=["ad", "advertisement"]):
                            unwanted.decompose()
                        article_content = body.get_text(separator="\n", strip=True)

                # 限制内容长度
                if len(article_content) > 5000:
                    article_content = article_content[:5000] + "..."

                # 如果内容仍然为空，返回None
                if not article_content or len(article_content.strip()) < 50:
                    logger.warning(f"文章内容不足: {url}")
                    return None

                return Article(
                    title=title,
                    content=article_content,
                    url=url,
                    source="华图教育网",
                    published_at=None
                )
        except Exception as e:
            logger.error(f"获取文章内容时出错: {url} - {e}")

        return None
    
    async def _fetch_and_parse_page(self, session: aiohttp.ClientSession) -> Article | None:
        """
        获取并解析华图教育网页面。

        Args:
            session: 用于请求的aiohttp会话。

        Returns:
            如果成功，返回Article对象，否则返回None。
        """
        try:
            # 设置请求头，模拟真实浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            async with session.get(self.url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                # 尝试使用不同的编码方式解析内容
                try:
                    content = await response.text()
                except UnicodeDecodeError:
                    # 如果默认编码失败，尝试使用 GB2312 或 GBK 编码
                    raw_content = await response.read()
                    try:
                        content = raw_content.decode('gb2312', errors='ignore')
                    except UnicodeDecodeError:
                        content = raw_content.decode('gbk', errors='ignore')

                # 解析HTML内容
                soup = BeautifulSoup(content, 'html.parser')

                # 提取标题 - 尝试多种可能的选择器
                title_selectors = [
                    'title',
                    'h1',
                    '.page-title',
                    '.article-title'
                ]
                title = "华图教育网招考公告"
                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break

                # 提取主要内容
                content_text = ""

                # 尝试获取招考公告页面的主要内容区域
                content_selectors = [
                    '.article-content',
                    '.content',
                    '.news-content',
                    '.zhaokao-content',
                    '.main-content',
                    'article',
                    '.article-body',
                    '.news-body'
                ]

                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # 移除脚本、样式和其他不需要的元素
                        for unwanted in content_elem(["script", "style", "nav", "header", "footer", "aside", ".ad", ".advertisement"]):
                            unwanted.decompose()

                        content_text = content_elem.get_text(separator='\n', strip=True)
                        if len(content_text) > 100:  # 只有当我们获取到足够的内容时才使用
                            break

                # 如果没有找到特定的内容区域，尝试获取body中的文本
                if not content_text:
                    body = soup.find('body')
                    if body and isinstance(body, Tag):
                        # 移除脚本、样式和其他不需要的元素
                        for unwanted in body.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                            unwanted.decompose()
                        for unwanted in body.find_all(class_=["ad", "advertisement"]):
                            unwanted.decompose()
                        content_text = body.get_text(separator='\n', strip=True)

                if not content_text or len(content_text) < 100:
                    logger.warning(f"无法从华图教育网提取足够的内容")
                    return None

                # 限制内容长度
                if len(content_text) > 5000:
                    content_text = content_text[:5000] + "..."

                return Article(
                    title=title,
                    content=content_text,
                    url=self.url,
                    source="华图教育网",
                    published_at=None  # 在这个简单实现中，我们不提取日期
                )

        except asyncio.TimeoutError:
            logger.warning(f"获取华图教育网页面超时")
        except aiohttp.ClientError as e:
            logger.warning(f"获取华图教育网页面时HTTP错误: {e}")
        except Exception as e:
            logger.error(f"获取华图教育网页面时意外错误: {e}")

        return None