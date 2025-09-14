"""数据库存储服务模块"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Article, ProcessedArticle, Digest
from app.db.models import ArticleDB, ProcessedArticleDB, DigestDB, DigestArticleDB
from app.db.database import get_db

# 创建日志记录器
logger = logging.getLogger("NewsTracker.DBServices")

class ArticleService:
    """文章存储服务"""
    
    @staticmethod
    def save_article(article: Article, db: Session = None) -> ArticleDB:
        """保存文章到数据库
        
        Args:
            article: 要保存的文章
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            保存后的数据库文章对象
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            # 检查文章是否已存在
            existing = db.query(ArticleDB).filter(ArticleDB.id == article.id).first()
            if existing:
                logger.info(f"文章已存在，ID: {article.id}, 标题: {article.title}")
                return existing
                
            # 创建新文章
            db_article = ArticleDB.from_model(article)
            db.add(db_article)
            db.commit()
            db.refresh(db_article)
            logger.info(f"已保存文章，ID: {db_article.id}, 标题: {db_article.title}")
            return db_article
        except Exception as e:
            db.rollback()
            logger.error(f"保存文章时出错: {e}")
            raise
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_article_by_id(article_id: str, db: Session = None) -> Optional[Article]:
        """根据ID获取文章
        
        Args:
            article_id: 文章ID
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            找到的文章，如果不存在则返回None
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            db_article = db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
            if db_article:
                return db_article.to_model()
            return None
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_recent_articles(days: int = 7, limit: int = 100, db: Session = None) -> List[Article]:
        """获取最近的文章
        
        Args:
            days: 最近几天的文章
            limit: 最大返回数量
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            文章列表
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            db_articles = db.query(ArticleDB)\
                .filter(ArticleDB.created_at >= cutoff_date)\
                .order_by(desc(ArticleDB.created_at))\
                .limit(limit)\
                .all()
            
            return [article.to_model() for article in db_articles]
        finally:
            if close_db:
                db.close()

class ProcessedArticleService:
    """处理后的文章存储服务"""
    
    @staticmethod
    def save_processed_article(processed_article: ProcessedArticle, db: Session = None) -> ProcessedArticleDB:
        """保存处理后的文章到数据库
        
        Args:
            processed_article: 要保存的处理后文章
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            保存后的数据库处理后文章对象
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            # 检查处理后的文章是否已存在
            existing = db.query(ProcessedArticleDB).filter(ProcessedArticleDB.id == processed_article.id).first()
            if existing:
                logger.info(f"处理后的文章已存在，ID: {processed_article.id}")
                return existing
            
            # 确保原始文章已保存
            ArticleService.save_article(processed_article.original_article, db)
            
            # 创建处理后的文章
            db_processed_article = ProcessedArticleDB.from_model(processed_article)
            db.add(db_processed_article)
            db.commit()
            db.refresh(db_processed_article)
            logger.info(f"已保存处理后的文章，ID: {db_processed_article.id}")
            return db_processed_article
        except Exception as e:
            db.rollback()
            logger.error(f"保存处理后的文章时出错: {e}")
            raise
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_processed_article_by_id(article_id: str, db: Session = None) -> Optional[ProcessedArticle]:
        """根据ID获取处理后的文章
        
        Args:
            article_id: 文章ID
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            找到的处理后文章，如果不存在则返回None
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            db_article = db.query(ProcessedArticleDB).filter(ProcessedArticleDB.id == article_id).first()
            if db_article:
                return db_article.to_model()
            return None
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_recent_processed_articles(days: int = 7, limit: int = 100, db: Session = None) -> List[ProcessedArticle]:
        """获取最近的处理后文章
        
        Args:
            days: 最近几天的文章
            limit: 最大返回数量
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            处理后文章列表
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            db_articles = db.query(ProcessedArticleDB)\
                .filter(ProcessedArticleDB.processed_at >= cutoff_date)\
                .order_by(desc(ProcessedArticleDB.processed_at))\
                .limit(limit)\
                .all()
            
            return [article.to_model() for article in db_articles]
        finally:
            if close_db:
                db.close()

class DigestService:
    """摘要存储服务"""
    
    @staticmethod
    def save_digest(digest: Digest, db: Session = None) -> DigestDB:
        """保存摘要到数据库
        
        Args:
            digest: 要保存的摘要
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            保存后的数据库摘要对象
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            # 检查摘要是否已存在
            existing = db.query(DigestDB).filter(DigestDB.id == digest.id).first()
            if existing:
                logger.info(f"摘要已存在，ID: {digest.id}, 标题: {digest.title}")
                return existing
            
            # 确保所有处理后的文章已保存
            for article in digest.articles:
                ProcessedArticleService.save_processed_article(article, db)
            
            # 创建摘要
            db_digest = DigestDB.from_model(digest)
            db.add(db_digest)
            db.flush()  # 先刷新以获取ID
            
            # 创建摘要-文章关联
            for i, article in enumerate(digest.articles):
                db_link = DigestArticleDB(
                    digest_id=db_digest.id,
                    processed_article_id=article.id,
                    position=i
                )
                db.add(db_link)
            
            db.commit()
            db.refresh(db_digest)
            logger.info(f"已保存摘要，ID: {db_digest.id}, 标题: {db_digest.title}")
            return db_digest
        except Exception as e:
            db.rollback()
            logger.error(f"保存摘要时出错: {e}")
            raise
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_digest_by_id(digest_id: str, db: Session = None) -> Optional[Digest]:
        """根据ID获取摘要
        
        Args:
            digest_id: 摘要ID
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            找到的摘要，如果不存在则返回None
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            db_digest = db.query(DigestDB).filter(DigestDB.id == digest_id).first()
            if db_digest:
                return db_digest.to_model()
            return None
        finally:
            if close_db:
                db.close()
    
    @staticmethod
    def get_recent_digests(days: int = 30, limit: int = 50, db: Session = None) -> List[Digest]:
        """获取最近的摘要
        
        Args:
            days: 最近几天的摘要
            limit: 最大返回数量
            db: 数据库会话，如果为None则创建新会话
            
        Returns:
            摘要列表
        """
        close_db = False
        if db is None:
            from app.db.database import get_db_session
            db = get_db_session()
            close_db = True
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            db_digests = db.query(DigestDB)\
                .filter(DigestDB.generated_at >= cutoff_date)\
                .order_by(desc(DigestDB.generated_at))\
                .limit(limit)\
                .all()
            
            return [digest.to_model() for digest in db_digests]
        finally:
            if close_db:
                db.close()