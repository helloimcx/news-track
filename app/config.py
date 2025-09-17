"""
Application configuration management using Pydantic Settings.
"""
import os
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Nested Configuration Models ---

class DeduplicationConfig(BaseModel):
    """Configuration for article deduplication."""
    enabled: bool = True
    url_similarity_threshold: float = 0.95
    content_similarity_threshold: float = 0.85
    load_existing_days: int = 7  # Days to look back for existing articles

class SchedulerConfig(BaseModel):
    """Configuration for the scheduler."""
    timezone: str = "Asia/Shanghai"
    # Scheduler mode: 'cron' for specific time, 'interval' for periodic execution
    mode: str = "interval"  # "cron" or "interval"
    # Interval settings (used when mode='interval')
    interval_hours: int = 1  # Run every X hours
    interval_minutes: int = 0  # Additional minutes (optional)
    # Cron settings (used when mode='cron')
    hour: int | None = 9
    minute: int | None = 0
    second: int | None = 0
    # Add more scheduler-specific settings here if needed

class SearchConfig(BaseModel):
    """Configuration for article search - supports both topic-based search and RSS feeds."""
    # The main topic to search for (if specified, will use Google Search)
    topic: str | None = None
    # Number of search results to fetch when using topic search
    num_results: int = 5
    # RSS feed configuration (used when no topic is specified)
    rss_feed_url: str | None = None
    rss_feed_urls: list[str] | None = None

class DirectWebConfig(BaseModel):
    """Configuration for Direct Web collector."""
    # A list of website URLs to scrape directly
    site_urls: list[str] | None = None
    # Number of articles to fetch per site (if applicable)
    articles_per_site: int = 5

class HuatuConfig(BaseModel):
    """
    Configuration for Huatu collector.
    """
    # Number of results to fetch
    num_results: int = 5
    # Maximum number of articles to process
    max_articles: int = 10
    # Enable or disable the collector
    enabled: bool = False
    # Topic to search for
    topic: str | None = None

class WebSearchConfig(BaseModel):
    """Configuration for Web Search collector."""
    # The search engine URL to use (e.g., https://www.google.com/search, https://duckduckgo.com)
    search_engine_url: str = "https://duckduckgo.com"
    # Number of search results to fetch and process
    num_results: int = 5
    # Google API Key for using the Custom Search API
    google_api_key: str | None = None
    # Google Custom Search Engine ID
    google_cse_id: str | None = None

class LLMConfig(BaseModel):
    """Configuration for the LLM processor."""
    api_key: str # This will be loaded from env var OPENAI_API_KEY by default
    model: str = "gpt-4o-mini" # Default model
    api_base_url: str = "https://api.openai.com/v1" # Default OpenAI API base URL

class EmailConfig(BaseModel):
    """Configuration for the email notifier."""
    smtp_server: str
    smtp_port: int = 587
    username: str
    password: str
    sender_email: str
    recipient_emails: str # Comma-separated list of emails

# --- Main Settings Class ---

class DatabaseConfig(BaseModel):
    """数据库配置"""
    # 数据库文件路径，如果为None则使用默认路径（data/news_tracker.db）
    db_path: str | None = None
    # 是否启用持久化存储
    enabled: bool = True

class Settings(BaseSettings):
    """
    Main application settings.
    Values are loaded from environment variables or .env file, with defaults provided.
    Nested models can be configured using a delimiter, e.g., SCHEDULER_TIMEZONE.
    """
    model_config = SettingsConfigDict(
        env_file=".env",  # Load from .env file
        env_file_encoding='utf-8',
        case_sensitive=False,  # Environment variables are case-insensitive
        env_nested_delimiter="__"  # Delimiter for nested models, e.g., scheduler__timezone
    )

    # --- Application Core Settings ---
    app_name: str = "NewsTracker"
    log_level: str = "INFO"
    
    # --- Database Settings ---
    database: DatabaseConfig = DatabaseConfig()
    
    # --- Search Settings (Topic-based or RSS) ---
    search: SearchConfig = SearchConfig()
    
    # --- Web Search Collector Settings ---
    websearch: WebSearchConfig = WebSearchConfig()
    
    # --- Huatu Collector Settings ---
    huatu: HuatuConfig = HuatuConfig()
    
    # --- LLM Processor Settings ---
    llm: LLMConfig = LLMConfig(api_key="") # api_key will be loaded from env var
    
    # --- Scheduler Settings ---
    scheduler: SchedulerConfig = SchedulerConfig()
    
    # --- Deduplication Settings ---
    deduplication: DeduplicationConfig = DeduplicationConfig()
    
    # --- Email Notifier Settings (Optional) ---
    email: EmailConfig | None = None

# --- Singleton Instance ---
# Create a single instance of Settings to be used throughout the application
# This ensures consistent configuration access and parsing happens only once.
settings = Settings()
