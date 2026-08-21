"""红金年会颁奖模板的结构、版式选择与装饰保护回归测试。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_7.json"


def _renderer() -> PresentationTemplateRenderer:
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict) -> str | None:
    value = element.get("textType")
    return value if isinstance(value, str) else None


def _semantic_items(count: int) -> list[dict[str, str]]:
    return [
        {"title": f"要点 {index}", "text": f"第 {index} 项的完整说明。"}
        for index in range(1, count + 1)
    ]


def test_template_7_has_complete_production_layout_inventory() -> None:
    """生产版必须包含22页，并覆盖约定的五种页面类型。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slides = template["slides"]
    counts = {
        slide_type: sum(slide["type"] == slide_type for slide in slides)
        for slide_type in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_7"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(slides) == 22
    assert counts == {
        "cover": 2,
        "contents": 6,
        "transition": 4,
        "content": 8,
        "end": 2,
    }
    assert len(template["metadata"]["mvpSlideIds"]) == 12


def test_template_7_respects_required_typography_minimums() -> None:
    """封面、页面、内容标题和正文必须满足开发说明中的可读字号门禁。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    cover_titles = []
    page_titles = []
    item_titles = []
    bodies = []
    contents_labels = []
    for slide in template["slides"]:
        for element in slide["elements"]:
            content = str(element.get("content", ""))
            sizes = [float(value) for value in re.findall(r"font-size:\s*([\d.]+)px", content)]
            if not sizes:
                continue
            size = max(sizes)
            if slide["type"] == "cover" and element.get("textType") == "title":
                cover_titles.append(size)
            elif element.get("textType") == "title":
                page_titles.append(size)
            elif element.get("textType") == "itemTitle":
                item_titles.append(size)
            elif element.get("textType") in {"item", "content"}:
                bodies.append(size)
            if "盛典流程" in content:
                contents_labels.append(size)

    assert cover_titles and min(cover_titles) >= 50
    assert page_titles and min(page_titles) >= 35
    assert contents_labels and min(contents_labels) >= 35
    assert item_titles and min(item_titles) >= 24
    assert bodies and min(bodies) >= 16


def test_template_7_assets_are_external_and_resolvable() -> None:
    """模板JSON不得内嵌大图，所有项目资源地址必须可以在资源目录解析。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    image_sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    ]

    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert image_sources
    assert all(not source.startswith("data:") for source in image_sources)
    assert all(source.startswith("/api/data/") for source in image_sources)
    assert all((TEMPLATE_ROOT / source.rsplit("/", 1)[-1]).is_file() for source in image_sources)


@pytest.mark.parametrize("item_count", [2, 3, 4, 5, 6, 10])
def test_template_7_selects_exact_contents_capacity(item_count: int) -> None:
    """目录页必须按2、3、4、5、6、10项选择精确容量版式。"""
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {
                "type": "contents",
                "data": {"items": [f"流程 {index}" for index in range(1, item_count + 1)]},
            }
        ],
        task_id=f"template-7-contents-{item_count}",
        fallback_title="盛典流程",
    )
    slide = document["slides"][0]

    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == item_count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == item_count


@pytest.mark.parametrize("item_count", [1, 2, 3, 4])
def test_template_7_selects_exact_text_content_capacity(item_count: int) -> None:
    """无配图内容应选择纯文字版式，且保留准确的独立要点数量。"""
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {"type": "content", "data": {"title": "年度复盘", "items": _semantic_items(item_count)}}
        ],
        task_id=f"template-7-text-{item_count}",
        fallback_title="年度复盘",
    )
    slide = document["slides"][0]

    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == item_count
    assert not any(
        element.get("type") == "image" and element.get("imageType") == "content"
        for element in slide["elements"]
    )


def test_template_7_ordinary_four_item_pages_never_rotate_into_metrics_layout() -> None:
    """普通四项内容跨页生成时必须保持文本版式，不能按页序误入年度数字版式。"""
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {"type": "content", "data": {"title": f"普通四项 {index}", "items": _semantic_items(4)}}
            for index in range(4)
        ],
        task_id="template-7-four-item-consistency",
        fallback_title="普通四项",
    )

    assert {slide.get("layoutKind") for slide in document["slides"]} == {"text"}


def test_template_7_metrics_semantics_selects_metrics_layout() -> None:
    """显式数字项必须选择年度数字版式，而不是普通四项内容版式。"""
    items = [
        {"kind": "metric", "title": f"指标 {index}", "text": f"{index * 25}%"}
        for index in range(1, 5)
    ]
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[{"type": "content", "data": {"title": "年度数字", "items": items}}],
        task_id="template-7-metrics",
        fallback_title="年度数字",
    )

    assert document["slides"][0].get("layoutKind") == "metrics"


