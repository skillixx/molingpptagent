"""template_24 深蓝霓虹城市项目策划模板的 G2 探针测试。"""

from __future__ import annotations

import json
import re
import subprocess
import shutil
import importlib.util
from html import unescape
from pathlib import Path

from PIL import Image
import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_neon_city_project_template.mjs"
PROBE_IDS = {"cover-city", "content-text-4", "content-image-1"}
ASSET_CONTRACT = {
    "template_24_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB"),
    "template_24_asset_bg_content_v1.jpg": ((1920, 1080), "RGB"),
    "template_24_asset_bg_section_v1.jpg": ((1920, 1080), "RGB"),
    "template_24_asset_bg_end_v1.jpg": ((1920, 1080), "RGB"),
    "template_24_asset_city_grid_blue_v1.jpg": ((1200, 1200), "RGB"),
    "template_24_asset_city_glow_purple_v1.jpg": ((1200, 1200), "RGB"),
    "template_24_asset_route_light_v1.png": ((1800, 460), "RGBA"),
    "template_24_asset_edge_beam_v1.png": ((650, 1080), "RGBA"),
    "template_24_asset_skyline_corner_v1.png": ((1200, 900), "RGBA"),
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
    return unescape(re.sub(r"<[^>]+>", "", str(raw or "")))


def test_template_24_probe_builder_is_deterministic(tmp_path: Path) -> None:
    first = _run_builder(tmp_path / "first.json")
    second = _run_builder(tmp_path / "second.json")
    assert first == second
    assert first["id"] == "template_24"
    assert first["metadata"]["buildStage"] == "probe"
    assert {slide["id"] for slide in first["slides"]} == PROBE_IDS


def test_template_24_default_stage_honors_custom_output(tmp_path: Path) -> None:
    """在隔离目录复现默认参数路径错误，不能让回归测试覆盖正式模板。"""
    script = tmp_path / "utils" / BUILDER_PATH.name
    script.parent.mkdir()
    shutil.copyfile(BUILDER_PATH, script)
    output = tmp_path / "requested.json"
    result = subprocess.run(["node", str(script), str(output)], capture_output=True, timeout=30)
    assert result.returncode == 0
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8"))["metadata"]["buildStage"] == "production"
    assert not (tmp_path / "backend/main_api/template/template_24.json").exists()


def test_template_24_finalizer_keeps_closed_goal_records(tmp_path: Path, monkeypatch) -> None:
    """已确认的交付不能因误运行冻结器而退回待确认；检查原有记录字节不变。"""
    spec = importlib.util.spec_from_file_location("template24_finalizer", REPOSITORY_ROOT / "utils/finalize_template_24_qa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "QA", tmp_path)
    for name in ("g9-closure.json", "progress.json"):
        (tmp_path / name).write_text('{"status":"COMPLETE"}', encoding="utf-8")
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(RuntimeError, match="G9"):
        module.main()
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()} == before


def test_template_24_probe_stays_inside_canvas_and_uses_readable_body(tmp_path: Path) -> None:
    """固定截图暴露的越界与小字号，防止复用布局时带入旧模板缺陷。"""
    template = _run_builder(tmp_path / "geometry.json")
    for slide in template["slides"]:
        content_groups = {
            element.get("groupId") for element in slide["elements"]
            if element.get("imageType") == "content"
        }
        for element in slide["elements"]:
            if element["type"] != "line":
                assert element["left"] >= 0, element["id"]
                assert element["top"] >= 0, element["id"]
                assert element["left"] + element["width"] <= 1000, element["id"]
                assert element["top"] + element["height"] <= 562.5, element["id"]
            if element.get("textType") in {"item", "content"}:
                assert element.get("minimumFontSize", 0) >= 16, element["id"]
                assert min(float(size) for size in re.findall(r"font-size:\s*([\d.]+)px", element["content"])) >= 16
            if element.get("imageType") == "decoration":
                assert not element.get("groupId") or element["groupId"] not in content_groups


def test_template_24_image_decoration_does_not_cover_business_slot(tmp_path: Path) -> None:
    """透明边饰只能位于图片槽外侧，不能用不透明方形纹理覆盖业务照片。"""
    page = next(s for s in _run_builder(tmp_path / "image.json")["slides"] if s["id"] == "content-image-1")
    slot_index = next(i for i, e in enumerate(page["elements"]) if e.get("imageType") == "content")
    slot = page["elements"][slot_index]
    for decor in page["elements"][slot_index + 1:]:
        if decor.get("imageType") != "decoration":
            continue
        overlap_x = min(slot["left"] + slot["width"], decor["left"] + decor["width"]) - max(slot["left"], decor["left"])
        overlap_y = min(slot["top"] + slot["height"], decor["top"] + decor["height"]) - max(slot["top"], decor["top"])
        assert overlap_x <= 0 or overlap_y <= 0, decor["id"]


