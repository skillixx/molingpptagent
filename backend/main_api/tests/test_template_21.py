"""template_21 蓝米流纹商务汇报模板的 G2 探针专项测试。"""

from __future__ import annotations

import json
import ast
import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_21.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_blue_ivory_marble_template.mjs"
PROBE_IDS = {"cover-marble-frame", "content-text-4", "content-image-1"}
PRODUCTION_IDS = {
    "cover-marble-frame", "cover-marble-minimal", "contents-2", "contents-3", "contents-4",
    "contents-5", "contents-6", "contents-10", "transition-marble-left", "transition-marble-right",
    "content-focus-1", "content-image-1", "content-text-2", "content-text-3", "content-text-4",
    "content-metrics-4", "end-marble-frame", "end-action",
}
ASSET_CONTRACT = {
    "template_21_asset_bg_cover_v2.jpg": ((1920, 1080), "RGB", 450_000),
    "template_21_asset_bg_content_v1.jpg": ((1920, 1080), "RGB", 280_000),
    "template_21_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 350_000),
    "template_21_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 420_000),
    "template_21_asset_marble_tile_blue_v1.jpg": ((1200, 1200), "RGB", 320_000),
    "template_21_asset_marble_tile_ivory_v1.jpg": ((1200, 1200), "RGB", 320_000),
    "template_21_asset_bottom_flow_v1.png": ((1800, 460), "RGBA", 750_000),
    "template_21_asset_side_flow_v1.png": ((650, 1080), "RGBA", 650_000),
    "template_21_asset_corner_flow_v1.png": ((1200, 900), "RGBA", 850_000),
}


def _renderer() -> PresentationTemplateRenderer:
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def test_cover_background_matches_content_palette() -> None:
    """封面复用用户选定的正文蓝白背景，避免恢复为旧版黄绿色满版纹理。"""
    cover = TEMPLATE_ROOT / "template_21_asset_bg_cover_v2.jpg"
    content = TEMPLATE_ROOT / "template_21_asset_bg_content_v1.jpg"
    assert cover.read_bytes() == content.read_bytes()


def test_generated_cover_uses_blue_white_versioned_asset() -> None:
    """生成文档本身必须引用新背景，不能只更新模板列表缩略图。"""
    document = _renderer().render(
        template_id="template_21",
        semantic_slides=[{"type": "cover", "data": {"title": "业务汇报", "text": "配色检查"}}],
        task_id="cover-asset-revision", fallback_title="业务汇报",
    )
    background = next(e for e in document["slides"][0]["elements"] if e.get("type") == "image")
    assert background["src"] == "/api/data/template_21_asset_bg_cover_v2.jpg"
    assert background["imageType"] == "decoration"


