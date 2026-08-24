"""科技蓝扁平模板的结构、容量、图片保护与资源回归测试。"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_8.json"
REAL_OUTLINE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "template_8_real_outlines.json"


def _renderer() -> PresentationTemplateRenderer:
    """返回使用生产模板目录的真实渲染器。"""
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict) -> str | None:
    """兼容文本元素和带文字形状的PPTist槽位写法。"""
    value = element.get("textType")
    if isinstance(value, str):
        return value
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("type"), str):
        return text["type"]
    return None


def _plain_html(value: str) -> str:
    """提取测试所需纯文本，验证分页和长正文没有丢字。"""
    return unescape(re.sub(r"<[^>]+>", "", value))


def _semantic_items(count: int) -> list[dict[str, str]]:
    """生成稳定的普通内容项，避免测试误入特殊版式。"""
    return [
        {"title": f"要点 {index}", "text": f"第 {index} 项的完整说明。"}
        for index in range(1, count + 1)
    ]


def _exact_text(seed: str, length: int) -> str:
    """按字符数生成确定性边界文案，避免测试因人工计数错误失真。"""
    return (seed * (length // len(seed) + 1))[:length]


def _agent_contract_slides(topic: str, sections: list[str], item_titles: list[str]) -> list[dict]:
    """把脱敏真实大纲扩展为符合Agent提示词上限的完整语义页面。"""
    directory_items = [
        f"{number}、{_exact_text(section, 12)}"
        for number, section in zip("一二三", sections, strict=True)
    ]
    transition_text = "".join(
        _exact_text(seed, 23) + "。"
        for seed in ("本章说明核心变化", "随后回答落地问题", "最终形成行动依据")
    )
    body = _exact_text("围绕业务目标组织信息并明确执行责任与验证方式", 60)
    return [
        {"type": "cover", "data": {"title": topic, "text": "面向真实业务场景的结构化分析与行动建议"}},
        {"type": "contents", "data": {"items": directory_items}},
        {"type": "transition", "data": {"title": sections[0], "text": transition_text}},
        {
            "type": "content",
            "data": {
                "title": _exact_text(topic + "实践路径", 32),
                "items": [
                    {"title": _exact_text(title, 24), "text": body}
                    for title in item_titles
                ],
            },
        },
        {"type": "end", "data": {"title": "感谢观看", "text": "欢迎继续交流"}},
    ]


def test_template_8_has_complete_production_layout_inventory() -> None:
    """生产版必须为18页，并准确覆盖五种基础页面类型。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    counts = {
        slide_type: sum(slide["type"] == slide_type for slide in template["slides"])
        for slide_type in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_8"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(template["slides"]) == 18
    assert counts == {
        "cover": 2,
        "contents": 6,
        "transition": 2,
        "content": 6,
        "end": 2,
    }
    assert len(template["metadata"]["mvpSlideIds"]) == 12
    assert set(template["metadata"]["mvpSlideIds"]) <= {
        slide["id"] for slide in template["slides"]
    }


def test_template_8_respects_typography_minimums() -> None:
    """封面、页面、内容项和正文必须满足规划中的可读字号。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    cover_titles: list[float] = []
    page_titles: list[float] = []
    item_titles: list[float] = []
    bodies: list[float] = []
    contents_items: list[float] = []

    for slide in template["slides"]:
        for element in slide["elements"]:
            content = str(element.get("content", ""))
            sizes = [float(value) for value in re.findall(r"font-size:\s*([\d.]+)px", content)]
            if not sizes:
                continue
            size = max(sizes)
            slot_type = _slot_type(element)
            if slide["type"] == "cover" and slot_type == "title":
                cover_titles.append(size)
            elif slot_type == "title":
                page_titles.append(size)
            elif slot_type == "itemTitle":
                item_titles.append(size)
            elif slot_type in {"item", "content"}:
                bodies.append(size)
            if slide["type"] == "contents" and slot_type == "item":
                contents_items.append(size)

    assert cover_titles and min(cover_titles) >= 48
    assert page_titles and min(page_titles) >= 35
    assert item_titles and min(item_titles) >= 24
    assert bodies and min(bodies) >= 16
    assert contents_items and min(contents_items) >= 16


def test_template_8_assets_are_external_resolvable_and_all_referenced() -> None:
    """模板不得内嵌大图，所有发布素材必须存在且被真实页面引用。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    image_sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    ]
    referenced_files = {source.rsplit("/", 1)[-1] for source in image_sources}
    published_assets = {
        path.name
        for path in TEMPLATE_ROOT.glob("template_8_asset_*")
    }

    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert image_sources
    assert all(not source.startswith("data:") for source in image_sources)
    assert all(source.startswith("/api/data/") for source in image_sources)
    assert all((TEMPLATE_ROOT / source.rsplit("/", 1)[-1]).is_file() for source in image_sources)
    assert published_assets == referenced_files