@pytest.mark.parametrize("image_count", [0, 1, 2, 3])
def test_template_7_fills_only_explicit_content_image_slots(image_count: int) -> None:
    """AI配图只允许进入内容槽，背景、帷幕、奖杯和人物相框必须保持原地址。"""
    sources = [f"https://example.invalid/content-{index}.jpg" for index in range(image_count)]
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "获奖展示", "items": _semantic_items(image_count)},
                "images": [{"src": source, "alt": f"配图 {index + 1}"} for index, source in enumerate(sources)],
            }
        ],
        task_id=f"template-7-images-{image_count}",
        fallback_title="获奖展示",
    )
    images = [element for element in document["slides"][0]["elements"] if element.get("type") == "image"]
    content_images = [element for element in images if element.get("imageType") == "content"]
    decorations = [element for element in images if element.get("imageType") == "decoration"]

    assert [element["src"] for element in content_images] == sources
    assert decorations
    assert all(element["src"].startswith("/api/data/template_7_asset_") for element in decorations)


def test_template_7_ignores_image_entries_without_a_source() -> None:
    """空图片地址不得占用内容图片槽，也不得覆盖模板装饰。"""
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "空图片", "items": _semantic_items(1)},
                "images": [{"src": "   "}, {"alt": "缺少地址"}],
            }
        ],
        task_id="template-7-empty-image",
        fallback_title="空图片",
    )

    assert not any(
        element.get("type") == "image" and element.get("imageType") == "content"
        for element in document["slides"][0]["elements"]
    )


def test_template_7_paginates_eight_items_without_reordering() -> None:
    """8项内容必须自动拆页，连接后的正文顺序与输入完全一致。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[{"type": "content", "data": {"title": "八项成果", "items": items}}],
        task_id="template-7-eight-items",
        fallback_title="八项成果",
    )
    rendered = "".join(
        str(element.get("content", ""))
        for slide in document["slides"]
        for element in slide["elements"]
    )

    assert len(document["slides"]) == 2
    positions = [rendered.index(item["text"]) for item in items]
    assert positions == sorted(positions)


def test_template_7_long_body_is_split_without_silent_truncation() -> None:
    """长正文拆分后必须逐字符保持原始顺序，不能靠截断获得成功。"""
    long_text = "荣耀来自每一次认真投入，也来自团队之间持续而坦诚的协作。" * 80
    document = _renderer().render(
        template_id="template_7",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "完整记录", "items": [{"title": "年度回顾", "text": long_text}]},
            }
        ],
        task_id="template-7-long-body",
        fallback_title="完整记录",
    )
    parts = []
    for rendered_slide in document["slides"]:
        for element in sorted(
            [candidate for candidate in rendered_slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        ):
            value = str(element.get("content", ""))
            parts.append(value.split(">", 2)[-1].split("<", 1)[0])

    assert len(document["slides"]) > 1
    assert "".join(parts) == long_text


def test_template_7_corrupted_json_is_rejected(tmp_path: Path) -> None:
    """模板JSON损坏时必须返回稳定错误，不能生成半成品文档。"""
    (tmp_path / "template_7.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(TemplateRenderError, match="模板数据损坏"):
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_7",
            semantic_slides=[],
            task_id="template-7-broken",
            fallback_title="损坏模板",
        )


def test_template_7_missing_content_slots_is_rejected(tmp_path: Path) -> None:
    """内容页缺少 item/content 槽时必须显式失败，不能静默丢失正文。"""
    template = {
        "width": 1000,
        "height": 562.5,
        "slides": [
            {
                "id": "content-without-slots",
                "type": "content",
                "elements": [
                    {
                        "id": "title",
                        "type": "text",
                        "textType": "title",
                        "left": 60,
                        "top": 40,
                        "width": 800,
                        "height": 80,
                        "content": '<p><span style="font-size: 40px">标题</span></p>',
                    }
                ],
            }
        ],
    }
    (tmp_path / "template_7.json").write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(TemplateRenderError, match="模板缺少内容槽位"):
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_7",
            semantic_slides=[
                {"type": "content", "data": {"title": "正文", "items": _semantic_items(1)}}
            ],
            task_id="template-7-missing-slot",
            fallback_title="正文",
        )


def test_template_7_missing_content_slots_rejects_plain_text_fallback(tmp_path: Path) -> None:
    """仅提供 data.text 时也不能在缺少正文槽位的模板中静默丢失内容。"""
    template = {
        "width": 1000,
        "height": 562.5,
        "slides": [
            {
                "id": "plain-text-without-slot",
                "type": "content",
                "elements": [
                    {
                        "id": "title",
                        "type": "text",
                        "textType": "title",
                        "left": 60,
                        "top": 40,
                        "width": 800,
                        "height": 80,
                        "content": '<p><span style="font-size: 40px">标题</span></p>',
                    }
                ],
            }
        ],
    }
    (tmp_path / "template_7.json").write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(TemplateRenderError, match="模板缺少内容槽位"):
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_7",
            semantic_slides=[
                {"type": "content", "data": {"title": "正文", "text": "必须保留的正文"}}
            ],
            task_id="template-7-missing-plain-text-slot",
            fallback_title="正文",
        )
