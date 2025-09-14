# 内容和任务持久化模块

本模块负责将收集到的信息和总结后的报告保存到数据库中，使用SQLite作为存储引擎。

## 模块结构

- `database.py`: 数据库连接和初始化模块
- `models.py`: 数据库模型定义
- `services.py`: 数据访问服务

## 配置说明

在应用配置中添加了数据库相关设置：

```python
class DatabaseConfig(BaseModel):
    """数据库配置"""
    # 数据库文件路径，如果为None则使用默认路径（data/news_tracker.db）
    db_path: str | None = None
    # 是否启用持久化存储
    enabled: bool = True
```

可以通过环境变量或.env文件配置：

```
DATABASE__DB_PATH=/path/to/your/database.db
DATABASE__ENABLED=true
```

## 使用方法

### 初始化数据库

```python
from app.db.database import init_db

# 使用默认路径
init_db()

# 或指定数据库路径
init_db("/path/to/your/database.db")
```

### 保存文章

```python
from app.db.services import ArticleService
from app.models import Article

# 创建文章对象
article = Article(
    title="文章标题",
    url="https://example.com/article",
    content="文章内容",
    source="文章来源",
    published_at=datetime.now()
)

# 保存文章
ArticleService.save_article(article)
```

### 保存处理后的文章

```python
from app.db.services import ProcessedArticleService
from app.models import ProcessedArticle

# 创建处理后的文章对象
processed_article = ProcessedArticle(
    original_article=article,
    summary="文章摘要",
    key_points=["要点1", "要点2"],
    sentiment="positive",
    tags=["标签1", "标签2"]
)

# 保存处理后的文章
ProcessedArticleService.save_processed_article(processed_article)
```

### 保存摘要

```python
from app.db.services import DigestService
from app.models import Digest

# 创建摘要对象
digest = Digest(
    title="摘要标题",
    articles=[processed_article1, processed_article2],
    overall_summary="总体摘要"
)

# 保存摘要
DigestService.save_digest(digest)
```

### 查询数据

```python
from app.db.services import ArticleService, ProcessedArticleService, DigestService
from app.db.database import get_session

# 使用上下文管理器获取会话
with get_session() as session:
    # 查询最近的5篇文章
    articles = ArticleService.get_recent_articles(5, session)
    
    # 查询特定来源的文章
    articles = ArticleService.get_articles_by_source("某来源", session)
    
    # 查询最近处理的文章
    processed_articles = ProcessedArticleService.get_recent_processed_articles(5, session)
    
    # 查询最近的摘要
    digests = DigestService.get_recent_digests(5, session)
```

## 测试

运行测试用例：

```bash
python -m unittest tests.test_db
```