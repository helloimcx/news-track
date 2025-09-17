#!/usr/bin/env python3
"""
Test script to debug Docker logging issues.
This script helps verify that logging works properly in the Docker environment.
"""
import logging
import sys
import time
from datetime import datetime

# Configure logging similar to main app
logger = logging.getLogger("TestLogger")
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Formatter
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(log_format)

# Add handler
logger.addHandler(console_handler)

def main():
    """Test logging functionality."""
    logger.info("=== Docker Logging Test Started ===")
    logger.info(f"Current time: {datetime.now()}")
    logger.info("Python version: " + sys.version)
    
    # Test different log levels
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    
    # Test continuous logging
    for i in range(5):
        logger.info(f"Test log message {i+1}/5")
        time.sleep(1)
    
    logger.info("=== Docker Logging Test Completed ===")
    print("Direct print statement - this should also appear in logs")
    
if __name__ == "__main__":
    main()