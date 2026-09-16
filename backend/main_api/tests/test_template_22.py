"""template_22 桃夭墨韵商务汇报模板的专项测试。"""

from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError
from backend.main_api.template_assets import resolve_template_asset


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_peach_ink_template.mjs"
PROBE_ASSET_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa" / "probe-assets"
PROBE_IDS = {"cover-scroll-blossom", "content-image-1", "probe-image-circle-1"}
MVP_IDS = {
    "cover-scroll-blossom",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-petal-number",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "end-blossom-mountain",
}
PRODUCTION_IDS = MVP_IDS | {
    "cover-blossom-minimal",
    "transition-ink-circle",
    "content-statement-1",
    "content-image-1",
    "content-metrics-4",
    "end-action",
}
SAMPLE_IDS = {
    "cover-scroll-blossom",
    "contents-4",
    "transition-petal-number",
    "content-text-4",
    "content-metrics-4",
    "content-image-1",
    "end-blossom-mountain",
}
ASSET_CONTRACT = {
    "template_22_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 450_000),
    "template_22_asset_bg_content_v1.jpg": ((1920, 1080), "RGB", 280_000),
    "template_22_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 350_000),
    "template_22_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 420_000),
    "template_22_asset_scroll_roll_v1.png": ((1500, 900), "RGBA", 900_000),
    "template_22_asset_ink_title_frame_v1.png": ((1200, 320), "RGBA", 450_000),
    "template_22_asset_ink_circle_frame_v1.png": ((900, 900), "RGBA", 750_000),
    "template_22_asset_ink_brush_band_v1.png": ((1800, 360), "RGBA", 650_000),
    "template_22_asset_petal_sweep_v1.png": ((1200, 900), "RGBA", 700_000),
}


def _run_builder(output: Path, stage: str = "probe") -> dict[str, object]:
    result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", stage, str(output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(output.read_text(encoding="utf-8"))


def _plain_text(element: dict[str, object]) -> str:
    raw = element.get("content")
    if not isinstance(raw, str):
        text = element.get("text")
        raw = text.get("content", "") if isinstance(text, dict) else ""
    return unescape(re.sub(r"<[^>]+>", "", str(raw)))


def test_template_22_probe_builder_is_deterministic_and_has_required_inventory(tmp_path: Path) -> None:
    """构建器公共入口必须稳定产出三个约定探针页面。"""

    first = _run_builder(tmp_path / "probe-first.json")
    second = _run_builder(tmp_path / "probe-second.json")

    assert first == second
    assert first["metadata"]["buildStage"] == "probe"
    assert set(first["metadata"]["probeSlideIds"]) == PROBE_IDS
    assert {slide["id"] for slide in first["slides"]} == PROBE_IDS


