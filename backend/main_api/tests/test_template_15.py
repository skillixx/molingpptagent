"""星脉科技产品发布模板的库存、素材、选版、分页和图片协议回归。"""

from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_15.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_star_pulse_launch_template.mjs"

PRODUCTION_IDS = {
    "cover-minimal", "cover-hero",
    "contents-3", "contents-4", "contents-5", "contents-6",
    "transition-horizon", "transition-spectrum", "transition-particle", "transition-stage",
    "content-text-1", "content-text-2", "content-text-3", "content-text-4", "content-text-5", "content-text-6",
    "content-hero-left", "content-hero-right", "content-image-1-dense", "content-dual-image-2",
    "content-metrics-3", "content-metrics-4", "content-metrics-5",
    "content-compare-2", "content-compare-4",
    "content-gallery-3", "content-gallery-4", "content-gallery-5", "content-gallery-6",
    "content-timeline-3", "content-timeline-4", "content-timeline-5",
    "content-process-3", "content-process-4", "content-process-5",
    "content-positioning-3", "content-positioning-4",
    "end-minimal", "end-action",
}

MVP_IDS = {
    "cover-minimal", "cover-hero",
    "contents-3", "contents-4", "contents-5", "contents-6",
    "transition-horizon", "transition-spectrum",
    "content-text-1", "content-text-2", "content-text-3", "content-text-4", "content-text-5", "content-text-6",
    "content-hero-left", "content-metrics-3", "content-metrics-4", "content-compare-2", "content-gallery-3",
    "end-minimal",
}


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _renderer() -> PresentationTemplateRenderer:
    """每个案例使用新 renderer，避免模板缓存掩盖磁盘变化。"""
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict) -> str | None:
    value = element.get("textType")
    if isinstance(value, str):
        return value
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("type"), str):
        return text["type"]
    return None


def _plain_text(element: dict) -> str:
    value = element.get("content")
    if not isinstance(value, str):
        text = element.get("text")
        value = text.get("content") if isinstance(text, dict) else ""
    return unescape(re.sub(r"<[^>]+>", "", value or ""))


def _items(count: int, *, kind: str | None = None, body: str | None = None) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index in range(1, count + 1):
        item = {"title": f"要点 {index}", "text": body or f"第 {index} 项完整说明。"}
        if kind:
            item["kind"] = kind
        values.append(item)
    return values


def _images(count: int) -> list[dict[str, object]]:
    return [
        {"src": f"https://example.invalid/product-{index}.jpg", "width": 1600, "height": 900}
        for index in range(1, count + 1)
    ]


def _render_content(
    count: int,
    *,
    image_count: int = 0,
    layout_kind: str | None = None,
    variant: str | None = None,
    kind: str | None = None,
) -> dict:
    data: dict[str, object] = {"title": "产品价值形成清晰证据", "items": _items(count, kind=kind)}
    if layout_kind:
        data["layoutKind"] = layout_kind
    if variant:
        data["variant"] = variant
    semantic: dict[str, object] = {"type": "content", "data": data}
    if image_count:
        semantic["images"] = _images(image_count)
    return _renderer().render(
        template_id="template_15",
        semantic_slides=[semantic],
        task_id=f"template-15-{count}-{image_count}-{layout_kind}-{variant}-{kind}",
        fallback_title="产品价值",
    )


def test_template_15_inventory_matches_declared_stage() -> None:
    """MVP 与生产阶段都必须精确匹配规格声明的稳定 ID。"""
    template = _template()
    stage = template["metadata"]["buildStage"]
    expected_ids = MVP_IDS if stage == "mvp" else PRODUCTION_IDS
    expected_counts = (
        {"cover": 2, "contents": 4, "transition": 2, "content": 11, "end": 1}
        if stage == "mvp"
        else {"cover": 2, "contents": 4, "transition": 4, "content": 27, "end": 2}
    )
    assert template["id"] == "template_15"
    assert template["title"] == "星脉科技产品发布"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert {slide["id"] for slide in template["slides"]} == expected_ids
    assert {kind: sum(slide["type"] == kind for slide in template["slides"]) for kind in expected_counts} == expected_counts
    assert len(template["metadata"]["mvpSlideIds"]) == 20