def test_template_8_ids_are_unique_and_samples_are_clean() -> None:
    """页面和元素ID不得重复，生产模板不能残留参考稿示例文案。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [
        element["id"]
        for slide in template["slides"]
        for element in slide["elements"]
    ]
    serialized = json.dumps(template, ensure_ascii=False)

    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    for forbidden in ("XXX设计", "FEI ER SHE JI", "2019", "THANK YOU"):
        assert forbidden not in serialized


@pytest.mark.parametrize("item_count", [2, 3, 4, 5, 6, 10])
def test_template_8_selects_exact_contents_capacity(item_count: int) -> None:
    """目录页必须按输入数量选择精确槽位容量。"""
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[
            {
                "type": "contents",
                "data": {"items": [f"议题 {index}" for index in range(1, item_count + 1)]},
            }
        ],
        task_id=f"template-8-contents-{item_count}",
        fallback_title="目录",
    )
    slide = document["slides"][0]

    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == item_count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == item_count


@pytest.mark.parametrize("item_count", [1, 2, 3, 4])
def test_template_8_selects_exact_text_content_capacity(item_count: int) -> None:
    """无配图内容必须使用纯文字版式并保留准确项目数。"""
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[
            {"type": "content", "data": {"title": "核心观点", "items": _semantic_items(item_count)}}
        ],
        task_id=f"template-8-text-{item_count}",
        fallback_title="核心观点",
    )
    slide = document["slides"][0]

    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == item_count
    assert not any(
        element.get("type") == "image" and element.get("imageType") == "content"
        for element in slide["elements"]
    )


@pytest.mark.parametrize("image_count", [0, 1, 2])
def test_template_8_fills_only_explicit_content_image_slots(image_count: int) -> None:
    """AI图片只能进入内容槽，背景、网络和光效必须保持项目地址。"""
    item_count = max(1, image_count)
    sources = [f"https://example.invalid/content-{index}.jpg" for index in range(image_count)]
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "图文说明", "items": _semantic_items(item_count)},
                "images": [
                    {"src": source, "alt": f"内容图片 {index + 1}"}
                    for index, source in enumerate(sources)
                ],
            }
        ],
        task_id=f"template-8-images-{image_count}",
        fallback_title="图文说明",
    )
    images = [
        element
        for element in document["slides"][0]["elements"]
        if element.get("type") == "image"
    ]
    content_images = [element for element in images if element.get("imageType") == "content"]
    decorations = [element for element in images if element.get("imageType") == "decoration"]

    assert [element["src"] for element in content_images] == sources
    assert decorations
    assert all(element["src"].startswith("/api/data/template_8_asset_") for element in decorations)


def test_template_8_ignores_image_entries_without_a_source() -> None:
    """空图片地址不能占用内容槽，也不能覆盖模板装饰。"""
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "空图片", "items": _semantic_items(1)},
                "images": [{"src": "   "}, {"alt": "缺少地址"}],
            }
        ],
        task_id="template-8-empty-image",
        fallback_title="空图片",
    )

    assert not any(
        element.get("type") == "image" and element.get("imageType") == "content"
        for element in document["slides"][0]["elements"]
    )


def test_template_8_paginates_eight_items_without_reordering() -> None:
    """8项内容必须拆为两页，且项目顺序和文字完整保留。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-8-eight-items",
        fallback_title="八项内容",
    )
    rendered = "".join(
        str(element.get("content", ""))
        for slide in document["slides"]
        for element in slide["elements"]
    )

    assert len(document["slides"]) == 2
    positions = [rendered.index(item["text"]) for item in items]
    assert positions == sorted(positions)


