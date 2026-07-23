#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/20 10:02
# @File  : tools.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import asyncio
import logging
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
try:
    from .weixin_search import sogou_weixin_search, get_real_url, get_article_content
except ImportError:
    # 兼容从 simpleOutline 目录直接运行 main_api.py 的既有方式。
    from weixin_search import sogou_weixin_search, get_real_url, get_article_content
import time
from datetime import datetime
import random

logger = logging.getLogger(__name__)

def _search_one_document(keyword: str) -> list[dict[str, str]]:
    """同步抓取一篇精简资料；由异步入口在线程池中限时执行。"""
    results = sogou_weixin_search(keyword)
    if not results:
        return []
    result = results[0]
    sogou_link = result["link"]
    real_url = get_real_url(sogou_link)
    content = get_article_content(real_url, referer=sogou_link)
    return [{
        "title": result["title"],
        "publish_time": result["publish_time"],
        "real_url": real_url,
        # 限制模型上下文体积，避免长文章拖慢第二次模型调用。
        "content": content[:6000],
    }]


async def DocumentSearch(keyword: str, tool_context: ToolContext):
    """在 12 秒内返回精简搜索资料，超时则安全降级为模型自身知识。"""
    metadata = tool_context.state.get("metadata") or {}
    if metadata.get("outline_document_search_used"):
        logger.info("大纲文档检索次数已用完，跳过重复调用")
        return "已完成一次资料搜索，请停止调用工具并立即输出 Markdown 大纲"

    # 在外部请求前占用次数，即使超时也不会被模型反复触发。
    metadata["outline_document_search_used"] = True
    tool_context.state["metadata"] = metadata
    logger.info("大纲文档检索开始 agent=%s", tool_context.agent_name)
    start_time = time.monotonic()
    try:
        articles = await asyncio.wait_for(
            asyncio.to_thread(_search_one_document, keyword),
            timeout=12,
        )
    except TimeoutError:
        logger.warning("大纲文档检索超时，使用模型知识继续")
        return "搜索超时，请直接使用已有知识生成大纲"

    if not articles:
        logger.info("大纲文档检索无结果，使用模型知识继续")
        return "没有搜索结果，请直接使用已有知识生成大纲"
    logger.info("大纲文档检索完成 count=%s elapsed=%.2f", len(articles), time.monotonic() - start_time)
    # Session 只保存来源标识，不保存整篇文章，避免状态膨胀和日志意外泄露。
    metadata["tool_document_ids"] = [
        {"title": article["title"], "real_url": article["real_url"]}
        for article in articles
    ]
    tool_context.state["metadata"] = metadata
    return articles

if __name__ == '__main__':
    result = DocumentSearch(keyword="电动汽车")
    print(result)