def test_template_15_production_builder_matches_catalog(tmp_path: Path) -> None:
    """生产构建器必须稳定输出 39 个唯一版式。"""
    output = tmp_path / "template_15.json"
    result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", "production", str(output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    template = json.loads(output.read_text(encoding="utf-8"))
    assert len(template["slides"]) == 39
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS


def test_template_15_builder_requires_output_path() -> None:
    result = subprocess.run(
        ["node", str(BUILDER_PATH)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    assert "build_star_pulse_launch_template.mjs" in result.stderr


def test_template_15_assets_are_external_and_valid() -> None:
    """7 项发布素材与列表封面必须满足规格属性。"""
    expected = {
        "template_15_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 380_000),
        "template_15_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 340_000),
        "template_15_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 340_000),
        "template_15_asset_spectrum_footer_v1.png": ((1600, 520), "RGBA", 950_000),
        "template_15_asset_horizon_glow_v1.png": ((1600, 700), "RGBA", 850_000),
        "template_15_asset_particle_field_v1.png": ((1600, 900), "RGBA", 900_000),
        "template_15_asset_product_stage_v1.png": ((1200, 700), "RGBA", 800_000),
    }
    assert {path.name for path in TEMPLATE_ROOT.glob("template_15_asset_*")} == set(expected)
    for name, (size, mode, max_bytes) in expected.items():
        path = TEMPLATE_ROOT / name
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                alpha_min, alpha_max = image.getchannel("A").getextrema()
                assert alpha_min < 255 and alpha_max > 0
        assert path.stat().st_size <= max_bytes
    with Image.open(TEMPLATE_ROOT / "template_15.jpg") as cover:
        assert cover.size == (960, 540)
        assert cover.mode == "RGB"


def test_template_15_ids_fonts_and_paths_are_clean() -> None:
    template = _template()
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)
    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    assert "template_14_asset_" not in serialized
    assert ".codex-tmp" not in serialized and "file://" not in serialized
    assert not any(token in serialized for token in ("Lorem ipsum", "点击添加", "XXX", "Electronic", "Note x"))
    for slide in template["slides"]:
        for element in slide["elements"]:
            if _slot_type(element) in {"title", "content", "item", "itemTitle"}:
                assert element.get("minimumFontSize", 0) >= (36 if _slot_type(element) == "title" else 16)


@pytest.mark.parametrize("count", [3, 4, 5, 6])
def test_template_15_selects_exact_contents_capacity(count: int) -> None:
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "contents", "data": {"items": [f"章节 {index}" for index in range(count)]}}],
        task_id=f"template-15-contents-{count}",
        fallback_title="目录",
    )
    assert len(document["slides"]) == 1
    assert sum(_slot_type(element) == "item" for element in document["slides"][0]["elements"]) == count


@pytest.mark.parametrize(("count", "expected"), [(7, [4, 3]), (11, [6, 5])])
def test_template_15_balances_overflowing_contents(count: int, expected: list[int]) -> None:
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "contents", "data": {"items": [f"章节 {index}" for index in range(count)]}}],
        task_id=f"template-15-contents-overflow-{count}",
        fallback_title="目录",
    )
    assert [sum(_slot_type(element) == "item" for element in slide["elements"]) for slide in document["slides"]] == expected


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_template_15_selects_exact_text_capacity(count: int) -> None:
    slide = _render_content(count)["slides"][0]
    assert slide["templateSlideId"] == f"content-text-{count}"
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count


def test_template_15_paginates_seven_text_items_as_six_plus_one() -> None:
    document = _render_content(7)
    assert [sum(_slot_type(element) == "item" for element in slide["elements"]) for slide in document["slides"]] == [6, 1]