def test_template_8_long_body_is_split_without_silent_truncation() -> None:
    """长正文拆分后必须逐字符保持原始顺序。"""
    long_text = "复杂信息需要先确定结论，再按层级组织证据和行动。" * 80
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "完整说明", "items": [{"title": "核心结论", "text": long_text}]},
            }
        ],
        task_id="template-8-long-body",
        fallback_title="完整说明",
    )
    parts: list[str] = []
    for rendered_slide in document["slides"]:
        for element in sorted(
            [candidate for candidate in rendered_slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        ):
            parts.append(_plain_html(str(element.get("content", ""))))

    assert len(document["slides"]) > 1
    assert "".join(parts) == long_text


def test_template_8_corrupted_json_is_rejected(tmp_path: Path) -> None:
    """模板JSON损坏时必须稳定失败，不能生成半成品。"""
    (tmp_path / "template_8.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(TemplateRenderError, match="模板数据损坏") as captured:
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_8",
            semantic_slides=[],
            task_id="template-8-broken",
            fallback_title="损坏模板",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_8_missing_file_uses_resource_error_code(tmp_path: Path) -> None:
    """模板文件不存在属于资源缺失，不得与JSON损坏或文字溢出混为一类。"""
    with pytest.raises(TemplateRenderError) as captured:
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_8",
            semantic_slides=[],
            task_id="template-8-missing-file",
            fallback_title="缺失模板",
        )
    assert captured.value.code == "TEMPLATE_RESOURCE_MISSING"


@pytest.mark.parametrize("item_count", [2, 3, 4, 5, 6, 10])
def test_template_8_accepts_agent_contract_directory_items(item_count: int) -> None:
    """每种目录版式都必须容纳14字和中文编号，不得在生产渲染阶段失败。"""
    items = [
        f"{number}、科技创新驱动业务增长路径"[:14]
        for number in "一二三四五六七八九十"[:item_count]
    ]
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{"type": "contents", "data": {"items": items}}],
        task_id=f"template-8-directory-contract-{item_count}",
        fallback_title="目录",
    )

    assert len(document["slides"]) == 1
    rendered = json.dumps(document, ensure_ascii=False)
    assert all(item in rendered for item in items)


def test_template_8_accepts_mixed_language_directory_items() -> None:
    """目录必须覆盖中文编号与AIGC等英文缩写混排的14字边界。"""
    items = [
        (f"{number}、AIGC驱动教学创新路径" + "升级")[:14]
        for number in "一二三四五六"
    ]
    assert all(len(item) == 14 for item in items)

    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{"type": "contents", "data": {"items": items}}],
        task_id="template-8-mixed-directory-contract",
        fallback_title="目录",
    )

    rendered = json.dumps(document, ensure_ascii=False)
    assert all(item in rendered for item in items)


def test_template_8_accepts_three_transition_sentences_at_agent_limit() -> None:
    """章节说明必须稳定容纳3句、每句24字且包含中文标点和英文缩写。"""
    sentences = [
        _exact_text("AIGC推动教学内容生成与审核协同", 23) + "。",
        _exact_text("本章回答技术如何进入真实课堂流程", 23) + "。",
        _exact_text("读者将获得可执行的质量治理框架", 23) + "。",
    ]
    text_value = "".join(sentences)

    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": "AIGC在教育领域的应用边界", "text": text_value},
        }],
        task_id="template-8-transition-contract",
        fallback_title="章节过渡",
    )

    assert text_value in json.dumps(document, ensure_ascii=False)


