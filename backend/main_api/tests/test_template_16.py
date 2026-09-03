"""深空星环科技模板的结构、容量、图片保护与资源回归测试。"""

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
TEMPLATE_PATH = TEMPLATE_ROOT / "template_16.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_deep_space_orbit_template.mjs"
PREVIEW_RENDERER_PATH = REPOSITORY_ROOT / "utils" / "render_pptist_template_preview.mjs"

MVP_IDS = {
    "cover-orbit",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-orbit",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "end-orbit",
}

PRODUCTION_IDS = MVP_IDS | {
    "cover-image",
    "transition-nebula",
    "content-focus-1",
    "content-image-1",
    "content-image-2",
    "end-action",
}


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _renderer() -> PresentationTemplateRenderer:
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


def _items(count: int, *, body: str | None = None) -> list[dict[str, str]]:
    return [
        {"title": f"要点 {index}", "text": body or f"第 {index} 项完整说明。"}
        for index in range(1, count + 1)
    ]


def _images(count: int, *, width: int = 1600, height: int = 900) -> list[dict[str, object]]:
    return [
        {
            "src": f"https://example.invalid/content-{index}.jpg",
            "width": width,
            "height": height,
        }
        for index in range(1, count + 1)
    ]


def _render_content(count: int, *, image_count: int = 0) -> dict:
    semantic: dict[str, object] = {
        "type": "content",
        "data": {"title": "深空中的关键洞察", "items": _items(count)},
    }
    if image_count:
        semantic["images"] = _images(image_count)
    return _renderer().render(
        template_id="template_16",
        semantic_slides=[semantic],
        task_id=f"template-16-{count}-{image_count}",
        fallback_title="深空洞察",
    )


def test_template_16_inventory_matches_goal() -> None:
    """生产版必须为 18 页，MVP 必须精确包含 12 个稳定 ID。"""
    template = _template()
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_16"
    assert template["title"] == "深空星环科技"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert template["metadata"]["buildStage"] == "production"
    assert set(template["metadata"]["mvpSlideIds"]) == MVP_IDS
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}


@pytest.mark.parametrize(("stage", "expected"), [("mvp", 12), ("production", 18)])
def test_template_16_builder_is_deterministic(tmp_path: Path, stage: str, expected: int) -> None:
    output = tmp_path / f"template_16_{stage}.json"
    result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", stage, str(output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    value = json.loads(output.read_text(encoding="utf-8"))
    assert len(value["slides"]) == expected
    assert value["metadata"]["buildStage"] == stage
    second_output = tmp_path / f"template_16_{stage}_second.json"
    second_result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", stage, str(second_output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert second_result.returncode == 0, second_result.stderr
    assert json.loads(second_output.read_text(encoding="utf-8")) == value
    if stage == "production":
        # 防止构建器或 template_8 基础骨架变化后，提交的生产 JSON 静默漂移。
        assert value == _template()


