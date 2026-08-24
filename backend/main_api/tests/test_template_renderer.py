"""PPTist 模板渲染器的版式映射与文字适配测试。"""

from __future__ import annotations

import json
import math
import re
from html import unescape
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


def _plain_html(value: str) -> str:
    """提取测试所需纯文本，验证拆分前后没有丢字。"""
    return unescape(re.sub(r"<[^>]+>", "", value))


def _estimated_text_height(element: dict[str, object]) -> float:
    """按前端 10px 内边距和 1.5 行高独立估算正文实际高度。"""
    html_content = _content(element)
    sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", html_content)]
    font_size = min(sizes) if sizes else 16.0
    lines = [
        unescape(re.sub(r"<[^>]+>", "", part))
        for part in re.split(r"<br\s*/?>", html_content)
    ]
    usable_width = max(1.0, float(element.get("width", 0)) - 20)
    weighted_per_line = usable_width / font_size * 0.9
    wrapped_lines = sum(
        max(
            1,
            math.ceil(
                sum(1.0 if ord(char) > 255 else 0.56 for char in line)
                / weighted_per_line
            ),
        )
        for line in lines
    )
    return wrapped_lines * font_size * 1.5 + 20


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
        assert sizes and 12 <= max(sizes) <= 16


def test_template_1_splits_five_long_items_without_losing_their_order() -> None:
    """超过模板要点容量时必须拆页，并原样保留全部内容顺序。"""
    items = [
        {
            "title": f"产业要点 {index}",
            "text": (
                "全球大数据产业进入规模化增长阶段，企业通过数据采集、治理、分析和应用"
                f"形成业务闭环。第 {index} 项重点说明产业价值与实际落地路径。"
            ),
        }
        for index in range(1, 6)
    ]

    document = _renderer().render(
        template_id="template_1",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "大数据产业生态形成", "items": items},
            }
        ],
        task_id="task-template-1-overflow",
        fallback_title="大数据产业生态形成",
    )

    assert len(document["slides"]) == 2
    rendered_html = "".join(
        _content(element)
        for slide in document["slides"]
        for element in slide["elements"]
    )
    positions = [rendered_html.index(item["text"]) for item in items]
    assert positions == sorted(positions)


def test_template_1_long_items_stay_inside_text_boxes_and_slide_bounds() -> None:
    """拆页后的语义文字必须同时位于文本框容量和幻灯片边界内。"""
    items = [
        {
            "title": f"产业要点 {index}",
            "text": "大数据平台形成采集、治理、分析和应用闭环，并在多个业务场景持续释放价值。" * 3,
        }
        for index in range(1, 6)
    ]
    document = _renderer().render(
        template_id="template_1",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "大数据产业生态形成", "items": items},
            }
        ],
        task_id="task-template-1-bounds",
        fallback_title="大数据产业生态形成",
    )
    slide_height = document["viewport_size"] * document["viewport_ratio"]

    for slide in document["slides"]:
        for element in slide["elements"]:
            if _slot_type(element) is None:
                continue
            assert float(element.get("top", 0)) + float(element.get("height", 0)) <= slide_height + 1
            assert _estimated_text_height(element) <= float(element.get("height", 0)) + 1
            assert float(element.get("top", 0)) + float(element.get("height", 0)) <= slide_height + 1


def test_template_1_splits_one_oversized_item_without_dropping_text() -> None:
    """单条正文超过可读容量时也要拆页，且正文字符必须完整保留。"""
    long_text = "数据要素需要经过采集、治理、分析和应用形成完整闭环。" * 40
    document = _renderer().render(
        template_id="template_1",
        semantic_slides=[
            {
                "type": "content",
                "data": {
                    "title": "超长单项内容",
                    "items": [{"title": "数据闭环", "text": long_text}],
                },
            }
        ],
        task_id="task-single-item-overflow",
        fallback_title="超长单项内容",
    )

    assert len(document["slides"]) > 1
    rendered_parts = [
        _plain_html(_content(element))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (
                float(candidate.get("top", 0)),
                float(candidate.get("left", 0)),
            ),
        )
    ]
    assert "".join(rendered_parts) == long_text


