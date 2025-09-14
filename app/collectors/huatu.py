"""华图教育网收集器，用于获取考公信息。"""
import logging
import asyncio
from typing import List
import aiohttp
from bs4 import BeautifulSoup
from app.models import Article
from app.config import settings

logger = logging.getLogger("NewsTracker.HuatuCollector")

class HuatuCollector:
    """
    华图教育网收集器，用于获取考公信息。
    """
    
    def __init__(self, num_results: int = 5, topic: str = None, max_articles: int = 10):
        """
        初始化华图教育网收集器。
        
        Args:
            num_results: 要获取的结果数量。
            topic: 订阅主题，例如"广东考公"。
            max_articles: 最大处理文章数量。
        """
        self.base_url = "https://www.huatu.com"
        self.topic = topic
        
        # 根据主题设置URL
        if topic and "广东考公" in topic:
            self.url = "https://www.huatu.com/gdgwy/"
        else:
            self.url = self.base_url
            
        self.num_results = num_results
        self.max_articles = max_articles
        logger.info(f"初始化华图教育网收集器，主题：{topic or '默认'}, 获取 {num_results} 条结果，最大处理 {max_articles} 篇文章")
    
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
                
                # 查找所有文章链接
                # 华图网站的文章链接通常在ul标签中的li>a结构中
                for ul in soup.find_all('ul', class_='clear'):
                    for li in ul.find_all('li'):
                        a_tag = li.find('a')
                        if a_tag and a_tag.has_attr('href'):
                            article_url = a_tag['href']
                            # 确保URL是完整的
                            if not article_url.startswith('http'):
                                if article_url.startswith('/'):
                                    article_url = self.base_url + article_url
                                else:
                                    article_url = self.base_url + '/' + article_url
                            article_urls.append(article_url)
                
                # 如果没有找到文章链接，尝试其他选择器
                if not article_urls:
                    for a_tag in soup.find_all('a'):
                        if a_tag.has_attr('href') and a_tag.text.strip():
                            href = a_tag['href']
                            if href.endswith('.html') or '/html/' in href:
                                # 确保URL是完整的
                                if not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = self.base_url + href
                                    else:
                                        href = self.base_url + '/' + href
                                article_urls.append(href)
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
                
                # 提取标题
                title = soup.title.text if soup.title else "华图教育网文章"
                
                # 尝试获取文章主体内容
                article_content = ""
                # 大多数文章内容通常在特定的div中
                content_div = soup.find('div', class_='article-content') or soup.find('div', class_='content')
                if content_div:
                    article_content = content_div.get_text(separator="\n", strip=True)
                else:
                    # 如果找不到特定的内容div，则获取整个body的文本
                    article_content = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
                
                # 限制内容长度
                if len(article_content) > 5000:
                    article_content = article_content[:5000] + "..."
                
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
                
                # 提取标题
                title = "广东公务员考试信息 - 华图教育网"
                
                # 提取主要内容
                content_text = ""
                
                # 尝试获取招考信息区域
                info_section = soup.select_one('.zhaokao-info')
                if not info_section:
                    # 如果没有找到特定的区域，尝试获取页面中的主要内容
                    content_selectors = [
                        '.main-content',
                        '.content',
                        '.article-content',
                        'main',
                        'article',
                        'body'
                    ]
                    
                    for selector in content_selectors:
                        content_elem = soup.select_one(selector)
                        if content_elem:
                            # 移除脚本和样式元素
                            for script in content_elem(["script", "style", "nav", "header", "footer", "aside"]):
                                script.decompose()
                            
                            content_text = content_elem.get_text(separator=' ', strip=True)
                            if len(content_text) > 200:  # 只有当我们获取到足够的内容时才使用
                                break
                else:
                    # 如果找到了招考信息区域，提取其中的文本
                    for script in info_section(["script", "style"]):
                        script.decompose()
                    content_text = info_section.get_text(separator=' ', strip=True)
                
                # 如果没有足够的内容，尝试提取所有文本
                if not content_text or len(content_text) < 100:
                    logger.warning(f"从华图教育网提取的内容不足")
                    # 尝试提取页面中的所有文本作为备选
                    body = soup.find('body')
                    if body:
                        for script in body(["script", "style"]):
                            script.decompose()
                        content_text = body.get_text(separator=' ', strip=True)
                
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