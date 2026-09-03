"""PPT 内容生成阶段的纯函数工具。"""

from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any
import unicodedata


ALLOWED_SEARCH_ENGINES = ("KnowledgeBaseSearch", "SearchImage")
MAX_MODEL_CALLS_PER_PAGE = 2


def consume_page_model_call_budget(state: dict[str, Any], page_index: int) -> bool:
    """登记单页真实模型调用；超过硬上限时返回 False，由调用方改走本地回退。"""
    counts = state.get("page_model_call_count_map")
    if not isinstance(counts, dict):
        counts = {}
        state["page_model_call_count_map"] = counts
    current = int(counts.get(page_index, 0)) + 1
    counts[page_index] = current
    return current <= MAX_MODEL_CALLS_PER_PAGE


def item_title_limit(item_count: int) -> int:
    """按单页项目密度返回展示标题上限，四项以上统一使用最严格容量。"""
    if item_count <= 1:
        return 20
    if item_count == 2:
        return 16
    if item_count == 3:
        return 12
    return 10


def _normalized_title_length(value: str) -> int:
    """按 NFC 归一化后的字符数校验标题，避免组合字符造成不稳定结果。"""
    return len(unicodedata.normalize("NFC", value).strip())


def _prepend_source_title(body: str, source_title: str) -> str:
    """把原始标题无损放到正文开头；重复归一化不会再次追加。"""
    normalized_body = body.strip()
    if normalized_body.startswith(source_title):
        return body
    separator = "" if source_title.endswith(("。", "！", "？", ".", "!", "?")) else "。"
    return f"{source_title}{separator}{body}" if body else source_title


def normalize_content_page_titles(
    page: dict[str, Any],
    *,
    source_page: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """确定性归一化内容项标题，同时保存原题、正文和项目顺序。"""
    normalized = deepcopy(page)
    if normalized.get("type") != "content":
        return normalized

    data = normalized.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return normalized
    items = data["items"]
    limit = item_title_limit(len(items))

    source_items: list[Any] = []
    if isinstance(source_page, dict):
        source_data = source_page.get("data")
        if isinstance(source_data, dict) and isinstance(source_data.get("items"), list):
            source_items = source_data["items"]

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        source_item = source_items[index] if index < len(source_items) else None
        source_title = ""
        if isinstance(source_item, dict):
            source_title = str(
                source_item.get("sourceTitle") or source_item.get("title") or ""
            ).strip()
        if not source_title:
            source_title = str(item.get("sourceTitle") or item.get("title") or "").strip()

        display_title = str(item.get("title") or "").strip()
        if not display_title or _normalized_title_length(display_title) > limit:
            # 不截取原句冒充压缩；模型未给出合格短标题时使用稳定且可追踪的展示名。
            display_title = f"核心要点{index + 1:02d}"
        item["title"] = display_title

        if source_title:
            item["sourceTitle"] = source_title
            body_key = "text" if isinstance(item.get("text"), str) else (
                "content" if isinstance(item.get("content"), str) else "text"
            )
            body = item.get(body_key) if isinstance(item.get(body_key), str) else ""
            if display_title != source_title:
                item[body_key] = _prepend_source_title(body, source_title)
    return normalized


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
    state["page_model_call_count_map"] = {}
    state["generated_slides_content"] = []
    state["last_written_raw"] = None
    state["last_slide_json"] = None
    state["is_valid_json"] = False
    state["last_validation_passed"] = None
    state["last_validation_feedback"] = None


def fallback_slide_for_failed_generation(
    outline: list[dict[str, Any]], index: int
) -> dict[str, Any]:
    """模型单页重试耗尽时返回安全结构，保证该页不会被静默丢弃。"""
    if index < 0 or index >= len(outline):
        raise IndexError("幻灯片页码超出大纲范围")
    source_page = outline[index]
    return normalize_content_page_titles(source_page, source_page=source_page)


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