def test_template_24_probe_assets_match_contract() -> None:
    template = json.loads((TEMPLATE_ROOT / "template_24.json").read_text(encoding="utf-8"))
    referenced = {
        element["src"].rsplit("/", 1)[-1]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    }
    assert set(template["metadata"]["assetFiles"]) == set(ASSET_CONTRACT)
    assert referenced <= set(ASSET_CONTRACT)
    for filename, (size, mode) in ASSET_CONTRACT.items():
        with Image.open(TEMPLATE_ROOT / filename) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema()[0] == 0


def test_template_24_probe_renderer_preserves_slots_and_decorations(tmp_path: Path) -> None:
    # 探针精确选版只能以三页探针为输入，不能误把生产版双封面的合法选版判作失败。
    _run_builder(tmp_path / "template_24.json", "probe")
    for name in ASSET_CONTRACT:
        shutil.copyfile(TEMPLATE_ROOT / name, tmp_path / name)
    renderer = PresentationTemplateRenderer(tmp_path)

    cover = renderer.render(
        template_id="template_24",
        semantic_slides=[{"type": "cover", "data": {"title": "项目策划探针"}}],
        task_id="template-24-cover",
        fallback_title="项目策划探针",
    )["slides"][0]
    assert cover["templateSlideId"] == "cover-city"

    body = renderer.render(
        template_id="template_24",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "四项正文探针",
                "items": [
                    {"title": f"要点{index}", "text": f"完整正文{index}"}
                    for index in range(1, 5)
                ],
            },
        }],
        task_id="template-24-text",
        fallback_title="四项正文探针",
    )["slides"][0]
    assert body["templateSlideId"] == "content-text-4"
    body_text = "".join(
        _plain_text(element)
        for element in body["elements"]
        if element.get("textType") == "item"
    )
    assert all(f"完整正文{index}" in body_text for index in range(1, 5))

    image_page = renderer.render(
        template_id="template_24",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "单图文探针",
                "items": [{"title": "图片标题", "text": "图片正文"}],
            },
            "images": [{
                "src": "https://example.invalid/probe.jpg",
                "width": 1200,
                "height": 800,
            }],
        }],
        task_id="template-24-image",
        fallback_title="单图文探针",
    )["slides"][0]
    assert image_page["templateSlideId"] == "content-image-1"
    content_images = [
        element
        for element in image_page["elements"]
        if element.get("imageType") == "content"
    ]
    decorations = [
        element
        for element in image_page["elements"]
        if element.get("imageType") == "decoration"
    ]
    assert len(content_images) == 1
    assert content_images[0]["src"].startswith("https://example.invalid/")
    assert decorations
    assert all(element.get("lock") is True for element in decorations)


@pytest.fixture
def production_renderer(tmp_path: Path) -> PresentationTemplateRenderer:
    """生产版测试使用独立模板目录，避免把预览文件当作正式发布文件。"""
    _run_builder(tmp_path / "template_24.json", "production")
    for name in ASSET_CONTRACT:
        shutil.copyfile(TEMPLATE_ROOT / name, tmp_path / name)
    return PresentationTemplateRenderer(tmp_path)


def _render(renderer, kind, data, **extra):
    return renderer.render(template_id="template_24", semantic_slides=[{"type": kind, "data": data, **extra}],
                           task_id="template24-fixed-qa", fallback_title="项目策划")


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10, 11])
def test_template_24_directory_preserves_every_item(production_renderer, count):
    items = [f"章节{index:02d}" for index in range(count)]
    document = _render(production_renderer, "contents", {"items": items})
    actual = [_plain_text(e) for s in document["slides"] for e in s["elements"] if e.get("textType") == "item"]
    assert actual == items
    if count <= 10:
        assert document["slides"][0]["templateSlideId"] == f"contents-{count}"


@pytest.mark.parametrize("count", [1, 2, 3, 4, 8])
def test_template_24_text_preserves_order_and_original_titles(production_renderer, count):
    items = [{"title": f"需要完整保留的项目实施计划和业务说明标题{index:02d}", "text": f"业务正文{index:02d}。"}
             for index in range(count)]
    document = _render(production_renderer, "content", {"title": "实施规划", "items": items})
    bodies = [_plain_text(e) for s in document["slides"] for e in s["elements"] if e.get("textType") == "item"]
    joined = "|".join(bodies)
    for item in items:
        assert item["title"] in joined and item["text"] in joined
    assert [joined.index(i["text"]) for i in items] == sorted(joined.index(i["text"]) for i in items)
    if count == 8:
        assert len(document["slides"]) == 2
        assert all(s["templateSlideId"] == "content-text-4" for s in document["slides"])


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_24_end_action_content(production_renderer, count):
    items = [f"行动{index}：完成对应交付" for index in range(count)]
    document = _render(production_renderer, "end", {"title": "下一步", "items": items})
    assert document["slides"][0]["templateSlideId"] == ("end-city" if count == 0 else "end-action")
    assert [_plain_text(e) for e in document["slides"][0]["elements"] if e.get("textType") == "item"] == items


