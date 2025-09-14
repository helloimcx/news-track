#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查询数据库内容的脚本

使用方法：
    python -m scripts.query_db --type [articles|processed|digests] --limit 10
"""

import argparse
import sys
import os
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import init_db, get_session
from app.db.services import ArticleService, ProcessedArticleService, DigestService
from app.config import settings


def format_article(article):
    """格式化文章信息"""
    return f"""标题: {article.title}
来源: {article.source}
URL: {article.url}
发布时间: {article.published_at}
内容长度: {len(article.content) if article.content else 0} 字符
"""


def format_processed_article(processed_article):
    """格式化处理后的文章信息"""
    return f"""标题: {processed_article.original_article.title}
来源: {processed_article.original_article.source}
摘要: {processed_article.summary}
关键要点: {', '.join(processed_article.key_points)}
情感倾向: {processed_article.sentiment}
标签: {', '.join(processed_article.tags)}
"""


def format_digest(digest):
    """格式化摘要信息"""
    articles_info = f"包含 {len(digest.articles)} 篇文章"
    return f"""标题: {digest.title}
生成时间: {digest.generated_at}
{articles_info}
总体摘要: {digest.overall_summary}
"""


def main():
    parser = argparse.ArgumentParser(description="查询数据库内容")
    parser.add_argument(
        "--type",
        choices=["articles", "processed", "digests"],
        default="digests",
        help="要查询的内容类型: articles(原始文章), processed(处理后的文章), digests(摘要)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="返回结果的最大数量"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="数据库文件路径，默认使用配置中的路径"
    )
    
    args = parser.parse_args()
    
    # 初始化数据库
    db_path = args.db_path or settings.database.db_path
    init_db(db_path)
    
    with get_session() as session:
        if args.type == "articles":
            articles = ArticleService.get_recent_articles(args.limit, session)
            print(f"找到 {len(articles)} 篇原始文章:")
            for i, article in enumerate(articles, 1):
                print(f"\n--- 文章 {i} ---")
                print(format_article(article))
                
        elif args.type == "processed":
            processed_articles = ProcessedArticleService.get_recent_processed_articles(args.limit, session)
            print(f"找到 {len(processed_articles)} 篇处理后的文章:")
            for i, article in enumerate(processed_articles, 1):
                print(f"\n--- 处理后文章 {i} ---")
                print(format_processed_article(article))
                
        elif args.type == "digests":
            digests = DigestService.get_recent_digests(args.limit, session)
            print(f"找到 {len(digests)} 个摘要:")
            for i, digest in enumerate(digests, 1):
                print(f"\n--- 摘要 {i} ---")
                print(format_digest(digest))
                
                # 显示摘要中的文章
                if digest.articles:
                    print(f"\n包含的文章:")
                    for j, article in enumerate(digest.articles, 1):
                        print(f"\n文章 {j}: {article.original_article.title}")
                        print(f"摘要: {article.summary[:100]}...")


if __name__ == "__main__":
    main()