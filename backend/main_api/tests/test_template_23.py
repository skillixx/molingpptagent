"""template_23 蓝曜星幕商务汇报模板的专项回归测试。"""

from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.template_assets import resolve_template_asset
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_cyan_star_business_template.mjs"
REFERENCE_PATH = Path.home() / "Desktop" / "星空风格(1).pptx"
PROBE_IDS = {"cover-horizon", "content-image-1", "content-metrics-4"}
PRODUCTION_IDS = {
    "cover-horizon",
    "cover-visual",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-particle-number",
    "transition-lightline",
    "content-focus-1",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "content-image-1",
    "content-metrics-3",
    "content-metrics-4",
    "content-metrics-5",
    "end-horizon",
    "end-action",
}
ASSET_CONTRACT = {
    "template_23_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 450_000),
    "template_23_asset_bg_content_v1.jpg": ((1920, 1080), "RGB", 300_000),
    "template_23_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 380_000),
    "template_23_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 420_000),
    "template_23_asset_particle_field_v1.png": ((1600, 900), "RGBA", 800_000),
    "template_23_asset_horizon_glow_v1.png": ((1800, 600), "RGBA", 600_000),
    "template_23_asset_title_flare_v1.png": ((1800, 180), "RGBA", 350_000),
    "template_23_asset_image_halo_v1.png": ((1200, 900), "RGBA", 700_000),
    "template_23_asset_grid_arc_v1.png": ((1600, 900), "RGBA", 650_000),
}


def _run_builder(output: Path, stage: str = "production") -> dict[str, object]:
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


def test_template_23_builder_is_deterministic_for_probe_and_production(tmp_path: Path) -> None:
    for stage, expected in (("probe", PROBE_IDS), ("production", PRODUCTION_IDS)):
        first = _run_builder(tmp_path / f"{stage}-first.json", stage)
        second = _run_builder(tmp_path / f"{stage}-second.json", stage)
        assert first == second
        assert first["metadata"]["buildStage"] == stage
        assert {slide["id"] for slide in first["slides"]} == expected


