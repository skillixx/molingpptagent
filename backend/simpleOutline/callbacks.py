"""大纲 Agent 的安全回调日志。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any


logger = logging.getLogger(__name__)


def before_model_callback(callback_context: Any, llm_request: Any) -> None:
    """仅记录结构化指标，不输出用户正文、模型请求或凭据。"""
    logger.debug(
        "大纲模型调用开始 agent=%s history_count=%s has_metadata=%s",
        getattr(callback_context, "agent_name", "unknown"),
        len(getattr(llm_request, "contents", ()) or ()),
        bool(getattr(callback_context, "state", {}).get("metadata")),
    )
    return None


def after_model_callback(callback_context: Any, llm_response: Any) -> None:
    """模型回调只记录分片数量，避免 Windows 控制台编码导致生成断流。"""
    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", ()) or ()
    logger.debug(
        "大纲模型调用完成 agent=%s part_count=%s",
        getattr(callback_context, "agent_name", "unknown"),
        len(parts),
    )
    return None


def after_tool_callback(
    tool: Any,
    args: Mapping[str, Any],
    tool_context: Any,
    tool_response: Any,
) -> None:
    """工具结果可能含任意 Unicode；日志中只保留类型与数量。"""
    is_collection = isinstance(tool_response, (Mapping, Sequence)) and not isinstance(
        tool_response, (str, bytes, bytearray)
    )
    item_count = len(tool_response) if is_collection else None
    logger.info(
        "大纲工具调用完成 tool=%s response_type=%s item_count=%s",
        getattr(tool, "name", "unknown"),
        type(tool_response).__name__,
        item_count,
    )
    return None