@pytest.mark.parametrize(
    ("variant", "expected_slide_id", "expected_clip", "expected_ranges"),
    [
        (
            None,
            "content-image-1",
            "rect",
            {
                (1600, 900): [[11.5131579, 0], [88.4868421, 100]],
                (900, 1600): [[0, 29.4471154], [100, 70.5528846]],
                (1000, 1000): [[0, 13.4615385], [100, 86.5384615]],
            },
        ),
        (
            "circle",
            "probe-image-circle-1",
            "ellipse",
            {
                (1600, 900): [[21.875, 0], [78.125, 100]],
                (900, 1600): [[0, 21.875], [100, 78.125]],
                (1000, 1000): [[0, 0], [100, 100]],
            },
        ),
    ],
)
@pytest.mark.parametrize("width,height", [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_22_probe_renders_editable_image_slots(
    tmp_path: Path,
    variant: str | None,
    expected_slide_id: str,
    expected_clip: str,
    expected_ranges: dict[tuple[int, int], list[list[float]]],
    width: int,
    height: int,
) -> None:
    """普通图和圆图均通过公开渲染接口换图，并保留内容文字与装饰边界。"""

    template = _run_builder(tmp_path / "template_22.json")
    for filename in template["metadata"]["probeAssetFiles"]:
        (tmp_path / filename).write_bytes((PROBE_ASSET_ROOT / filename).read_bytes())

    data: dict[str, object] = {
        "title": "桃花主题图文",
        "items": [{"title": "完整标题", "text": "正文编辑和换图后必须完整保留。"}],
    }
    if variant:
        data["variant"] = variant
    document = PresentationTemplateRenderer(tmp_path).render(
        template_id="template_22",
        semantic_slides=[{
            "type": "content",
            "data": data,
            "images": [{
                "src": "https://example.invalid/template-22-content.jpg",
                "width": width,
                "height": height,
            }],
        }],
        task_id=f"template-22-probe-{expected_slide_id}-{width}-{height}",
        fallback_title="桃花主题图文",
    )

    slide = document["slides"][0]
    assert slide["templateSlideId"] == expected_slide_id
    content_image = next(element for element in slide["elements"] if element.get("imageType") == "content")
    assert content_image["src"].startswith("https://example.invalid/")
    assert content_image["clip"]["shape"] == expected_clip
    for actual_point, expected_point in zip(
        content_image["clip"]["range"], expected_ranges[(width, height)], strict=True
    ):
        assert actual_point == pytest.approx(expected_point)
    assert (content_image["originalWidth"], content_image["originalHeight"]) == (width, height)
    assert any("正文编辑和换图后必须完整保留" in _plain_text(element) for element in slide["elements"])
    decorations = [element for element in slide["elements"] if element.get("imageType") == "decoration"]
    assert decorations and all(element.get("lock") is True for element in decorations)


@pytest.mark.parametrize(
    ("stage", "expected_ids"),
    [("sample", SAMPLE_IDS), ("mvp", MVP_IDS), ("production", PRODUCTION_IDS)],
)
def test_template_22_builder_is_deterministic_for_each_release_stage(
    tmp_path: Path,
    stage: str,
    expected_ids: set[str],
) -> None:
    first = _run_builder(tmp_path / f"{stage}-first.json", stage)
    second = _run_builder(tmp_path / f"{stage}-second.json", stage)

    assert first == second
    assert first["metadata"]["buildStage"] == stage
    assert {slide["id"] for slide in first["slides"]} == expected_ids


def test_template_22_production_inventory_and_assets_match_contract(tmp_path: Path) -> None:
    template = _run_builder(tmp_path / "production.json", "production")
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}
    assert set(template["metadata"]["productionSlideIds"]) == PRODUCTION_IDS
    assert "probe-image-circle-1" not in template["metadata"]["productionSlideIds"]

    # groupId 表示一个页面内的业务内容组，不能跨页面复用并误联动。
    group_owners: dict[str, str] = {}
    for slide in template["slides"]:
        for element in slide["elements"]:
            group_id = element.get("groupId")
            if not group_id:
                continue
            owner = group_owners.setdefault(group_id, slide["id"])
            assert owner == slide["id"], f"groupId {group_id} 同时属于 {owner} 和 {slide['id']}"

    referenced = {
        element["src"].rsplit("/", 1)[-1]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image" and str(element.get("src", "")).startswith("/api/data/")
    }
    assert referenced == set(ASSET_CONTRACT)
    for filename, (size, mode, max_bytes) in ASSET_CONTRACT.items():
        path = TEMPLATE_ROOT / filename
        assert path.is_file()
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema()[0] == 0
        assert path.stat().st_size <= max_bytes


def test_template_22_production_ids_paths_and_roles_are_clean(tmp_path: Path) -> None:
    template = _run_builder(tmp_path / "production.json", "production")
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))

    serialized = json.dumps(template, ensure_ascii=False)
    assert "data:image/" not in serialized
    assert "file://" not in serialized
    assert "C:\\Users" not in serialized
    assert "animations" not in serialized
    assert template["theme"]["fontName"] == "微软雅黑"
    assert template["metadata"]["rightsPolicy"] == "reference-media-excluded"
    for slide in template["slides"]:
        for element in slide["elements"]:
            if element.get("type") == "image":
                assert element["src"].startswith("/api/data/template_22_asset_")
                assert element.get("imageType") in {"content", "decoration"}
                if element.get("imageType") == "decoration":
                    assert element.get("lock") is True


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_22_selects_exact_contents_capacity(count: int) -> None:
    values = [f"目录项目{index}" for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id=f"template-22-contents-{count}",
        fallback_title="目录",
    )["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"
    rendered = [_plain_text(element) for element in page["elements"] if element.get("textType") == "item"]
    assert rendered == values


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-statement-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_22_selects_exact_text_content_capacity(count: int, expected: str) -> None:
    items = [{"title": f"要点{index}", "text": f"完整正文{index}"} for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{"type": "content", "data": {"title": "内容页", "items": items}}],
        task_id=f"template-22-content-{count}",
        fallback_title="内容页",
    )["slides"][0]
    assert page["templateSlideId"] == expected
    body = "".join(_plain_text(element) for element in page["elements"] if element.get("textType") == "item")
    assert all(item["text"] in body for item in items)


def test_template_22_selects_content_image_and_preserves_crop() -> None:
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文页", "items": [{"title": "图文标题", "text": "图文正文"}]},
            "images": [{"src": "https://example.invalid/image.jpg", "width": 900, "height": 1600}],
        }],
        task_id="template-22-content-image",
        fallback_title="图文页",
    )["slides"][0]
    assert page["templateSlideId"] == "content-image-1"
    content_image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert content_image["clip"]["shape"] == "rect"
    assert content_image["originalWidth"] == 900
    assert content_image["originalHeight"] == 1600


def test_template_22_metrics_keep_titles_values_and_descriptions() -> None:
    items = [
        {"kind": "metric", "title": f"指标{index}", "value": f"{index * 20}%", "text": f"说明{index}"}
        for index in range(1, 5)
    ]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{"type": "content", "data": {"title": "业务指标", "items": items}}],
        task_id="template-22-metrics",
        fallback_title="业务指标",
    )["slides"][0]
    assert page["templateSlideId"] == "content-metrics-4"
    values = [_plain_text(element) for element in page["elements"] if element.get("textType") == "itemNumber"]
    assert values == [item["value"] for item in items]
    body = "".join(_plain_text(element) for element in page["elements"] if element.get("textType") == "item")
    assert all(item["text"] in body for item in items)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_22_selects_end_layout_and_preserves_actions(count: int) -> None:
    actions = [f"行动{index}" for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": actions}}],
        task_id=f"template-22-end-{count}",
        fallback_title="结束",
    )["slides"][0]
    assert page["templateSlideId"] == ("end-blossom-mountain" if count == 0 else "end-action")
    rendered = [_plain_text(element) for element in page["elements"] if element.get("textType") == "item"]
    assert rendered == actions