def test_template_15_infers_metrics_only_when_all_items_are_metrics() -> None:
    metrics = _render_content(3, kind="metric")["slides"][0]
    assert metrics["layoutKind"] == "metrics"
    data = {"title": "混合内容", "items": _items(3)}
    data["items"][0]["kind"] = "metric"
    mixed = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "content", "data": data}],
        task_id="template-15-mixed-metrics",
        fallback_title="混合内容",
    )["slides"][0]
    assert mixed.get("layoutKind") != "metrics"
    assert mixed["templateSlideId"] == "content-text-3"


def test_template_15_rejects_invalid_explicit_specialty_inputs() -> None:
    with pytest.raises(TemplateRenderError):
        _render_content(2, layout_kind="focus")
    with pytest.raises(TemplateRenderError):
        _render_content(2, layout_kind="hero")
    with pytest.raises(TemplateRenderError):
        _render_content(6, layout_kind="metrics", kind="metric")


def test_template_15_mvp_hero_and_gallery_are_reachable() -> None:
    hero = _render_content(2, image_count=1)["slides"][0]
    assert hero["templateSlideId"] == "content-hero-left"
    assert sum(element.get("imageType") == "content" for element in hero["elements"]) == 1
    gallery = _render_content(3, image_count=3)["slides"][0]
    assert gallery["templateSlideId"] == "content-gallery-3"


def test_template_15_rejects_three_images_with_four_items() -> None:
    with pytest.raises(TemplateRenderError):
        _render_content(4, image_count=3)


def test_template_15_production_image_matrix_and_variants() -> None:
    if _template()["metadata"]["buildStage"] != "production":
        pytest.skip("生产图片矩阵在 MVP 门禁后执行")
    assert _render_content(2, image_count=1, variant="right")["slides"][0]["templateSlideId"] == "content-hero-right"
    assert _render_content(4, image_count=1)["slides"][0]["templateSlideId"] == "content-image-1-dense"
    assert _render_content(6, image_count=2)["slides"][0]["templateSlideId"] == "content-dual-image-2"
    seven = _render_content(7, image_count=7)
    assert [sum(element.get("imageType") == "content" for element in slide["elements"]) for slide in seven["slides"]] == [6, 1]


def test_template_15_content_image_crop_and_decoration_protection() -> None:
    slide = _render_content(2, image_count=1)["slides"][0]
    content = [element for element in slide["elements"] if element.get("imageType") == "content"]
    decorations = [element for element in slide["elements"] if element.get("imageType") == "decoration"]
    assert content and all("clip" in element for element in content)
    assert decorations and all(element["src"].startswith("/api/data/template_15_asset_") for element in decorations)
    assert all("groupId" not in element for element in content)


def test_template_15_cover_variants_and_title_limits() -> None:
    minimal = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "cover", "data": {"title": "新品发布"}}],
        task_id="template-15-cover-minimal",
        fallback_title="新品发布",
    )["slides"][0]
    assert minimal["templateSlideId"] == "cover-minimal"
    hero = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "cover", "data": {"title": "新品发布"}, "images": _images(1)}],
        task_id="template-15-cover-hero",
        fallback_title="新品发布",
    )["slides"][0]
    assert hero["templateSlideId"] == "cover-hero"
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_15",
            semantic_slides=[{"type": "cover", "data": {"title": "超" * 37}}],
            task_id="template-15-cover-too-long",
            fallback_title="超长标题",
        )


def test_template_15_end_layouts_follow_action_count() -> None:
    minimal = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "end", "data": {"title": "发布完成"}}],
        task_id="template-15-end-minimal",
        fallback_title="发布完成",
    )["slides"][0]
    assert minimal["templateSlideId"] == "end-minimal"
    if _template()["metadata"]["buildStage"] == "production":
        action = _renderer().render(
            template_id="template_15",
            semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": ["发布", "跟进", "复盘"]}}],
            task_id="template-15-end-action",
            fallback_title="下一步",
        )["slides"][0]
        assert action["templateSlideId"] == "end-action"
        assert sum(_slot_type(element) == "item" for element in action["elements"]) == 3


