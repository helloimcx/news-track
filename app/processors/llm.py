"""
LLM Processor for summarizing articles using a Large Language Model.
"""
import aiohttp
import json
import logging
from typing import Dict, Any
from app.models import Article, ProcessedArticle
from app.config import settings # To get API endpoint, if needed from config

# Create a logger for this module
logger = logging.getLogger("NewsTracker.Processor")

class LLMProcessor:
    """
    An asynchronous processor that analyzes articles using a Large Language Model (LLM).
    It constructs prompts, calls the LLM API, and parses the response.
    It can also generate summaries of multiple articles.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", api_base_url: str = "https://api.openai.com/v1"):
        """
        Initializes the LLM processor.

        Args:
            api_key: The API key for the LLM service.
            model: The specific model to use (e.g., 'gpt-3.5-turbo').
            api_base_url: The base URL for the LLM API. Defaults to OpenAI's API.
        """
        self.api_key = api_key
        self.model = model
        self.api_base_url = api_base_url
        self.endpoint = f"{self.api_base_url}/chat/completions"

    async def process_article(self, article: Article) -> ProcessedArticle:
        """
        Asynchronously processes a single Article using the LLM.

        Args:
            article: The Article object to process.

        Returns:
            A ProcessedArticle object containing the analysis.
        """
        prompt = self._build_prompt(article)
        logger.debug(f"LLM Prompt for article '{article.title}':{prompt}---")

        try:
            llm_response_text = await self._call_llm_api(prompt)
            logger.debug(f"Raw LLM Response for article '{article.title}':{llm_response_text}---")
            # Parse the LLM response into a ProcessedArticle using the class method
            return ProcessedArticle.from_llm_response(article, llm_response_text)
        except Exception as e:
            # Log the error
            logger.error(f"Failed to process article '{article.title}': {e}", exc_info=True)
            # Re-raise the exception to be handled by the caller
            raise

    async def process(self, article: Article) -> ProcessedArticle:
        """
        Alias for process_article to match test expectations.
        """
        return await self.process_article(article)
        
    async def summarize_articles(self, articles: list[Article]) -> str:
        """
        生成多篇文章的汇总摘要。
        
        Args:
            articles: 要汇总的文章列表。
            
        Returns:
            汇总摘要文本。
        """
        if not articles:
            return "没有文章可供汇总。"
            
        if len(articles) == 1:
            # 如果只有一篇文章，直接处理它
            processed = await self.process_article(articles[0])
            return processed.summary
            
        # 构建汇总提示
        prompt = self._build_summary_prompt(articles)
        
        try:
            # 调用LLM API获取汇总
            summary_text = await self._call_llm_api(prompt)
            
            # 尝试解析JSON响应
            try:
                summary_data = json.loads(summary_text)
                return summary_data.get("summary", summary_text)
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接返回文本
                return summary_text
                
        except Exception as e:
            logger.error(f"生成汇总摘要时出错: {e}")
            return f"生成汇总时出错: {str(e)}"

    def _build_prompt(self, article: Article) -> str:
        """
        Builds the prompt to send to the LLM for processing an article.

        Args:
            article: The Article object to build a prompt for.

        Returns:
            A string containing the formatted prompt for the LLM.
        """
        prompt = (
            f"Summarize the following article and provide key points, sentiment, and relevant tags.\n\n"
            f"Title: {article.title}\n"
            f"Content: {article.content}\n\n"
            f"Please respond in the following JSON format:\n"
            f"{{\"summary\": \"...\", \"key_points\": [\"...\"], \"sentiment\": 0.0, \"tags\": [\"...\"]}}"
        )
        return prompt
        
    def _build_summary_prompt(self, articles: list[Article]) -> str:
        """
        构建用于汇总多篇文章的提示。
        
        Args:
            articles: 要汇总的文章列表。
            
        Returns:
            用于LLM的提示字符串。
        """
        # 构建提示的开头部分
        prompt = "请对以下多篇关于广东公务员考试的文章进行汇总分析，提取重要信息，并生成一个全面的摘要。\n\n"
        
        # 添加每篇文章的信息
        for i, article in enumerate(articles, 1):
            # 限制每篇文章内容长度，避免提示过长
            content = article.content
            if len(content) > 1000:
                content = content[:1000] + "...(内容已截断)"
                
            prompt += f"文章 {i}:\n标题: {article.title}\n内容: {content}\n\n"
        
        # 添加响应格式要求
        prompt += (
            "请以JSON格式回复，包含以下字段:\n"
            "{\"summary\": \"全面汇总的摘要\", "
            "\"key_points\": [\"要点1\", \"要点2\", ...], "
            "\"important_dates\": [\"日期1: 事件\", \"日期2: 事件\", ...], "
            "\"advice\": \"给考生的建议\"}"
        )
        
        return prompt

    async def _call_llm_api(self, prompt: str) -> str:
        """
        Internal method to call the LLM API. This is separated to make mocking easier.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The raw text response from the LLM API.

        Raises:
            aiohttp.ClientError: If an HTTP error occurs during the API call.
            ValueError: If the LLM API returns a non-2xx status code.
        """
        # 1. Prepare the payload for the LLM API
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "response_format": { "type": "json_object" } # Explicitly request JSON
        }

        # 2. Set up headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 3. Make the asynchronous HTTP POST request
        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=payload, headers=headers) as response:
                # 4. Handle potential HTTP errors
                response.raise_for_status() # This will raise aiohttp.ClientError for bad status

                # 5. Get the response text
                response_text = await response.text()
                
                # 6. Attempt to parse the full API response to extract the content
                try:
                    full_response_data = json.loads(response_text)
                    # Standard OpenAI response structure
                    content_text = full_response_data["choices"][0]["message"]["content"]
                    return content_text
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    # If parsing fails, log and return the raw text
                    # This might indicate a problem with the API response format
                    logger.warning(f"Could not parse full LLM API response structure: {e}. Returning raw text.")
                    return response_text