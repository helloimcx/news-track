"""
Main application entry point and core logic.
"""
import asyncio
import argparse
import sys
import logging
from typing import List, Optional
from datetime import datetime
import os

# --- Logging Configuration ---
# Ensure the logs directory exists
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Create a custom logger
logger = logging.getLogger("NewsTracker")
logger.setLevel(logging.DEBUG) # Capture all messages from DEBUG level up

# Create handlers
console_handler = logging.StreamHandler(sys.stdout) # Log to stdout
file_handler = logging.FileHandler(os.path.join(LOGS_DIR, "news_tracker.log"))

# Set levels for handlers (optional, can be more specific)
console_handler.setLevel(logging.INFO) # Console shows INFO and above
file_handler.setLevel(logging.DEBUG)   # File captures everything

# Create formatters and add them to handlers
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# Add handlers to the logger
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# APScheduler imports
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from app.collectors.rss import RSSCollector
from app.collectors.huatu import HuatuCollector
from app.collectors.google_search import GoogleSearchCollector
from app.processors.llm import LLMProcessor
from app.notifiers.email import EmailNotifier
from app.utils.deduplication import get_deduplicator
# RSS discovery service removed
from app.models import Article, ProcessedArticle, Digest
from app.config import settings


async def process_articles(articles: List[Article]) -> Optional[Digest]:
    """
    处理文章并生成摘要。
    
    Args:
        articles: 要处理的文章列表。
        
    Returns:
        如果成功，返回生成的摘要，否则返回None。
    """
    if not articles:
        logger.info("没有文章需要处理。")
        return None
        
    try:
        # 初始化LLM处理器
        processor = LLMProcessor(api_key=settings.llm.api_key, model=settings.llm.model, api_base_url=settings.llm.api_base_url)
        
        # 处理文章
        processed_articles = []
        for article in articles:
            try:
                processed_article = await processor.process_article(article)
                processed_articles.append(processed_article)
                logger.info(f"成功处理文章: {article.title}")
                
                # 如果启用了数据库持久化，保存处理后的文章
                if settings.database.enabled:
                    try:
                        from app.db.services import ProcessedArticleService
                        ProcessedArticleService.save_processed_article(processed_article)
                        logger.info(f"已将文章保存到数据库: {article.title}")
                    except Exception as e:
                        logger.error(f"保存文章到数据库时出错: {e}", exc_info=True)
                        
            except Exception as e:
                logger.error(f"处理文章时出错: {e}", exc_info=True)
        
        if not processed_articles:
            logger.warning("没有成功处理的文章。")
            return None
            
        # 如果有多篇文章，生成汇总摘要
        summary_title = f"{settings.app_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        overall_summary = None
        if len(articles) > 1:
            try:
                overall_summary = await processor.summarize_articles(articles)
                if overall_summary:
                    summary_title = f"{settings.app_name} - 广东考公汇总 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    logger.info(f"成功生成汇总摘要: {overall_summary[:100]}...")
            except Exception as e:
                logger.error(f"生成汇总摘要时出错: {e}", exc_info=True)
            
        # 创建摘要
        digest = Digest(
            title=summary_title,
            articles=processed_articles,
            overall_summary=overall_summary
        )
        
        # 如果启用了数据库持久化，保存摘要
        if settings.database.enabled:
            try:
                from app.db.services import DigestService
                DigestService.save_digest(digest)
                logger.info(f"已将摘要保存到数据库: {digest.title}")
            except Exception as e:
                logger.error(f"保存摘要到数据库时出错: {e}", exc_info=True)
        
        # 发送邮件通知
        if settings.email:
            try:
                notifier = EmailNotifier(config=settings.email)
                await notifier.send_digest(digest)
                logger.info("成功发送摘要邮件。")
            except Exception as e:
                logger.error(f"发送邮件通知时出错: {e}", exc_info=True)
        
        return digest
    except Exception as e:
        logger.error(f"处理文章过程中出错: {e}", exc_info=True)
        return None