def test_template_22_paginates_contents_and_content_without_loss() -> None:
    directory = [f"章节{index}" for index in range(1, 12)]
    items = [{"title": f"要点{index}", "text": f"完整正文{index}"} for index in range(1, 9)]
    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[
            {"type": "contents", "data": {"items": directory}},
            {"type": "content", "data": {"title": "八项内容", "items": items}},
        ],
        task_id="template-22-pagination",
        fallback_title="分页",
    )
    rendered = "\n".join(_plain_text(element) for slide in document["slides"] for element in slide["elements"])
    directory_positions = [rendered.index(value) for value in directory]
    item_positions = [rendered.index(item["text"]) for item in items]
    assert directory_positions == sorted(directory_positions)
    assert item_positions == sorted(item_positions)
    assert len(document["slides"]) == 4


def test_template_22_long_titles_keep_four_item_density_and_source_content() -> None:
    titles = ["这是需要完整保留的业务项目长标题" + str(index) for index in range(1, 5)]
    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "标题保真", "items": [{"title": title, "text": "正文"} for title in titles]},
        }],
        task_id="template-22-long-titles",
        fallback_title="标题保真",
    )
    assert len(document["slides"]) == 1
    assert document["slides"][0]["templateSlideId"] == "content-text-4"
    rendered = "".join(_plain_text(element) for element in document["slides"][0]["elements"])
    positions = [rendered.index(title) for title in titles]
    assert positions == sorted(positions)


def test_template_22_four_item_boundary_titles_fit_without_losing_density() -> None:
    """四项页声明支持 10 个中文字，边界标题必须与真实槽位容量一致。"""

    titles = [
        "核心业务增长策略规划",
        "客户服务体验优化路径",
        "产品创新能力建设方案",
        "组织协同效率提升计划",
    ]
    items = [
        {"title": title, "text": f"完整正文{index}"}
        for index, title in enumerate(titles, start=1)
    ]
    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "十字标题边界", "items": items},
        }],
        task_id="template-22-four-item-ten-wide-title",
        fallback_title="十字标题边界",
    )

    assert len(document["slides"]) == 1
    page = document["slides"][0]
    assert page["templateSlideId"] == "content-text-4"
    rendered_titles = [
        _plain_text(element)
        for element in page["elements"]
        if element.get("textType") == "itemTitle"
    ]
    assert rendered_titles == titles
    rendered_body = "".join(
        _plain_text(element)
        for element in page["elements"]
        if element.get("textType") == "item"
    )
    positions = [rendered_body.index(item["text"]) for item in items]
    assert positions == sorted(positions)


def test_template_22_transition_circle_accepts_eleven_wide_title() -> None:
    """章节页的确定性墨圈变体必须容纳实际生成的 11 字标题。"""

    title = "项目实施路径与成果展望"
    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_22",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": title, "text": "章节说明"},
        }],
        task_id="template-22-transition-boundary-0",
        fallback_title="章节边界",
    )

    assert len(document["slides"]) == 1
    page = document["slides"][0]
    assert page["templateSlideId"] == "transition-ink-circle"
    rendered_title = next(
        _plain_text(element)
        for element in page["elements"]
        if element.get("textType") == "title"
    )
    assert rendered_title == title


def test_template_22_rejects_missing_image_dimensions_and_too_many_actions() -> None:
    renderer = PresentationTemplateRenderer(TEMPLATE_ROOT)
    with pytest.raises(TemplateRenderError) as missing_dimensions:
        renderer.render(
            template_id="template_22",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图文", "items": [{"title": "标题", "text": "正文"}]},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-22-missing-image-size",
            fallback_title="图文",
        )
    assert missing_dimensions.value.code == "TEMPLATE_DATA_INVALID"
    with pytest.raises(TemplateRenderError) as too_many_actions:
        renderer.render(
            template_id="template_22",
            semantic_slides=[{"type": "end", "data": {"items": ["一", "二", "三", "四"]}}],
            task_id="template-22-too-many-actions",
            fallback_title="结束",
        )
    assert too_many_actions.value.code == "TEMPLATE_DATA_INVALID"


def test_template_22_cover_and_registration_are_available() -> None:
    main_source = (REPOSITORY_ROOT / "backend" / "main_api" / "main.py").read_text(encoding="utf-8")
    registration = '{ "name": "桃夭墨韵商务汇报", "id": "template_22", "cover": "/api/data/template_22.jpg" }'
    assert main_source.count(registration) == 1

    cover = resolve_template_asset("template_22.jpg")
    with Image.open(cover) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
    assert cover.stat().st_size <= 150_000
