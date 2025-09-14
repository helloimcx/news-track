import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

# Create a logger for this module
logger = logging.getLogger("NewsTracker.Models")


class Article(BaseModel):
    """
    Represents a raw article fetched from a source.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    url: str
    content: str
    source: str
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessedArticle(BaseModel):
    """
    Represents an article that has been processed and summarized by an LLM.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_article: Article
    summary: str
    key_points: List[str] = []
    sentiment: Optional[float] = None  # Range from -1 (negative) to 1 (positive)
    tags: List[str] = []
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_llm_response(cls, original_article: Article, response_text: str) -> 'ProcessedArticle':
        """
        Creates a ProcessedArticle instance from the raw text response of an LLM.

        Args:
            original_article: The original Article that was processed.
            response_text: The raw text response from the LLM.

        Returns:
            A new ProcessedArticle instance populated with data from the response.
        """
        logger.debug(f"Attempting to parse LLM response for article '{original_article.title}'...")
        # Initialize default values
        data = {
            "original_article": original_article,
            "summary": "",
            "key_points": [],
            "sentiment": None,
            "tags": []
        }
        
        try:
            # Attempt to parse the response as JSON
            response_data = json.loads(response_text)
            logger.debug(f"Parsed JSON data for article '{original_article.title}': {response_data}")
            
            # Extract fields, providing defaults if keys are missing or None
            data["summary"] = response_data.get("summary", "")
            # Ensure key_points is a list
            raw_key_points = response_data.get("key_points", [])
            data["key_points"] = raw_key_points if isinstance(raw_key_points, list) else []
            
            # Ensure sentiment is a float or None
            raw_sentiment = response_data.get("sentiment")
            data["sentiment"] = float(raw_sentiment) if raw_sentiment is not None else None
            
            # Ensure tags is a list
            raw_tags = response_data.get("tags", [])
            data["tags"] = raw_tags if isinstance(raw_tags, list) else []
            
            logger.debug(f"Extracted data for article '{original_article.title}': summary='{data['summary']}', key_points={data['key_points']}")

        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            logger.error(f"JSONDecodeError for article '{original_article.title}': {e}")
            logger.error(f"Raw response that failed to parse: {response_text}")
            # Raise ValueError to match test expectations
            raise ValueError(f"Invalid JSON response: {e}") from e
            
        except (TypeError, ValueError) as e:
            # Handle errors from type conversion (e.g., float(sentiment))
            logger.error(f"TypeError/ValueError for article '{original_article.title}': {e}")
            logger.error(f"Raw response: {response_text}")
            # Data might be partially filled, but we keep defaults for failed conversions

        # Create and return the ProcessedArticle instance
        processed_article = cls(**data)
        logger.info(f"Created ProcessedArticle for '{original_article.title}' with summary: '{processed_article.summary[:50]}...'")
        return processed_article

class Digest(BaseModel):
    """
    Represents a digest of processed articles to be sent out.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    articles: List[ProcessedArticle]
    overall_summary: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)