async def run_pipeline() -> Optional[Digest]:
    """
    Runs the main news processing pipeline:
    1. Discovers RSS feeds (if auto-discovery is enabled).
    2. Collects articles using RSSCollector.
    3. If RSS fails/empty and fallback is enabled, collects articles using BrowserSearchCollector.
    4. Processes articles using LLMProcessor.
    5. Packages processed articles into a Digest.
    6. Sends the Digest using EmailNotifier.

    Returns:
        The generated Digest if successful, None otherwise.
    """
    logger.info("Starting news processing pipeline...")

    # Initialize database if enabled
    if settings.database.enabled:
        try:
            from app.db.database import init_db
            init_db(settings.database.db_path)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            # Database initialization failure should not stop the entire process
    
    # Initialize deduplicator
    deduplicator = get_deduplicator()
    if settings.deduplication.enabled:
        logger.info("Deduplication is enabled - will check against database records")
    else:
        logger.info("Deduplication is disabled in configuration")
    
    # --- 1. Initialize Components ---
    # Check if required configs are present
    if not settings.email:
        logger.error("Email configuration is missing. Cannot initialize EmailNotifier.")
        raise ValueError("Email configuration is missing. Cannot initialize EmailNotifier.")
    
    # --- Determine collection strategy ---
    search_config = settings.search
    articles: List[Article] = []
    
    # --- 2. Collect Articles ---
    # 首先检查是否启用了华图教育网收集器
    if settings.huatu.enabled:
        logger.info("华图教育网收集器已启用，开始获取考公信息...")
        try:
            huatu_collector = HuatuCollector(
                num_results=settings.huatu.num_results,
                topic=settings.huatu.topic,
                max_articles=settings.huatu.max_articles
            )
            logger.info("正在通过华图教育网收集器获取文章...")
            articles = await huatu_collector.fetch_articles()
            logger.info(f"华图教育网收集：收集了 {len(articles)} 篇文章。")
            
            # Apply deduplication
            if articles and settings.deduplication.enabled:
                unique_articles = deduplicator.deduplicate_articles(articles)
                logger.info(f"去重后剩余 {len(unique_articles)} 篇文章")
                articles = unique_articles
            
            if articles:
                # 如果成功获取到文章，直接处理
                return await process_articles(articles)
        except Exception as e:
            logger.error(f"华图教育网收集过程中出错: {e}", exc_info=True)
            # 继续尝试其他收集方式
    
    # 如果华图教育网收集器未启用或未获取到文章，继续使用其他收集方式
    # If topic is specified, use Google Search; otherwise use RSS feeds
    if search_config.topic and search_config.topic.strip():
        logger.info(f"Topic specified: '{search_config.topic}'. Using Google Search...")
        try:
            google_collector = GoogleSearchCollector(
                topic=search_config.topic,
                num_results=search_config.num_results
            )
            logger.info(f"Collecting articles via Google Search for topic: '{search_config.topic}'...")
            articles = await google_collector.fetch_articles()
            logger.info(f"Google Search Collection: Collected {len(articles)} articles.")
            
            # Apply deduplication
            if articles and settings.deduplication.enabled:
                unique_articles = deduplicator.deduplicate_articles(articles)
                logger.info(f"After deduplication: {len(unique_articles)} unique articles")
                articles = unique_articles
        except Exception as e:
            logger.error(f"Error during Google Search collection: {e}", exc_info=True)
            return None
    else:
        # Use RSS feeds when no topic is specified
        feed_urls_to_use = []
        if search_config.rss_feed_urls:
            feed_urls_to_use = search_config.rss_feed_urls
        elif search_config.rss_feed_url:
            feed_urls_to_use = [search_config.rss_feed_url]
            
        if feed_urls_to_use:
            logger.info("No topic specified. Collecting articles from RSS feeds...")
            try:
                collector = RSSCollector(feed_urls=feed_urls_to_use)
                articles = await collector.collect()
                logger.info(f"RSS Collection: Collected {len(articles)} articles.")
                
                # Apply deduplication
                if articles and settings.deduplication.enabled:
                    unique_articles = deduplicator.deduplicate_articles(articles)
                    logger.info(f"After deduplication: {len(unique_articles)} unique articles")
                    articles = unique_articles
            except Exception as e:
                logger.error(f"Error during RSS collection: {e}", exc_info=True)
                return None
        else:
            logger.warning("No topic or RSS feeds configured. Cannot collect articles.")
            return None
    
    if not articles:
        logger.info("No articles collected. Exiting pipeline.")
        return None
        
    # 处理收集到的文章
    return await process_articles(articles)


