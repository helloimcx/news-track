# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python 3.13+ application called "News Tracker" that collects articles from RSS feeds or web searches, processes them using LLMs, and sends email notifications. The application supports scheduled execution and data persistence in SQLite.

## Key Components

1. **Collectors** (`app/collectors/`) - Modules for collecting data from various sources:
   - RSS feeds
   - Huatu (specific Chinese exam website)
   - Web search (Google, DuckDuckGo, etc.)

2. **Processors** (`app/processors/`) - Modules for processing data:
   - LLM processor using OpenAI API or compatible services

3. **Notifiers** (`app/notifiers/`) - Modules for sending notifications:
   - Email notifier using SMTP

4. **Database** (`app/db/`) - SQLite persistence using SQLAlchemy ORM

5. **Models** (`app/models/`) - Pydantic data models for articles, digests, etc.

6. **Configuration** (`app/config.py`) - Centralized configuration using pydantic-settings

## Development Commands

### Setup & Dependencies
```bash
# Install dependencies using uv (recommended)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Running the Application
```bash
# Run pipeline once
python -m app.main --mode once

# Start scheduler
python -m app.main --mode schedule
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_rss_collector.py -v

# Run tests with coverage
python -m pytest --cov=app --cov-report=html
```

### Adding Dependencies
```bash
# Add new dependency
uv add <package-name>

# Upgrade dependencies
uv lock --upgrade
uv lock --upgrade-package <package-name>
```

## Architecture Overview

The application follows a modular architecture with separate components for collection, processing, and notification. The main flow is:

1. Collect articles from configured sources (RSS, web search, etc.)
2. Process articles using LLM to generate summaries
3. Store processed data in database (if enabled)
4. Package articles into a digest
5. Send digest via email
6. Schedule the pipeline to run periodically (if in scheduler mode)

Configuration is managed through environment variables and .env files, with pydantic providing validation and type safety.