def test_template_16_preview_renderer_escapes_untrusted_markup(tmp_path: Path) -> None:
    """静态预览器不得把模板标题或文本内容直接拼成可执行 HTML。"""
    source = tmp_path / "untrusted-template.json"
    output = tmp_path / "preview.html"
    source.write_text(
        json.dumps({
            "id": "untrusted",
            "title": "</title><script>window.titleAttack = true</script>",
            "slides": [{
                "id": "cover",
                "type": "cover",
                "background": {"color": "#04131f"},
                "elements": [{
                    "id": "unsafe-text",
                    "type": "text",
                    "content": "<p><img src=x onerror='window.textAttack=true'><strong>安全文本</strong></p>",
                    "left": 0,
                    "top": 0,
                    "width": 300,
                    "height": 80,
                }],
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["node", str(PREVIEW_RENDERER_PATH), str(source), str(output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    html = output.read_text(encoding="utf-8")
    assert "<title>&lt;/title&gt;&lt;script&gt;window.titleAttack = true&lt;/script&gt; 预览</title>" in html
    assert "</title><script>window.titleAttack" not in html
    assert "node.innerHTML = element.content" not in html
    assert "holder.innerHTML" not in html
    assert "appendSafeText(node, element.content)" in html
    assert "\\u003cimg src=x onerror='window.textAttack=true'>" in html


def test_template_16_assets_are_external_and_valid() -> None:
    """四个发布素材与封面必须满足尺寸、模式、Alpha 和体积规格。"""
    expected = {
        "template_16_asset_bg_space_dark_v1.jpg": ((1920, 1080), "RGB", 380_000),
        "template_16_asset_orbital_ring_v1.png": ((1200, 1200), "RGBA", 900_000),
        "template_16_asset_constellation_edge_v1.png": ((1600, 900), "RGBA", 900_000),
        "template_16_asset_nebula_glow_v1.png": ((1200, 700), "RGBA", 700_000),
    }
    assert {path.name for path in TEMPLATE_ROOT.glob("template_16_asset_*")} == set(expected)
    for name, (size, mode, max_bytes) in expected.items():
        path = TEMPLATE_ROOT / name
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                alpha_min, alpha_max = image.getchannel("A").getextrema()
                assert alpha_min < 255 and alpha_max > 0
        assert path.stat().st_size <= max_bytes
    with Image.open(TEMPLATE_ROOT / "template_16.jpg") as cover:
        assert cover.size == (960, 540)
        assert cover.mode == "RGB"


def test_template_16_ids_fonts_paths_and_samples_are_clean() -> None:
    template = _template()
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)
    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    assert "template_8_asset_" not in serialized
    assert "扁平风格(38)" not in serialized
    assert not any(value in serialized for value in ("2019", "XXX设计", "FEI ER", "THANK YOU"))
    assert not any(value in serialized for value in ("Agency FB", "时尚中黑简体", "华文细黑"))
    for slide in template["slides"]:
        for element in slide["elements"]:
            if _slot_type(element) == "title":
                assert element.get("minimumFontSize", 0) >= 35
            elif _slot_type(element) == "itemTitle":
                expected = 20 if slide["id"] in {"content-text-2", "content-text-3", "content-text-4"} else 24
                assert element.get("minimumFontSize", 0) >= expected
            elif _slot_type(element) in {"item", "content"}:
                assert element.get("minimumFontSize", 0) >= 16


def test_template_16_references_every_published_asset() -> None:
    template = _template()
    referenced = {
        element["src"].rsplit("/", 1)[-1]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
        and isinstance(element.get("src"), str)
        and element["src"].startswith("/api/data/template_16_asset_")
    }
    published = {path.name for path in TEMPLATE_ROOT.glob("template_16_asset_*")}
    assert referenced == published
    assert all(not source.startswith("data:") for source in referenced)


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_16_selects_exact_contents_capacity(count: int) -> None:
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[{"type": "contents", "data": {"items": [f"章节 {index}" for index in range(count)]}}],
        task_id=f"template-16-contents-{count}",
        fallback_title="目录",
    )
    slide = document["slides"][0]
    assert slide["templateSlideId"] == f"contents-{count}"
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-focus-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_16_selects_exact_text_capacity(count: int, expected: str) -> None:
    slide = _render_content(count)["slides"][0]
    assert slide["templateSlideId"] == expected
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in slide["elements"])


@pytest.mark.parametrize(("count", "expected"), [(1, "content-image-1"), (2, "content-image-2")])
def test_template_16_fills_only_content_image_slots(count: int, expected: str) -> None:
    slide = _render_content(count, image_count=count)["slides"][0]
    content = [element for element in slide["elements"] if element.get("imageType") == "content"]
    decoration = [element for element in slide["elements"] if element.get("imageType") == "decoration"]
    assert slide["templateSlideId"] == expected
    assert len(content) == count
    assert all(element["src"].startswith("https://example.invalid/") for element in content)
    assert all("clip" in element for element in content)
    assert decoration and all(element["src"].startswith("/api/data/template_16_asset_") for element in decoration)


def test_template_16_empty_images_do_not_expose_content_frames() -> None:
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "无图内容", "items": _items(1)},
            "images": [{"src": "   "}, {"alt": "缺少地址"}],
        }],
        task_id="template-16-empty-image",
        fallback_title="无图内容",
    )
    assert document["slides"][0]["templateSlideId"] == "content-focus-1"
    assert not any(element.get("imageType") == "content" for element in document["slides"][0]["elements"])


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_16_crops_horizontal_vertical_and_square_images(width: int, height: int) -> None:
    semantic = {
        "type": "content",
        "data": {"title": "图片裁剪", "items": _items(1)},
        "images": _images(1, width=width, height=height),
    }
    slide = _renderer().render(
        template_id="template_16",
        semantic_slides=[semantic],
        task_id=f"template-16-crop-{width}-{height}",
        fallback_title="图片裁剪",
    )["slides"][0]
    clip = next(element["clip"]["range"] for element in slide["elements"] if element.get("imageType") == "content")
    assert 0 <= clip[0][0] <= clip[1][0] <= 100
    assert 0 <= clip[0][1] <= clip[1][1] <= 100