@pytest.mark.parametrize("cover_id", ["cover-marble-frame", "cover-marble-minimal"])
def test_cover_preserves_long_chinese_subtitle(tmp_path: Path, cover_id: str) -> None:
    """两个封面都必须完整容纳两行中文副标题，且不侵入下方装饰线。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    template["slides"] = [s for s in template["slides"] if s["id"] == cover_id]
    # 隔离模板库存时复制真实装饰资源，确保测试失败来自文本容量而非缺图。
    for element in template["slides"][0]["elements"]:
        if str(element.get("src", "")).startswith("/api/data/"):
            name = element["src"].rsplit("/", 1)[-1]
            shutil.copyfile(TEMPLATE_ROOT / name, tmp_path / name)
    (tmp_path / "template_21.json").write_text(json.dumps(template), encoding="utf-8")
    subtitle = "测" * 31
    document = PresentationTemplateRenderer(tmp_path).render(
        template_id="template_21",
        semantic_slides=[{"type": "cover", "data": {"title": "业务汇报", "text": subtitle}}],
        task_id="cover-long-subtitle",
        fallback_title="业务汇报",
    )
    slot = next(e for e in document["slides"][0]["elements"] if e.get("textType") == "content")
    assert subtitle in slot["content"]
    assert slot["top"] + slot["height"] < 395


def _items(count: int) -> list[dict[str, str]]:
    return [{"title": f"item{index}", "text": f"Full item {index} body."} for index in range(1, count + 1)]


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_contents_preserves_chinese_line_breaks(count: int) -> None:
    """目录项带显式换行时仍保留全文，且相邻项目文本框不重叠。"""
    value = "业务发展规划\n年度执行方案"
    page = _renderer().render(template_id="template_21",
        semantic_slides=[{"type": "contents", "data": {"items": [value] * count}}],
        task_id="contents-chinese-lines", fallback_title="目录")["slides"][0]
    slots = [e for e in page["elements"] if e.get("textType") == "item"]
    assert len(slots) == count
    for slot in slots:
        assert "业务发展规划" in slot["content"] and "年度执行方案" in slot["content"]
        assert slot["top"] + slot["height"] <= 500
    for a, b in zip(slots, slots[1:]):
        if a["left"] == b["left"]:
            assert a["top"] + a["height"] <= b["top"]


@pytest.mark.parametrize("title", ["...", "感谢观看"])
def test_end_default_and_chinese_title_fit(title: str) -> None:
    """Agent 返回空占位结束语时，默认四字标题也必须通过最终容量检查。"""
    page = _renderer().render(template_id="template_21",
        semantic_slides=[{"type": "end", "data": {"title": title, "text": "..."}}],
        task_id="end-default-title", fallback_title="...")["slides"][0]
    assert any("感谢观看" in e.get("content", "") for e in page["elements"])


@pytest.mark.parametrize("slide_id", sorted(PRODUCTION_IDS))
def test_production_default_text_geometry(slide_id: str) -> None:
    """逐个检查生产版默认语义文字，防止未被换字的默认元素绕过字号适配。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slide = next(s for s in template["slides"] if s["id"] == slide_id)
    _renderer()._validate_slide_text_bounds(slide, template["height"])


def test_chinese_four_item_pages_do_not_explode() -> None:
    """常规中文正文应保持四项密度，不因模板浪费留白拆成大量续页。"""
    body = "业务进展保持稳定" * 8
    pages = [{"type": "content", "data": {"title": "业务进展", "items": [
        {"title": f"要点{i}", "text": body} for i in range(4)
    ]}} for _ in range(20)]
    result = _renderer().render(template_id="template_21", semantic_slides=pages,
                               task_id="chinese-density", fallback_title="业务汇报")
    assert len(result["slides"]) == 20
    for slide in result["slides"]:
        slots = [e for e in slide["elements"] if e.get("textType") == "item"]
        assert len(slots) == 4
        assert all(body in e["content"] for e in slots)
        assert all(e["top"] + e["height"] <= 500 for e in slots)