async def run_scheduler():
    """
    Sets up and starts the APScheduler to run the pipeline periodically.
    The schedule is configured via app.config.settings.scheduler.
    """
    logger.info("Initializing scheduler...")
    
    # Create an AsyncIOScheduler instance
    scheduler = AsyncIOScheduler()
    
    # Get schedule parameters from settings
    sched_config = settings.scheduler
    timezone = sched_config.timezone
    mode = sched_config.mode
    
    logger.info(f"Scheduler mode: {mode}, timezone: {timezone}")

    # Add the run_pipeline job based on configuration mode
    try:
        if mode == "interval":
            # Interval mode - run periodically
            interval_hours = sched_config.interval_hours
            interval_minutes = sched_config.interval_minutes
            
            scheduler.add_job(
                run_pipeline,  # The function to call
                'interval',    # Trigger type - run at intervals
                hours=interval_hours,
                minutes=interval_minutes,
                timezone=timezone,
                id='news_digest_job' # Unique ID for the job
            )
            logger.info(f"Job 'news_digest_job' added to scheduler.")
            logger.info(f"Schedule: Every {interval_hours} hours and {interval_minutes} minutes (timezone: {timezone})")
        
        elif mode == "cron":
            # Cron mode - run at specific times
            hour = sched_config.hour if sched_config.hour is not None else 9
            minute = sched_config.minute if sched_config.minute is not None else 0
            second = sched_config.second if sched_config.second is not None else 0
            
            scheduler.add_job(
                run_pipeline,  # The function to call
                'cron',        # Trigger type
                hour=hour,
                minute=minute,
                second=second,
                timezone=timezone,
                id='news_digest_job' # Unique ID for the job
            )
            logger.info(f"Job 'news_digest_job' added to scheduler.")
            logger.info(f"Schedule: {second} {minute} {hour} * * * (timezone: {timezone})")
        
        else:
            logger.error(f"Unknown scheduler mode: {mode}. Supported modes: 'interval', 'cron'")
            return
    except Exception as e:
        logger.error(f"Failed to add job to scheduler: {e}")
        return

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started successfully.")
    logger.info("Application is running. Press Ctrl+C to exit.")
    
    # Log current configuration status
    logger.info(f"Huatu collector enabled: {settings.huatu.enabled}")
    logger.info(f"Email configuration present: {settings.email is not None}")
    logger.info(f"Database enabled: {settings.database.enabled}")

    try:
        # Keep the main thread alive
        while True:
            await asyncio.sleep(60)  # Wake up every minute to log status
            logger.debug("Scheduler heartbeat - application is running")
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down.")


# --- Main Execution Block ---
# This allows the script to be run directly: `python -m app.main`
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="News Tracker Application")
    parser.add_argument(
        "--mode", 
        choices=["once", "schedule"], 
        default="once",
        help="Run mode: 'once' to run the pipeline immediately, 'schedule' to start the scheduler (default: once)"
    )
    
    args = parser.parse_args()

    try:
        if args.mode == "once":
            logger.info("Running pipeline once...")
            asyncio.run(run_pipeline())
        elif args.mode == "schedule":
            logger.info("Starting scheduler...")
            asyncio.run(run_scheduler())
    except Exception as e:
        logger.error(f"Application failed with error: {e}", exc_info=True)
        sys.exit(1)