@pytest.mark.parametrize(
    ("layout_kind", "count", "image_count", "expected_id"),
    [
        ("focus", 1, 0, "content-text-1"),
        ("hero", 1, 1, "content-hero-left"),
        ("hero", 2, 1, "content-hero-left"),
        ("hero", 3, 1, "content-hero-left"),
        ("metrics", 3, 0, "content-metrics-3"),
        ("metrics", 4, 0, "content-metrics-4"),
        ("metrics", 5, 0, "content-metrics-5"),
        ("compare", 2, 0, "content-compare-2"),
        ("compare", 4, 0, "content-compare-4"),
        ("gallery", 2, 2, "content-dual-image-2"),
        ("gallery", 3, 3, "content-gallery-3"),
        ("gallery", 4, 4, "content-gallery-4"),
        ("gallery", 5, 5, "content-gallery-5"),
        ("gallery", 6, 6, "content-gallery-6"),
        ("timeline", 3, 0, "content-timeline-3"),
        ("timeline", 4, 0, "content-timeline-4"),
        ("timeline", 5, 0, "content-timeline-5"),
        ("process", 3, 0, "content-process-3"),
        ("process", 4, 0, "content-process-4"),
        ("process", 5, 0, "content-process-5"),
        ("positioning", 3, 0, "content-positioning-3"),
        ("positioning", 4, 0, "content-positioning-4"),
    ],
)
def test_template_15_all_specialty_layouts_are_reachable(
    layout_kind: str,
    count: int,
    image_count: int,
    expected_id: str,
) -> None:
    """规格声明的每个专项容量都必须正向到达唯一稳定 ID。"""
    kind = "metric" if layout_kind == "metrics" else None
    slide = _render_content(
        count,
        image_count=image_count,
        layout_kind=layout_kind,
        kind=kind,
    )["slides"][0]
    assert slide["templateSlideId"] == expected_id


@pytest.mark.parametrize(("item_count", "expected"), [(1, "content-hero-left"), (2, "content-hero-left"), (3, "content-hero-left"), (4, "content-image-1-dense"), (5, "content-image-1-dense"), (6, "content-image-1-dense")])
def test_template_15_one_image_matrix(item_count: int, expected: str) -> None:
    slide = _render_content(item_count, image_count=1)["slides"][0]
    assert slide["templateSlideId"] == expected


@pytest.mark.parametrize("item_count", [2, 3, 4, 5, 6])
def test_template_15_two_image_matrix(item_count: int) -> None:
    slide = _render_content(item_count, image_count=2)["slides"][0]
    assert slide["templateSlideId"] == "content-dual-image-2"


@pytest.mark.parametrize("count", [3, 4, 5, 6])
def test_template_15_equal_gallery_matrix(count: int) -> None:
    slide = _render_content(count, image_count=count)["slides"][0]
    assert slide["templateSlideId"] == f"content-gallery-{count}"


@pytest.mark.parametrize(("image_count", "item_count"), [(2, 1), (3, 4), (4, 3), (5, 6), (6, 5), (7, 8)])
def test_template_15_rejects_invalid_image_item_matrix(image_count: int, item_count: int) -> None:
    with pytest.raises(TemplateRenderError):
        _render_content(item_count, image_count=image_count)


@pytest.mark.parametrize(("count", "expected"), [(7, [6, 1]), (8, [6, 2]), (11, [6, 5])])
def test_template_15_paginates_large_equal_image_sets(count: int, expected: list[int]) -> None:
    document = _render_content(count, image_count=count)
    actual = [
        sum(element.get("imageType") == "content" for element in slide["elements"])
        for slide in document["slides"]
    ]
    assert actual == expected


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_15_crops_horizontal_vertical_and_square_images(width: int, height: int) -> None:
    semantic = {
        "type": "content",
        "data": {"title": "产品主图", "items": _items(1)},
        "images": [{"src": "https://example.invalid/crop.jpg", "width": width, "height": height}],
    }
    slide = _renderer().render(
        template_id="template_15",
        semantic_slides=[semantic],
        task_id=f"template-15-crop-{width}-{height}",
        fallback_title="产品主图",
    )["slides"][0]
    content = next(element for element in slide["elements"] if element.get("imageType") == "content")
    clip = content["clip"]["range"]
    assert 0 <= clip[0][0] <= clip[1][0] <= 100
    assert 0 <= clip[0][1] <= clip[1][1] <= 100


