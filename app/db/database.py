"""数据库连接和初始化模块"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# 创建日志记录器
logger = logging.getLogger("NewsTracker.Database")

# 创建Base类，所有模型类都将继承这个类
Base = declarative_base()

# 数据库引擎和会话工厂
engine = None
SessionLocal = None

def init_db(db_path=None):
    """初始化数据库连接和表结构
    
    Args:
        db_path: 数据库文件路径，如果为None则使用默认路径
    """
    global engine, SessionLocal
    
    # 确保数据目录存在
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # 如果未指定数据库路径，使用默认路径
    if db_path is None:
        db_path = os.path.join(data_dir, "news_tracker.db")
    
    # 创建数据库URL
    db_url = f"sqlite:///{db_path}"
    logger.info(f"初始化数据库连接: {db_url}")
    
    # 创建数据库引擎
    engine = create_engine(
        db_url, 
        connect_args={"check_same_thread": False}  # SQLite特有的设置，允许多线程访问
    )
    
    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 创建所有表
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表结构已创建")

def get_db_session() -> Session:
    """获取数据库会话
    
    Returns:
        SQLAlchemy会话对象
    """
    if SessionLocal is None:
        init_db()
    return SessionLocal()

@contextmanager
def get_db():
    """数据库会话上下文管理器
    
    用法:
    with get_db() as db:
        # 使用db进行数据库操作
    """
    db = get_db_session()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作出错: {e}")
        raise
    finally:
        db.close()

def close_db():
    """关闭数据库连接"""
    global engine, SessionLocal
    if engine is not None:
        engine.dispose()
        engine = None
        SessionLocal = None
        logger.info("数据库连接已关闭")