def test_template_23_production_inventory_assets_and_roles_match_contract(tmp_path: Path) -> None:
    template = _run_builder(tmp_path / "production.json")
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 8, "end": 2}
    assert set(template["metadata"]["productionSlideIds"]) == PRODUCTION_IDS

    group_owners: dict[str, str] = {}
    referenced: set[str] = set()
    for slide in template["slides"]:
        for element in slide["elements"]:
            group_id = element.get("groupId")
            if group_id:
                owner = group_owners.setdefault(group_id, slide["id"])
                assert owner == slide["id"]
            if element.get("type") == "image":
                assert element["src"].startswith("/api/data/template_23_asset_")
                assert element.get("imageType") in {"content", "decoration"}
                if element.get("imageType") == "decoration":
                    assert element.get("lock") is True
                referenced.add(element["src"].rsplit("/", 1)[-1])
    assert referenced == set(ASSET_CONTRACT)

    for filename, (size, mode, max_bytes) in ASSET_CONTRACT.items():
        asset = TEMPLATE_ROOT / filename
        with Image.open(asset) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema()[0] == 0
        assert asset.stat().st_size <= max_bytes

    serialized = json.dumps(template, ensure_ascii=False)
    assert "data:image/" not in serialized
    assert "file://" not in serialized
    assert "C:\\Users" not in serialized
    assert "animations" not in serialized
    assert template["theme"]["fontName"] == "微软雅黑"
    assert template["metadata"]["rightsPolicy"] == "reference-media-excluded"


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_23_selects_exact_contents_capacity(count: int) -> None:
    values = [f"目录项目{index}" for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id=f"template-23-contents-{count}",
        fallback_title="目录",
    )["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"
    rendered = [_plain_text(element) for element in page["elements"] if element.get("textType") == "item"]
    assert rendered == values


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-focus-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_23_selects_exact_text_content_capacity(count: int, expected: str) -> None:
    items = [{"title": f"要点{index}", "text": f"完整正文{index}"} for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[{"type": "content", "data": {"title": "内容页", "items": items}}],
        task_id=f"template-23-content-{count}",
        fallback_title="内容页",
    )["slides"][0]
    assert page["templateSlideId"] == expected
    body = "".join(_plain_text(element) for element in page["elements"] if element.get("textType") == "item")
    assert all(item["text"] in body for item in items)


@pytest.mark.parametrize(
    ("width", "height", "expected_range"),
    [
        (1600, 900, [[12.4417702, 0], [87.5582298, 100]]),
        (900, 1600, [[0, 28.9389535], [100, 71.0610465]]),
        (1000, 1000, [[0, 12.5581395], [100, 87.4418605]]),
    ],
)
def test_template_23_content_image_is_replaceable_and_keeps_center_crop(
    width: int,
    height: int,
    expected_range: list[list[float]],
) -> None:
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文页", "items": [{"title": "图文标题", "text": "图文正文"}]},
            "images": [{"src": "https://example.invalid/image.jpg", "width": width, "height": height}],
        }],
        task_id="template-23-content-image",
        fallback_title="图文页",
    )["slides"][0]
    assert page["templateSlideId"] == "content-image-1"
    content_image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert content_image["src"].startswith("https://example.invalid/")
    assert content_image["clip"]["shape"] == "rect"
    assert content_image["originalWidth"] == width
    assert content_image["originalHeight"] == height
    assert content_image["minimumSourceWidth"] == 600
    assert content_image["minimumSourceHeight"] == 450
    for actual_point, expected_point in zip(content_image["clip"]["range"], expected_range, strict=True):
        assert actual_point == pytest.approx(expected_point)
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    assert decorations and all(element.get("lock") is True for element in decorations)


@pytest.mark.parametrize("count", [3, 4, 5])
def test_template_23_metrics_keep_titles_values_and_descriptions(count: int) -> None:
    items = [
        {"kind": "metric", "title": f"指标{index}", "value": f"{index * 17}%", "text": f"说明{index}"}
        for index in range(1, count + 1)
    ]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[{"type": "content", "data": {"title": "业务指标", "items": items}}],
        task_id=f"template-23-metrics-{count}",
        fallback_title="业务指标",
    )["slides"][0]
    assert page["templateSlideId"] == f"content-metrics-{count}"
    values = [_plain_text(element) for element in page["elements"] if element.get("textType") == "itemNumber"]
    assert values == [item["value"] for item in items]
    body = "".join(_plain_text(element) for element in page["elements"] if element.get("textType") == "item")
    assert all(item["text"] in body for item in items)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_23_selects_end_layout_and_preserves_actions(count: int) -> None:
    actions = [f"行动{index}" for index in range(1, count + 1)]
    page = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": actions}}],
        task_id=f"template-23-end-{count}",
        fallback_title="结束",
    )["slides"][0]
    assert page["templateSlideId"] == ("end-horizon" if count == 0 else "end-action")
    rendered = [_plain_text(element) for element in page["elements"] if element.get("textType") == "item"]
    assert rendered == actions


def test_template_23_paginates_without_loss_and_keeps_long_title_density() -> None:
    directory = [f"章节{index}" for index in range(1, 12)]
    titles = [f"这是需要完整保留的业务项目长标题{index}" for index in range(1, 9)]
    items = [{"title": title, "text": f"完整正文{index}"} for index, title in enumerate(titles, 1)]
    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=[
            {"type": "contents", "data": {"items": directory}},
            {"type": "content", "data": {"title": "八项内容", "items": items}},
        ],
        task_id="template-23-pagination",
        fallback_title="分页",
    )
    rendered = "\n".join(_plain_text(element) for slide in document["slides"] for element in slide["elements"])
    assert [rendered.index(value) for value in directory] == sorted(rendered.index(value) for value in directory)
    assert [rendered.index(item["text"]) for item in items] == sorted(rendered.index(item["text"]) for item in items)
    assert all(title in rendered for title in titles)
    content_pages = [slide for slide in document["slides"] if slide["templateSlideId"].startswith("content-")]
    assert [slide["templateSlideId"] for slide in content_pages] == ["content-text-4", "content-text-4"]