def test_template_21_probe_builder_is_deterministic(tmp_path: Path) -> None:
    """同一探针连续构建两次必须得到相同 JSON。"""

    outputs = [tmp_path / f"probe-{index}.json" for index in (1, 2)]
    for output in outputs:
        result = subprocess.run(
            ["node", str(BUILDER_PATH), "--stage", "probe", str(output)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    first = json.loads(outputs[0].read_text(encoding="utf-8"))
    second = json.loads(outputs[1].read_text(encoding="utf-8"))
    assert first == second
    assert first["metadata"]["buildStage"] == "probe"
    assert {slide["id"] for slide in first["slides"]} == PROBE_IDS


def test_template_21_probe_has_expected_inventory() -> None:
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert template["metadata"]["buildStage"] in {"probe", "mvp", "production"}
    if template["metadata"]["buildStage"] == "probe":
        assert {slide["id"] for slide in template["slides"]} == PROBE_IDS
    else:
        assert set(template["metadata"]["probeSlideIds"]) == PROBE_IDS
    assert template["metadata"]["sourceFidelity"].startswith("must-match-reference-style")


def test_template_21_four_item_probe_keeps_four_item_density() -> None:
    page = _renderer().render(
        template_id="template_21",
        semantic_slides=[{"type": "content", "data": {"title": "Four items", "items": _items(4)}}],
        task_id="template-21-four-item-probe",
        fallback_title="Four items",
    )["slides"][0]
    assert page["templateSlideId"] == "content-text-4"
    assert sum(element.get("textType") == "itemTitle" for element in page["elements"]) == 4
    assert sum(element.get("textType") == "item" for element in page["elements"]) == 4


@pytest.mark.parametrize("width,height", [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_21_image_probe_preserves_content_slot(width: int, height: int) -> None:
    page = _renderer().render(
        template_id="template_21",
        semantic_slides=[
            {
                "type": "content",
                "data": {"title": "Image probe", "items": _items(1)},
                "images": [{"src": "https://example.invalid/probe.jpg", "width": width, "height": height}],
            }
        ],
        task_id=f"template-21-image-probe-{width}-{height}",
        fallback_title="Image probe",
    )["slides"][0]
    content_image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert content_image["src"].startswith("https://example.invalid/")
    assert content_image.get("clip", {}).get("shape") == "rect"
    assert (content_image.get("originalWidth"), content_image.get("originalHeight")) == (width, height)
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    assert decorations
    assert all(element["lock"] for element in decorations)


def test_template_21_image_probe_rejects_missing_dimensions() -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_21",
            semantic_slides=[
                {
                    "type": "content",
                    "data": {"title": "Image probe", "items": _items(1)},
                    "images": [{"src": "https://example.invalid/no-size.jpg"}],
                }
            ],
            task_id="template-21-image-probe-missing-size",
            fallback_title="Image probe",
        )


def test_template_21_production_inventory_and_assets_match_goal() -> None:
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert template["metadata"]["buildStage"] == "production"
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS
    counts = {kind: sum(slide["type"] == kind for slide in template["slides"]) for kind in ("cover", "contents", "transition", "content", "end")}
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}
    for filename, (size, mode, limit) in ASSET_CONTRACT.items():
        asset_path = TEMPLATE_ROOT / filename
        assert asset_path.is_file()
        with Image.open(asset_path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema()[1] > 0
        assert asset_path.stat().st_size <= limit


def test_template_21_cover_and_registration_are_present() -> None:
    main_text = (REPOSITORY_ROOT / "backend" / "main_api" / "main.py").read_text(encoding="utf-8")
    assert '"name": "蓝米流纹商务汇报", "id": "template_21"' in main_text
    assert (TEMPLATE_ROOT / "template_21.jpg").is_file()


def test_template_21_listing_uses_revised_cover_url() -> None:
    """执行实际列表函数，不启动服务或连接数据库，确认新版缩略图地址使旧缓存失效。"""
    source = (REPOSITORY_ROOT / "backend/main_api/main.py").read_text(encoding="utf-8")
    function = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_templates")
    function.decorator_list = []
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "template-list", "exec"), namespace)
    templates = asyncio.run(namespace["get_templates"]())["data"]
    item = next(t for t in templates if t["id"] == "template_21")
    assert item["cover"] == "/api/data/template_21.jpg?v=2ce4dc01e4fa"
    assert next(t for t in templates if t["id"] == "template_20")["cover"] == "/api/data/template_20.jpg"


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_21_selects_exact_contents_capacity(count: int) -> None:
    values = [f"item-{index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_21",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id=f"template-21-contents-{count}",
        fallback_title="Contents",
    )["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-focus-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_21_selects_exact_content_capacity(count: int, expected: str) -> None:
    page = _renderer().render(
        template_id="template_21",
        semantic_slides=[{"type": "content", "data": {"title": "Content", "items": _items(count)}}],
        task_id=f"template-21-content-{count}",
        fallback_title="Content",
    )["slides"][0]
    assert page["templateSlideId"] == expected


def test_template_21_pagination_preserves_order_and_source_titles() -> None:
    source_items = [
        {"title": f"Original title {index}", "text": f"Original body {index} with enough text to exercise pagination."}
        for index in range(1, 9)
    ]
    document = _renderer().render(
        template_id="template_21",
        semantic_slides=[{"type": "content", "data": {"title": "Long content", "items": source_items}}],
        task_id="template-21-pagination",
        fallback_title="Long content",
    )
    rendered_item_text = [
        element.get("content", "")
        for slide in document["slides"]
        for element in slide.get("elements", [])
        if element.get("textType") == "item"
    ]
    assert len(document["slides"]) >= 2
    for index in range(1, 9):
        assert any(f"Original title {index}" in value or f"Original title {index}" in str(value) for value in rendered_item_text)
