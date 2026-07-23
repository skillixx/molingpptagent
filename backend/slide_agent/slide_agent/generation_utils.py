"""PPT 内容生成阶段的纯函数工具。"""

import json
from copy import deepcopy
from collections.abc import Mapping
from typing import Any


ALLOWED_SEARCH_ENGINES = ("KnowledgeBaseSearch", "SearchImage")


def initialize_generation_state(
    state: dict[str, Any],
    *,
    slides: list[dict[str, Any]],
    markdown: str,
    language: str,
) -> None:
    """为每次生成建立干净页码状态，避免复用会话时从上一份PPT中途继续。"""
    state["language"] = language
    state["outline_json"] = deepcopy(slides)
    state["slides_plan_num"] = len(slides)
    state["makrdown"] = markdown
    state["current_slide_index"] = 0
    state["retry_count_map"] = {}
    state["generated_slides_content"] = []
    state["last_written_raw"] = None
    state["last_slide_json"] = None
    state["is_valid_json"] = False
    state["last_validation_passed"] = None
    state["last_validation_feedback"] = None


def fallback_slide_for_failed_generation(
    outline: list[dict[str, Any]], index: int
) -> dict[str, Any]:
    """模型单页重试耗尽时返回原始结构，保证该页不会被静默丢弃。"""
    if index < 0 or index >= len(outline):
        raise IndexError("幻灯片页码超出大纲范围")
    return deepcopy(outline[index])


def normalize_search_engines(metadata: Mapping[str, Any] | None) -> list[str]:
    """仅保留用户明确选择的搜索能力，空选择表示禁用搜索。"""
    raw_value = metadata.get("search_engine") if metadata else None
    if not isinstance(raw_value, list):
        return []
    return [name for name in raw_value if name in ALLOWED_SEARCH_ENGINES]


def parse_last_json_object(text: str | None) -> dict[str, Any] | None:
    """从模型文本中提取最后一个完整 JSON 对象，兼容说明文字和重复输出。"""
    if not text:
        return None

    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(text):
        index = text.find("{", cursor)
        if index < 0:
            break
        try:
            parsed, consumed = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            cursor = index + 1
            continue
        if isinstance(parsed, dict):
            candidates.append(parsed)
        # 整个对象已成功解析后直接跳过其内部，避免把嵌套字段误认为整页。
        cursor = index + max(consumed, 1)
    return candidates[-1] if candidates else None