def test_template_15_rejects_content_image_without_dimensions() -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_15",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺失尺寸", "items": _items(1)},
                "images": [{"src": "https://example.invalid/missing.jpg"}],
            }],
            task_id="template-15-missing-image-size",
            fallback_title="缺失尺寸",
        )


@pytest.mark.parametrize(
    ("name", "title", "with_image", "expected_id", "should_fail"),
    [
        ("hero-cjk-24", "中" * 24, True, "cover-hero", False),
        ("hero-cjk-25", "中" * 25, True, "cover-minimal", False),
        ("minimal-cjk-36", "中" * 36, False, "cover-minimal", False),
        ("minimal-cjk-37", "中" * 37, False, "", True),
        ("hero-latin-48", "A" * 48, True, "cover-hero", False),
        ("hero-latin-49", "A" * 49, True, "cover-minimal", False),
        ("minimal-latin-72", "A" * 72, False, "cover-minimal", False),
        ("minimal-latin-73", "A" * 73, False, "", True),
    ],
)
def test_template_15_cover_title_boundaries(
    name: str,
    title: str,
    with_image: bool,
    expected_id: str,
    should_fail: bool,
) -> None:
    semantic: dict[str, object] = {"type": "cover", "data": {"title": title}}
    if with_image:
        semantic["images"] = _images(1)
    if should_fail:
        with pytest.raises(TemplateRenderError):
            _renderer().render(template_id="template_15", semantic_slides=[semantic], task_id=name, fallback_title=title)
        return
    slide = _renderer().render(
        template_id="template_15",
        semantic_slides=[semantic],
        task_id=name,
        fallback_title=title,
    )["slides"][0]
    assert slide["templateSlideId"] == expected_id


@pytest.mark.parametrize(
    ("name", "title", "has_break", "should_fail"),
    [
        ("content-cjk-20", "中" * 20, False, False),
        ("content-cjk-21", "中" * 21, True, False),
        ("content-cjk-36", "中" * 36, True, False),
        ("content-cjk-37", "中" * 37, False, True),
        ("content-latin-44", "A" * 44, False, False),
        ("content-latin-45", "A" * 45, True, False),
        ("content-latin-80", "A" * 80, True, False),
        ("content-latin-81", "A" * 81, False, True),
        ("content-mixed-equal", "中" * 10 + "A" * 22, False, False),
        ("content-mixed-over", "中" * 10 + "A" * 23, True, False),
    ],
)
def test_template_15_content_title_boundaries(name: str, title: str, has_break: bool, should_fail: bool) -> None:
    if should_fail:
        with pytest.raises(TemplateRenderError):
            _render_content_with_title(title, name)
        return
    slide = _render_content_with_title(title, name)
    title_element = next(element for element in slide["elements"] if _slot_type(element) == "title")
    assert ("<br" in title_element["content"]) is has_break


def _render_content_with_title(title: str, task_id: str) -> dict:
    return _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "content", "data": {"title": title, "items": _items(1)}}],
        task_id=task_id,
        fallback_title=title,
    )["slides"][0]


def test_template_15_long_body_paginates_without_loss() -> None:
    body = "性能证据必须完整保留并按顺序进入下一页。" * 12
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{"type": "content", "data": {"title": "长正文", "items": _items(1, body=body)}}],
        task_id="template-15-long-body",
        fallback_title="长正文",
    )
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert len(document["slides"]) > 1
    assert rendered == body


