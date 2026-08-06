"""PPTist 模板渲染器的版式映射与文字适配测试。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"


def _renderer() -> PresentationTemplateRenderer:
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict[str, object]) -> str | None:
    if element.get("type") == "text":
        value = element.get("textType")
        return value if isinstance(value, str) else None
    text = element.get("text")
    if element.get("type") == "shape" and isinstance(text, dict):
        value = text.get("type")
        return value if isinstance(value, str) else None
    return None


def _content(element: dict[str, object]) -> str:
    if isinstance(element.get("content"), str):
        return element["content"]
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("content"), str):
        return text["content"]
    return ""


def _semantic_slides() -> list[dict[str, object]]:
    return [
        {"type": "cover", "data": {"title": "人工智能毕业答辩", "text": "从问题到成果"}},
        {
            "type": "contents",
            "data": {"items": [{"title": "研究背景"}, {"title": "技术方案"}, {"title": "成果展示"}]},
        },
        {"type": "transition", "data": {"title": "研究背景", "text": "为什么要解决这个问题"}},
        {
            "type": "content",
            "data": {
                "title": "核心成果",
                "items": [
                    {"title": "准确率", "text": "模型在验证集上达到预期目标"},
                    {"title": "性能", "text": "推理时间满足实时使用要求"},
                    {"title": "落地", "text": "已完成业务场景验证"},
                ],
            },
        },
        {"type": "end", "data": {}},
    ]


def test_template_5_preserves_design_and_maps_semantic_slots() -> None:
    document = _renderer().render(
        template_id="template_5",
        semantic_slides=_semantic_slides(),
        task_id="task-template-5",
        fallback_title="人工智能毕业答辩",
    )

    assert document["viewport_size"] == 1280
    assert document["viewport_ratio"] == pytest.approx(0.5625)
    assert document["theme"]["themeColors"][0] == "#B42318"
    assert document["theme"]["backgroundColor"] == "#F7F4EF"
    assert [slide["type"] for slide in document["slides"]] == [
        "cover",
        "contents",
        "transition",
        "content",
        "end",
    ]

    # 每种页面都保留模板装饰元素，正文页不再退化成两个白底文本框。
    assert len(document["slides"][0]["elements"]) == 5
    assert len(document["slides"][1]["elements"]) == 13
    assert sum(
        _slot_type(element) == "item"
        for element in document["slides"][1]["elements"]
    ) == 3
    assert len(document["slides"][3]["elements"]) >= 16
    assert any(element.get("type") != "text" for element in document["slides"][3]["elements"])

    all_html = "".join(
        _content(element)
        for slide in document["slides"]
        for element in slide["elements"]
    )
    for expected in ("人工智能毕业答辩", "研究背景", "核心成果", "准确率", "业务场景验证"):
        assert expected in all_html

    ids = [
        element["id"]
        for slide in document["slides"]
        for element in slide["elements"]
    ]
    assert len(ids) == len(set(ids))
    assert len({slide["id"] for slide in document["slides"]}) == len(document["slides"])

    for slide in document["slides"]:
        for element in slide["elements"]:
            if _slot_type(element) is None:
                continue
            assert 0 <= float(element.get("left", 0)) < 1280
            assert 0 <= float(element.get("top", 0)) < 720


def test_long_text_reduces_font_size_without_dropping_template_style() -> None:
    long_text = "这是用于验证长文本自动缩放且不会溢出模板正文区域的详细说明。" * 12
    document = _renderer().render(
        template_id="template_5",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "超长内容适配", "items": [{"title": "完整说明", "text": long_text}]},
            }
        ],
        task_id="task-long-text",
        fallback_title="长文本测试",
    )

    content_element = next(
        element
        for element in document["slides"][0]["elements"]
        if _slot_type(element) in {"item", "content"} and long_text in _content(element)
    )
    sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", _content(content_element))]
    assert sizes
    assert min(sizes) >= 10
    assert max(sizes) < 23
    assert "font-family: 微软雅黑" in _content(content_element)


def test_body_font_uses_actual_slot_height_to_avoid_crossing_divider() -> None:
    body = "长文本需要依据模板正文框的真实高度自动缩放，避免内容越过下方分隔线。" * 4
    document = _renderer().render(
        template_id="template_5",
        semantic_slides=[
            {
                "type": "content",
                "data": {
                    "title": "高度约束",
                    "items": [
                        {"title": "第一项", "text": body},
                        {"title": "第二项", "text": body},
                        {"title": "第三项", "text": body},
                    ],
                },
            }
        ],
        task_id="task-height-fit",
        fallback_title="高度测试",
    )

    bodies = [
        element
        for element in document["slides"][0]["elements"]
        if _slot_type(element) == "item"
    ]
    assert len(bodies) == 3
    for element in bodies:
        sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", _content(element))]
        assert float(element["height"]) == 92
        assert sizes and 10 <= max(sizes) <= 14


@pytest.mark.parametrize("template_id", ["../template_5", "template_999", "template_0"])
def test_invalid_or_missing_template_is_rejected(template_id: str) -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id=template_id,
            semantic_slides=_semantic_slides(),
            task_id="task-invalid",
            fallback_title="无效模板",
        )