def test_template_16_rejects_missing_image_dimensions() -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_16",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "尺寸缺失", "items": _items(1)},
                "images": [{"src": "https://example.invalid/missing.jpg"}],
            }],
            task_id="template-16-missing-size",
            fallback_title="尺寸缺失",
        )


def test_template_16_paginates_eight_items_without_reordering() -> None:
    items = _items(8)
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-16-eight-items",
        fallback_title="八项内容",
    )
    rendered = "".join(_plain_text(element) for slide in document["slides"] for element in slide["elements"])
    assert len(document["slides"]) > 1
    positions = [rendered.index(item["text"]) for item in items]
    assert positions == sorted(positions)


def test_template_16_long_body_is_split_without_loss() -> None:
    body = "深空中的复杂信息需要按层级组织，并完整保留每一条证据。" * 12
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "长正文", "items": [{"title": "完整说明", "text": body}]},
        }],
        task_id="template-16-long-body",
        fallback_title="长正文",
    )
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        )
    )
    assert len(document["slides"]) > 1
    assert rendered == body


def test_template_16_transition_variants_are_both_reachable() -> None:
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[
            {"type": "transition", "data": {"title": "第一章", "text": "建立问题背景。"}},
            {"type": "transition", "data": {"title": "第二章", "text": "形成行动方案。"}},
        ],
        task_id="template-16-transition-variants",
        fallback_title="章节",
    )
    assert {slide["templateSlideId"] for slide in document["slides"]} == {
        "transition-orbit",
        "transition-nebula",
    }


def test_template_16_accepts_real_agent_cover_subtitle_boundary() -> None:
    """真实 Agent 的 28 字封面副标题必须在 16px 最小字号下完整容纳。"""
    subtitle = "中" * 28
    assert len(subtitle) == 28
    document = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "人工智能项目全流程管理", "text": subtitle},
        }],
        task_id="template-16-real-cover-boundary",
        fallback_title="人工智能项目全流程管理",
    )
    assert subtitle in json.dumps(document, ensure_ascii=False)


def test_template_16_cover_variants_select_by_image_presence() -> None:
    """无图封面和带图封面必须按 Agent 是否提供内容图确定性选版。"""
    without_image = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "深空洞察", "text": "让复杂信息清晰呈现"},
        }],
        task_id="template-16-cover-without-image",
        fallback_title="深空洞察",
    )["slides"][0]
    with_image = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "深空洞察", "text": "让复杂信息清晰呈现"},
            "images": _images(1),
        }],
        task_id="template-16-cover-with-image",
        fallback_title="深空洞察",
    )["slides"][0]

    assert without_image["templateSlideId"] == "cover-orbit"
    assert with_image["templateSlideId"] == "cover-image"
    content_images = [
        element for element in with_image["elements"]
        if element.get("imageType") == "content"
    ]
    assert len(content_images) == 1
    assert content_images[0]["src"] == "https://example.invalid/content-1.jpg"


def test_template_16_end_action_selects_by_item_count() -> None:
    minimal = _renderer().render(
        template_id="template_16",
        semantic_slides=[{"type": "end", "data": {"title": "感谢观看"}}],
        task_id="template-16-end-minimal",
        fallback_title="感谢观看",
    )["slides"][0]
    action = _renderer().render(
        template_id="template_16",
        semantic_slides=[{
            "type": "end",
            "data": {"title": "下一步", "items": ["确认方案", "明确负责人", "安排复盘"]},
        }],
        task_id="template-16-end-action",
        fallback_title="下一步",
    )["slides"][0]
    assert minimal["templateSlideId"] == "end-orbit"
    assert action["templateSlideId"] == "end-action"
    assert sum(_slot_type(element) == "item" for element in action["elements"]) == 3