@pytest.mark.parametrize("title_length", [16, 24, 32, 40])
def test_template_8_accepts_long_page_titles(title_length: int) -> None:
    """页面标题最多40字时应使用可读的两行标题区，而不是终止整份作品。"""
    title = _exact_text("人工智能驱动组织转型实践路径", title_length)
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{
            "type": "content",
            "data": {"title": title, "items": _semantic_items(2)},
        }],
        task_id=f"template-8-page-title-{title_length}",
        fallback_title="页面标题",
    )

    assert title in json.dumps(document, ensure_ascii=False)


@pytest.mark.parametrize("item_count", [2, 3, 4])
@pytest.mark.parametrize("title_length", [11, 14, 20, 24, 30])
def test_template_8_accepts_real_item_title_lengths(item_count: int, title_length: int) -> None:
    """常见项目标题长度在2至4项内容版式中必须完整保留。"""
    titles = [
        _exact_text(f"第{index}项业务能力建设与落地路径", title_length)
        for index in range(1, item_count + 1)
    ]
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "真实项目标题容量验证",
                "items": [
                    {"title": title, "text": _exact_text("完整说明与执行建议", 45)}
                    for title in titles
                ],
            },
        }],
        task_id=f"template-8-item-title-{item_count}-{title_length}",
        fallback_title="内容标题",
    )

    rendered = json.dumps(document, ensure_ascii=False)
    assert all(title in rendered for title in titles)


@pytest.mark.parametrize("item_count,body_length", [(1, 90), (2, 90), (3, 60), (4, 45)])
def test_template_8_preserves_agent_contract_body_lengths(
    item_count: int, body_length: int
) -> None:
    """正文达到Agent允许上限时允许无损拆页，但字符和项目顺序必须完全一致。"""
    bodies = [
        _exact_text(f"第{index}项围绕业务目标组织证据并明确执行责任", body_length)
        for index in range(1, item_count + 1)
    ]
    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "正文容量契约",
                "items": [
                    {"title": f"行动建议{index}", "text": body}
                    for index, body in enumerate(bodies, start=1)
                ],
            },
        }],
        task_id=f"template-8-body-contract-{item_count}-{body_length}",
        fallback_title="正文容量契约",
    )

    rendered_parts = [
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        )
    ]
    assert "".join(rendered_parts) == "".join(bodies)


def test_template_8_renders_sanitized_real_outlines_without_losing_text() -> None:
    """三份脱敏生产大纲必须完整生成，所有输入字符均可在结果中追溯。"""
    fixtures = json.loads(REAL_OUTLINE_FIXTURE.read_text(encoding="utf-8"))
    for index, fixture in enumerate(fixtures):
        slides = _agent_contract_slides(
            fixture["topic"],
            fixture["sections"],
            fixture["item_titles"],
        )
        document = _renderer().render(
            template_id="template_8",
            semantic_slides=slides,
            task_id=f"template-8-real-outline-{index}",
            fallback_title=fixture["topic"],
        )
        rendered = json.dumps(document, ensure_ascii=False)
        assert fixture["topic"] in rendered
        assert all(item[:24] in rendered for item in fixture["item_titles"])


def test_template_8_end_page_tolerates_safe_model_overwrite_without_truncation() -> None:
    """模型意外补全结束页字段时，模板应保留文字而不是让整份作品在最后一页失败。"""
    title = _exact_text("感谢观看并欢迎继续交流", 80)
    text_value = _exact_text("围绕本次主题继续讨论实施路径与下一步协作安排", 100)

    document = _renderer().render(
        template_id="template_8",
        semantic_slides=[{"type": "end", "data": {"title": title, "text": text_value}}],
        task_id="template-8-end-safe-overwrite",
        fallback_title="结束页",
    )

    rendered = json.dumps(document, ensure_ascii=False)
    assert title in rendered
    assert text_value in rendered
