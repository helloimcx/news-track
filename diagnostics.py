#!/usr/bin/env python3
"""
Diagnostics script to check application configuration and dependencies.
"""
import logging
import sys
import os
from datetime import datetime

# Setup logging
logger = logging.getLogger("Diagnostics")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def check_environment():
    """Check environment variables and configuration."""
    logger.info("=== Environment Check ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info(f"PYTHONUNBUFFERED: {os.environ.get('PYTHONUNBUFFERED', 'Not set')}")
    
    # Check .env file
    env_file = "/app/.env"
    if os.path.exists(env_file):
        logger.info(f"Found .env file at {env_file}")
        with open(env_file, 'r') as f:
            lines = f.readlines()
            logger.info(f".env file has {len(lines)} lines")
    else:
        logger.warning(f".env file not found at {env_file}")

def check_dependencies():
    """Check if required dependencies are available."""
    logger.info("=== Dependencies Check ===")
    
    try:
        import aiohttp
        logger.info(f"✓ aiohttp: {aiohttp.__version__}")
    except ImportError as e:
        logger.error(f"✗ aiohttp: {e}")
    
    try:
        import pydantic
        logger.info(f"✓ pydantic: {pydantic.__version__}")
    except ImportError as e:
        logger.error(f"✗ pydantic: {e}")
    
    try:
        import bs4
        logger.info(f"✓ beautifulsoup4: {bs4.__version__}")
    except ImportError as e:
        logger.error(f"✗ beautifulsoup4: {e}")
    
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        logger.info("✓ APScheduler available")
    except ImportError as e:
        logger.error(f"✗ APScheduler: {e}")

def check_config():
    """Check application configuration."""
    logger.info("=== Configuration Check ===")
    
    try:
        from app.config import settings
        logger.info("✓ Configuration loaded successfully")
        logger.info(f"App name: {settings.app_name}")
        logger.info(f"Log level: {settings.log_level}")
        logger.info(f"Huatu enabled: {settings.huatu.enabled}")
        logger.info(f"Huatu topic: {settings.huatu.topic}")
        logger.info(f"Email configured: {settings.email is not None}")
        logger.info(f"Database enabled: {settings.database.enabled}")
        logger.info(f"Scheduler timezone: {settings.scheduler.timezone}")
        logger.info(f"Scheduler time: {settings.scheduler.hour:02d}:{settings.scheduler.minute:02d}:{settings.scheduler.second:02d}")
    except Exception as e:
        logger.error(f"✗ Configuration error: {e}", exc_info=True)

def main():
    """Run all diagnostics."""
    logger.info(f"=== News Tracker Diagnostics - {datetime.now()} ===")
    
    check_environment()
    check_dependencies()
    check_config()
    
    logger.info("=== Diagnostics Complete ===")

if __name__ == "__main__":
    main()