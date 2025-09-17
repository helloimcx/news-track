# Article Deduplication Feature

## Overview

The article deduplication feature automatically detects and filters out duplicate articles by comparing against existing database records. This prevents redundant processing and email notifications for the same content.

## Features

### 1. Database-Driven Deduplication

- **Direct Database Comparison**: Queries the database directly to check for existing articles
- **URL-based Deduplication**: Detects articles with identical or similar URLs
  - Normalizes URLs by removing tracking parameters (utm_source, utm_medium, etc.)
  - Checks both exact and normalized URL matches
  
- **Content-based Deduplication**: Detects articles with identical or similar content
  - Uses content hashing for exact duplicate detection
  - Uses content similarity analysis for near-duplicate detection
  - Normalizes content by removing extra whitespace and case differences

### 2. Smart URL Normalization

Automatically removes common tracking parameters while preserving important query parameters:
- Removes: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `gclid`, `ref`, `source`, `from`, `_t`, `share`
- Preserves: Important functional parameters like `id`, `page`, etc.

### 3. Efficient Database Integration

- No in-memory caching required - queries database directly
- Leverages existing database services for article lookup
- Configurable lookback period for content similarity checks
- Graceful fallback when database is disabled

## Configuration

Add the following settings to your `.env` file:

```bash
# Deduplication Settings
DEDUPLICATION__ENABLED=true
DEDUPLICATION__URL_SIMILARITY_THRESHOLD=0.95
DEDUPLICATION__CONTENT_SIMILARITY_THRESHOLD=0.85
DEDUPLICATION__LOAD_EXISTING_DAYS=7
```

### Configuration Options

- `enabled`: Enable/disable deduplication (default: true)
- `url_similarity_threshold`: Similarity threshold for URL matching (0.0-1.0, default: 0.95)
- `content_similarity_threshold`: Similarity threshold for content matching (0.0-1.0, default: 0.85)
- `load_existing_days`: Days to look back for existing articles in content comparison (default: 7)

## Usage

The deduplication feature is automatically integrated into the main application workflow:

1. **Initialization**: No pre-loading required - queries database on-demand
2. **Collection**: Applies deduplication after each collector fetches articles
3. **Database Queries**: Checks existing articles directly against database records
4. **Processing**: Only unique articles are processed by the LLM
5. **Notification**: Only unique articles are included in email digests

## Implementation Details

### Core Components

- `ArticleDeduplicator`: Main deduplication service class
- `get_deduplicator()`: Global deduplicator instance factory
- Database integration via `ArticleService.check_article_exists_by_url()` and `ArticleService.get_recent_articles()`
- Direct database queries eliminate need for in-memory caching

### Integration Points

The deduplication is applied in the main pipeline (`app/main.py`) after article collection:

```python
# Apply deduplication
if articles and settings.deduplication.enabled:
    unique_articles = deduplicator.deduplicate_articles(articles)
    logger.info(f"After deduplication: {len(unique_articles)} unique articles")
    articles = unique_articles
```

### Performance Considerations

- Direct database queries for real-time duplicate detection
- No memory overhead from maintaining article caches
- Efficient URL normalization and content hashing
- Configurable similarity thresholds allow fine-tuning for different use cases
- Graceful degradation when database is unavailable

## Testing

Comprehensive test coverage includes:

- URL normalization tests
- Content hashing and similarity tests
- Duplicate detection accuracy tests
- Integration tests with database services

Run tests with:
```bash
python -m pytest tests/test_deduplication.py -v
```

## Benefits

1. **Reduces Noise**: Eliminates duplicate content from email notifications
2. **Saves Resources**: Prevents redundant LLM processing of identical content
3. **Improves User Experience**: Users receive only unique, valuable content
4. **Database Efficiency**: Prevents storage of duplicate articles
5. **Cost Optimization**: Reduces LLM API calls for duplicate processing

## Monitoring

The deduplication process provides detailed logging:

```
INFO - Starting deduplication of 15 articles...
INFO - Skipping duplicate article: 广东公务员考试公告... - Exact URL match: https://example.com/article1.html
INFO - Deduplication complete: 12 unique articles, 3 duplicates removed
```

## Future Enhancements

Potential improvements for future versions:

1. **Advanced Content Analysis**: Use semantic similarity for better duplicate detection
2. **Title-based Deduplication**: Add title similarity analysis
3. **Source-specific Rules**: Different thresholds for different news sources
4. **Machine Learning**: Train models to detect duplicates more accurately
5. **Performance Optimization**: Implement more efficient similarity algorithms for large datasets