def test_template_23_uses_lower_density_layouts_before_splitting_normal_body_text() -> None:
    """普通长度正文应先降为两项版式，不能被四项小正文框拆成异常多页。"""

    semantic_slides = []
    expected_bodies: dict[str, str] = {}
    for page_index in range(1, 4):
        page_title = f"固定复现页{page_index}"
        items = []
        for item_index in range(1, 5):
            item_title = f"第{page_index}页需要完整保留的业务项目标题{item_index}"
            body = f"{item_title}。{'正文说明' * 18}尾{page_index}{item_index}"
            items.append({"title": item_title, "text": body})
        expected_bodies[page_title] = "".join(item["text"] for item in items)
        semantic_slides.append({
            "type": "content",
            "data": {"title": page_title, "items": items},
        })

    document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
        template_id="template_23",
        semantic_slides=semantic_slides,
        task_id="template-23-body-density-regression",
        fallback_title="正文密度回归",
    )

    assert len(document["slides"]) == 6
    assert all(slide["templateSlideId"] == "content-text-2" for slide in document["slides"])
    for page_title, expected in expected_bodies.items():
        related = [
            slide
            for slide in document["slides"]
            if any(
                element.get("textType") == "title"
                and _plain_text(element).startswith(page_title)
                for element in slide["elements"]
            )
        ]
        rendered_body = "".join(
            _plain_text(element)
            for slide in related
            for element in slide["elements"]
            if element.get("textType") == "item"
        )
        assert rendered_body == expected


def test_template_23_rejects_invalid_image_and_metric_inputs() -> None:
    renderer = PresentationTemplateRenderer(TEMPLATE_ROOT)
    with pytest.raises(TemplateRenderError) as missing_dimensions:
        renderer.render(
            template_id="template_23",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图文", "items": [{"title": "标题", "text": "正文"}]},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-23-missing-image-size",
            fallback_title="图文",
        )
    assert missing_dimensions.value.code == "TEMPLATE_DATA_INVALID"

    with pytest.raises(TemplateRenderError) as undersized_image:
        renderer.render(
            template_id="template_23",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图文", "items": [{"title": "标题", "text": "正文"}]},
                "images": [{"src": "https://example.invalid/too-small.jpg", "width": 599, "height": 450}],
            }],
            task_id="template-23-undersized-image",
            fallback_title="图文",
        )
    assert undersized_image.value.code == "TEMPLATE_DATA_INVALID"

    bad_metrics = [
        {"kind": "metric", "title": f"指标{index}", "value": "", "text": "说明"}
        for index in range(1, 4)
    ]
    with pytest.raises(TemplateRenderError) as missing_value:
        renderer.render(
            template_id="template_23",
            semantic_slides=[{"type": "content", "data": {"items": bad_metrics}}],
            task_id="template-23-missing-metric-value",
            fallback_title="指标",
        )
    assert missing_value.value.code == "TEMPLATE_DATA_INVALID"


def test_template_23_reference_registration_and_cover_are_available() -> None:
    assert REFERENCE_PATH.is_file()
    main_source = (REPOSITORY_ROOT / "backend" / "main_api" / "main.py").read_text(encoding="utf-8")
    registration = '{ "name": "蓝曜星幕商务汇报", "id": "template_23", "cover": "/api/data/template_23.jpg" }'
    assert main_source.count(registration) == 1

    cover = resolve_template_asset("template_23.jpg")
    with Image.open(cover) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
    assert cover.stat().st_size <= 150_000