@pytest.mark.parametrize("item_count", [1, 2, 3, 4])
def test_template_1_normal_item_counts_use_a_matching_multi_slot_layout(item_count: int) -> None:
    """正常内容数量继续使用能够完整容纳要点的模板版式。"""
    document = _renderer().render(
        template_id="template_1",
        semantic_slides=[
            {
                "type": "content",
                "data": {
                    "title": "正常内容",
                    "items": [
                        {"title": f"要点 {index}", "text": "简洁且适合演示的正文。"}
                        for index in range(item_count)
                    ],
                },
            }
        ],
        task_id=f"task-normal-{item_count}",
        fallback_title="正常内容",
    )

    item_slots = sum(
        _slot_type(element) == "item"
        for element in document["slides"][0]["elements"]
    )
    assert item_slots == item_count


def test_content_slot_without_font_size_receives_a_readable_size(tmp_path: Path) -> None:
    """模板未声明字号时，渲染结果仍必须包含明确且可读的字号。"""
    template = {
        "width": 1000,
        "height": 562.5,
        "slides": [
            {
                "id": "fontless-content",
                "type": "content",
                "elements": [
                    {
                        "id": "body",
                        "type": "text",
                        "textType": "content",
                        "left": 40,
                        "top": 100,
                        "width": 500,
                        "height": 160,
                        "content": '<p style=""></p>',
                    }
                ],
            }
        ],
    }
    (tmp_path / "template_1.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )
    renderer = PresentationTemplateRenderer(tmp_path)

    document = renderer.render(
        template_id="template_1",
        semantic_slides=[
            {
                "type": "content",
                "data": {
                    "title": "字号兜底",
                    "items": [
                        {
                            "title": "完整说明",
                            "text": "模板没有预设字号时必须写入默认字号。",
                        }
                    ],
                },
            }
        ],
        task_id="task-fontless-content",
        fallback_title="字号兜底",
    )

    body = next(
        element
        for element in document["slides"][0]["elements"]
        if _slot_type(element) == "content"
    )
    sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", _content(body))]
    assert sizes == [16.0]


def test_renderer_rejects_content_that_still_crosses_the_slide_boundary(tmp_path: Path) -> None:
    """没有可拆要点槽的模板也不能保存明显越过页面底部的正文。"""
    template = {
        "width": 1000,
        "height": 300,
        "slides": [
            {
                "id": "unsafe-content",
                "type": "content",
                "elements": [
                    {
                        "id": "body",
                        "type": "text",
                        "textType": "content",
                        "left": 40,
                        "top": 240,
                        "width": 180,
                        "height": 40,
                        "content": '<p style=""></p>',
                    }
                ],
            }
        ],
    }
    (tmp_path / "template_1.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(TemplateRenderError, match="文本框容量|页面边界") as captured:
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_1",
            semantic_slides=[
                {
                    "type": "content",
                    "data": {
                        "title": "边界门禁",
                        "items": [
                            {
                                "title": "超长正文",
                                "text": "没有要点槽时仍然必须拒绝越过页面底部的生成结果。" * 10,
                            }
                        ],
                    },
                }
            ],
            task_id="task-reject-overflow",
            fallback_title="边界门禁",
        )
    assert captured.value.code == "TEMPLATE_TEXT_OVERFLOW"


@pytest.mark.parametrize("template_id", ["../template_5", "template_999", "template_0"])
def test_invalid_or_missing_template_is_rejected(template_id: str) -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id=template_id,
            semantic_slides=_semantic_slides(),
            task_id="task-invalid",
            fallback_title="无效模板",
        )


def test_renderer_reports_missing_local_template_asset(tmp_path: Path) -> None:
    """模板JSON存在但引用资源缺失时必须返回独立安全错误码。"""
    template = {
        "width": 1000,
        "height": 562.5,
        "slides": [{
            "id": "cover",
            "type": "cover",
            "elements": [
                {
                    "id": "missing-image",
                    "type": "image",
                    "src": "/api/data/missing-template-asset.png",
                    "imageType": "decoration",
                    "left": 0,
                    "top": 0,
                    "width": 1000,
                    "height": 562.5,
                },
                {
                    "id": "title",
                    "type": "text",
                    "textType": "title",
                    "left": 100,
                    "top": 100,
                    "width": 800,
                    "height": 120,
                    "content": '<p><span style="font-size: 40px">标题</span></p>',
                },
            ],
        }],
    }
    (tmp_path / "template_1.json").write_text(
        json.dumps(template, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(TemplateRenderError) as captured:
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_1",
            semantic_slides=[{"type": "cover", "data": {"title": "资源检查"}}],
            task_id="task-missing-template-asset",
            fallback_title="资源检查",
        )

    assert captured.value.code == "TEMPLATE_RESOURCE_MISSING"