def test_template_24_metric_values_are_not_replaced_by_serial_numbers(production_renderer):
    items = [{"kind": "metric", "title": f"指标{i}", "value": f"{17*i}%", "text": f"来源说明{i}"} for i in range(1,5)]
    page = _render(production_renderer, "content", {"title": "关键指标", "items": items})["slides"][0]
    assert page["templateSlideId"] == "content-metrics-4"
    assert [_plain_text(e) for e in page["elements"] if e.get("textType") == "itemNumber"] == [i["value"] for i in items]


def test_template_24_transition_variants_follow_existing_renderer(production_renderer):
    """处理器依赖公共章节轮换规则，左右城市布局需覆盖现有变体别名。"""
    slides = [{"type":"transition", "data":{"title":f"章节{i}","text":"完整章节说明"}} for i in range(1,5)]
    document = production_renderer.render(template_id="template_24",semantic_slides=slides,
                                         task_id="template24-sections",fallback_title="章节")
    assert [s["templateSlideId"] for s in document["slides"]] == ["transition-city-left","transition-city-right"] * 2


@pytest.mark.parametrize("size", [(1600,900), (800,1200), (1000,1000)])
def test_template_24_business_image_crop_uses_real_dimensions(production_renderer, size):
    width, height = size
    page = _render(production_renderer, "content", {"title":"图片", "items":[{"title":"图片标题","text":"图片正文"}]},
                   images=[{"src":"https://example.invalid/fixture.jpg","width":width,"height":height}])["slides"][0]
    image = next(e for e in page["elements"] if e.get("imageType") == "content")
    (left,top),(right,bottom) = image["clip"]["range"]
    assert width*(right-left)/(height*(bottom-top)) == pytest.approx(image["width"]/image["height"])
    assert image["originalWidth"] == width and image["originalHeight"] == height


def test_template_24_production_inventory_and_identifiers(tmp_path):
    template = _run_builder(tmp_path / "all.json", "production")
    assert len(_run_builder(tmp_path / "mvp.json", "mvp")["slides"]) == 12
    assert len(template["slides"]) == 18
    assert {kind:sum(s["type"]==kind for s in template["slides"]) for kind in ("cover","contents","transition","content","end")} == {
        "cover":2,"contents":6,"transition":2,"content":6,"end":2}
    ids = [s["id"] for s in template["slides"]] + [e["id"] for s in template["slides"] for e in s["elements"]]
    assert len(ids)==len(set(ids))
    assets = {e["src"].split('/')[-1] for s in template["slides"] for e in s["elements"] if e["type"]=="image"}
    assert assets == set(ASSET_CONTRACT)
    for s in template["slides"]:
        for e in s["elements"]:
            if e.get("imageType") == "decoration":
                assert e.get("lock") and not e.get("groupId")


@pytest.mark.parametrize("images", [
    [{"src":"https://example.invalid/a.jpg"}],
    [{"src":"https://example.invalid/a.jpg","width":100,"height":100}],
])
def test_template_24_invalid_source_dimensions_produce_error(production_renderer, images):
    with pytest.raises(TemplateRenderError) as exc:
        _render(production_renderer,"content",{"title":"业务图片","items":[{"title":"标题","text":"正文"}]},images=images)
    assert exc.value.code == "TEMPLATE_DATA_INVALID"


def test_template_24_missing_resource_is_not_silently_ignored(production_renderer):
    (production_renderer.template_root / "template_24_asset_bg_cover_v1.jpg").unlink()
    with pytest.raises(TemplateRenderError) as exc:
        _render(production_renderer,"cover",{"title":"项目策划"})
    assert exc.value.code == "TEMPLATE_RESOURCE_MISSING"


def test_template_24_missing_metric_value_is_not_fabricated(production_renderer):
    items = [{"kind":"metric","title":f"指标{i}","value":"","text":"说明"} for i in range(4)]
    with pytest.raises(TemplateRenderError) as exc:
        _render(production_renderer,"content",{"title":"指标","items":items})
    assert exc.value.code == "TEMPLATE_DATA_INVALID"


def test_template_24_long_body_is_lossless(production_renderer):
    items = [{"title":f"内容{i}","text":"".join(f"第{i}项句子{j}保留完整。" for j in range(15))} for i in range(4)]
    result = _render(production_renderer,"content",{"title":"详细说明","items":items})
    texts="".join(_plain_text(e) for s in result["slides"] for e in s["elements"] if e.get("textType")=="item")
    for item in items:
        assert item["text"] in texts
    assert [texts.index(i["text"]) for i in items] == sorted(texts.index(i["text"]) for i in items)
