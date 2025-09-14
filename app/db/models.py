"""数据库模型定义"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# 创建Base类
Base = declarative_base()

class ArticleDB(Base):
    """文章数据库模型"""
    __tablename__ = "articles"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系：一篇原始文章可以有一个处理后的文章
    processed_article = relationship("ProcessedArticleDB", back_populates="original_article", uselist=False)
    
    @classmethod
    def from_model(cls, article):
        """从Pydantic模型创建数据库模型实例"""
        return cls(
            id=article.id,
            title=article.title,
            url=article.url,
            content=article.content,
            source=article.source,
            published_at=article.published_at,
            created_at=article.created_at
        )
    
    def to_model(self):
        """转换为Pydantic模型"""
        from app.models import Article
        return Article(
            id=self.id,
            title=self.title,
            url=self.url,
            content=self.content,
            source=self.source,
            published_at=self.published_at,
            created_at=self.created_at
        )

class ProcessedArticleDB(Base):
    """处理后的文章数据库模型"""
    __tablename__ = "processed_articles"
    
    id = Column(String(36), primary_key=True)
    original_article_id = Column(String(36), ForeignKey("articles.id"), nullable=False)
    summary = Column(Text, nullable=False)
    key_points = Column(Text, nullable=False)  # 存储为JSON字符串
    sentiment = Column(Float, nullable=True)
    tags = Column(Text, nullable=False)  # 存储为JSON字符串
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系：处理后的文章关联到原始文章
    original_article = relationship("ArticleDB", back_populates="processed_article")
    # 关系：处理后的文章可以属于多个摘要
    digests = relationship("DigestArticleDB", back_populates="processed_article")
    
    @classmethod
    def from_model(cls, processed_article):
        """从Pydantic模型创建数据库模型实例"""
        return cls(
            id=processed_article.id,
            original_article_id=processed_article.original_article.id,
            summary=processed_article.summary,
            key_points=json.dumps(processed_article.key_points),
            sentiment=processed_article.sentiment,
            tags=json.dumps(processed_article.tags),
            processed_at=processed_article.processed_at
        )
    
    def to_model(self):
        """转换为Pydantic模型"""
        from app.models import ProcessedArticle
        return ProcessedArticle(
            id=self.id,
            original_article=self.original_article.to_model(),
            summary=self.summary,
            key_points=json.loads(self.key_points),
            sentiment=self.sentiment,
            tags=json.loads(self.tags),
            processed_at=self.processed_at
        )

class DigestDB(Base):
    """摘要数据库模型"""
    __tablename__ = "digests"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    overall_summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系：摘要包含多篇处理后的文章
    articles = relationship("DigestArticleDB", back_populates="digest")
    
    @classmethod
    def from_model(cls, digest):
        """从Pydantic模型创建数据库模型实例"""
        return cls(
            id=digest.id,
            title=digest.title,
            overall_summary=digest.overall_summary,
            generated_at=digest.generated_at
        )
    
    def to_model(self):
        """转换为Pydantic模型"""
        from app.models import Digest, ProcessedArticle
        
        # 获取所有关联的处理后文章
        processed_articles = [link.processed_article.to_model() for link in self.articles]
        
        return Digest(
            id=self.id,
            title=self.title,
            articles=processed_articles,
            overall_summary=self.overall_summary,
            generated_at=self.generated_at
        )

class DigestArticleDB(Base):
    """摘要-文章关联表，用于多对多关系"""
    __tablename__ = "digest_articles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    digest_id = Column(String(36), ForeignKey("digests.id"), nullable=False)
    processed_article_id = Column(String(36), ForeignKey("processed_articles.id"), nullable=False)
    position = Column(Integer, nullable=False)  # 文章在摘要中的位置
    
    # 关系
    digest = relationship("DigestDB", back_populates="articles")
    processed_article = relationship("ProcessedArticleDB", back_populates="digests")