def test_template_15_real_agent_five_item_titles_fit_without_content_loss() -> None:
    """真实 Agent 的五项内容标题应保持可读，正文分页后不得丢失。"""
    titles = ["中" * length for length in (15, 11, 12, 11, 13)]
    bodies = ["正" * length for length in (40, 44, 37, 41, 41)]
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "真实内容页标题",
                "items": [
                    {"title": title, "text": body}
                    for title, body in zip(titles, bodies, strict=True)
                ],
            },
        }],
        task_id="template-15-real-agent-five-items",
        fallback_title="真实内容页标题",
    )

    rendered_titles = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    rendered_bodies = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert rendered_titles
    assert all(title.startswith("核心要点") and len(title) <= 10 for title in rendered_titles)
    assert rendered_bodies == "".join(
        f"{title}。{body}" for title, body in zip(titles, bodies, strict=True)
    )


@pytest.mark.parametrize("title_length", [17, 18])
def test_template_15_long_item_titles_choose_readable_pagination(title_length: int) -> None:
    """正文拆段后即使标题带续页语义，也必须改用能容纳标题的低密度版式。"""
    title = "中" * title_length
    body = "正" * 40
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "长标题分页",
                "items": [{"title": title, "text": body} for _ in range(5)],
            },
        }],
        task_id=f"template-15-long-item-title-{title_length}",
        fallback_title="长标题分页",
    )

    rendered_titles = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    rendered_bodies = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert len(document["slides"]) > 1
    assert rendered_titles
    assert all(value.startswith("核心要点") and len(value) <= 10 for value in rendered_titles)
    assert rendered_bodies == (f"{title}。{body}") * 5


@pytest.mark.parametrize(
    ("name", "items", "expected_body"),
    [
        (
            "string-items",
            ["字" * 18 for _ in range(5)],
            "字" * 90,
        ),
        (
            "title-only-items",
            [{"title": "题" * 18} for _ in range(5)],
            "题" * 90,
        ),
        (
            "chart-item",
            [
                {"title": f"要点 {index}", "text": "短正文"}
                for index in range(1, 5)
            ] + [{
                "kind": "chart",
                "title": "指标趋势",
                "text": "中" * 18,
                "chartType": "bar",
                "labels": ["A"],
                "series": [{"name": "X", "data": [1]}],
            }],
            "短正文" * 4 + "中" * 18,
        ),
    ],
)
def test_template_15_items_that_lack_native_frames_paginate_without_loss(
    name: str,
    items: list[object],
    expected_body: str,
) -> None:
    """字符串、仅标题和无原生图表框的 item 都必须按实际正文容量拆页。"""
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "生产输入兼容", "items": items},
        }],
        task_id=f"template-15-{name}",
        fallback_title="生产输入兼容",
    )

    rendered_bodies = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert rendered_bodies == expected_body


@pytest.mark.parametrize("variant", ["horizon", "spectrum", "particle", "stage"])
def test_template_15_transition_accepts_declared_agent_copy_limit(variant: str) -> None:
    """过渡页必须容纳提示词允许的三句上限，不因确定性变体随机失败。"""
    body = "".join(f"{'中' * 24}。" for _ in range(3))
    title = "中" * 18
    slide = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": title, "text": body, "variant": variant},
        }],
        task_id=f"template-15-transition-{variant}",
        fallback_title=title,
    )["slides"][0]

    rendered_title = next(
        _plain_text(element)
        for element in slide["elements"]
        if _slot_type(element) == "title"
    )
    content = next(
        _plain_text(element)
        for element in slide["elements"]
        if _slot_type(element) == "content"
    )
    assert rendered_title == title
    assert content == body


@pytest.mark.parametrize("variant", ["spectrum", "stage"])
@pytest.mark.parametrize("body_length", [77, 89])
def test_template_15_compact_transition_accepts_observed_agent_lengths(
    variant: str,
    body_length: int,
) -> None:
    """紧凑过渡页必须容纳生产日志中的真实长度，不能因选版不同失败。"""
    body = "中" * body_length
    title = "中" * 18
    slide = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": title, "text": body, "variant": variant},
        }],
        task_id=f"template-15-transition-real-{variant}-{body_length}",
        fallback_title=title,
    )["slides"][0]

    title_element = next(
        element
        for element in slide["elements"]
        if _slot_type(element) == "title"
    )
    content_element = next(
        element
        for element in slide["elements"]
        if _slot_type(element) == "content"
    )
    assert _plain_text(content_element) == body
    assert content_element["top"] >= title_element["top"] + title_element["height"]
    assert content_element["left"] + content_element["width"] <= 936
    assert content_element["top"] + content_element["height"] <= 500


def test_template_15_default_transition_selection_follows_section_order() -> None:
    """默认过渡页按章节序号选版，同一 sectionIndex 不得随任务 ID 漂移。"""
    selected: set[str] = set()
    for task_id in ("a", "b", "c", "d", "e"):
        slide = _renderer().render(
            template_id="template_15",
            semantic_slides=[{
                "type": "transition",
                "data": {"title": "中" * 18, "text": "中" * 89, "sectionIndex": 2},
            }],
            task_id=task_id,
            fallback_title="中",
        )["slides"][0]
        selected.add(slide["templateSlideId"])

    assert selected == {"transition-spectrum"}

    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[
            {"type": "transition", "data": {"title": "中" * 18, "text": "中" * 89}}
            for _ in range(4)
        ],
        task_id="template-15-transition-order",
        fallback_title="中",
    )
    assert [slide["templateSlideId"] for slide in document["slides"]] == [
        "transition-horizon",
        "transition-spectrum",
        "transition-particle",
        "transition-stage",
    ]


def test_template_15_long_transition_copy_paginates_without_shifting_sections() -> None:
    """超长过渡文案应在原章节内无损拆页，不能挤占后续章节的确定性选版序号。"""
    long_body = "中" * 98
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[
            {"type": "transition", "data": {"title": "第一章", "text": "短文案"}},
            {"type": "transition", "data": {"title": "第二章", "text": long_body}},
            {"type": "transition", "data": {"title": "第三章", "text": "短文案"}},
            {"type": "transition", "data": {"title": "第四章", "text": "短文案"}},
        ],
        task_id="template-15-long-transition-pagination",
        fallback_title="章节",
    )

    assert [slide["templateSlideId"] for slide in document["slides"]] == [
        "transition-horizon",
        "transition-spectrum",
        "transition-spectrum",
        "transition-particle",
        "transition-stage",
    ]
    second_section = document["slides"][1:3]
    assert "".join(
        _plain_text(element)
        for slide in second_section
        for element in slide["elements"]
        if _slot_type(element) == "content"
    ) == long_body
    assert {
        _plain_text(element)
        for slide in second_section
        for element in slide["elements"]
        if _slot_type(element) == "partNumber"
    } == {"02"}


def test_template_15_multiline_transition_copy_paginates_by_rendered_height() -> None:
    """强制换行必须计入实际高度，不能因总字符数较短而绕过过渡页分页。"""
    body = "\n".join(["中" * 20] * 3)
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": "多行过渡", "text": body, "variant": "spectrum"},
        }],
        task_id="template-15-multiline-transition-pagination",
        fallback_title="多行过渡",
    )

    assert [slide["templateSlideId"] for slide in document["slides"]] == [
        "transition-spectrum",
        "transition-spectrum",
    ]
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "content"
    )
    assert rendered == body.replace("\n", "")
    assert {
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "partNumber"
    } == {"01"}


def test_template_15_long_body_with_image_keeps_image_on_first_part_only() -> None:
    body = "产品图只属于正文首段，后续分页不得重复固定内容图。" * 12
    document = _renderer().render(
        template_id="template_15",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "带图长正文", "items": _items(1, body=body)},
            "images": _images(1),
        }],
        task_id="template-15-long-body-image",
        fallback_title="带图长正文",
    )
    image_counts = [
        sum(element.get("imageType") == "content" for element in slide["elements"])
        for slide in document["slides"]
    ]
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert image_counts[0] == 1
    assert all(count == 0 for count in image_counts[1:])
    assert rendered == body
