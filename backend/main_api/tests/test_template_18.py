"""飞檐雅韵模板的库存、素材、语义、分页和图片协议测试。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_18.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_eaves_elegance_template.mjs"

MVP_IDS = {
    "cover-rooftile",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-rose-band",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "end-rooftile",
}

PRODUCTION_IDS = MVP_IDS | {
    "cover-eaves",
    "transition-medallion",
    "content-statement-1",
    "content-image-1",
    "content-metrics-4",
    "end-action",
}

ASSET_CONTRACT = {
    "template_18_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 400_000),
    "template_18_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 320_000),
    "template_18_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 400_000),
    "template_18_asset_rooftile_band_v1.png": ((1800, 620), "RGBA", 1_000_000),
    "template_18_asset_eaves_corner_v1.png": ((1200, 900), "RGBA", 900_000),
    "template_18_asset_plum_branch_v1.png": ((1600, 650), "RGBA", 850_000),
    "template_18_asset_crane_pair_v1.png": ((1100, 700), "RGBA", 750_000),
    "template_18_asset_medallion_v1.png": ((900, 900), "RGBA", 600_000),
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


def _items(count: int, *, body: str | None = None, kind: str | None = None) -> list[dict[str, str]]:
    values = []
    for index in range(1, count + 1):
        item = {
            "title": f"要点 {index}",
            "text": body or f"第 {index} 项完整说明。",
        }
        if kind:
            item["kind"] = kind
        values.append(item)
    return values


def _images(count: int, *, width: int = 1600, height: int = 900) -> list[dict[str, object]]:
    return [
        {
            "src": f"https://example.invalid/content-{index}.jpg",
            "width": width,
            "height": height,
        }
        for index in range(1, count + 1)
    ]


def _render_content(count: int, *, image_count: int = 0, layout_kind: str | None = None) -> dict:
    data: dict[str, object] = {"title": "飞檐雅韵关键洞察", "items": _items(count)}
    if layout_kind:
        data["layoutKind"] = layout_kind
    semantic: dict[str, object] = {"type": "content", "data": data}
    if image_count:
        semantic["images"] = _images(image_count)
    return _renderer().render(
        template_id="template_18",
        semantic_slides=[semantic],
        task_id=f"template-18-{count}-{image_count}-{layout_kind}",
        fallback_title="飞檐雅韵洞察",
    )


def test_template_18_inventory_matches_goal() -> None:
    """生产版必须为18页，并精确覆盖规划中的五种页面类型。"""

    template = _template()
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    assert template["id"] == "template_18"
    assert template["title"] == "飞檐雅韵"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert template["metadata"]["buildStage"] == "production"
    assert set(template["metadata"]["mvpSlideIds"]) == MVP_IDS
    assert set(template["metadata"]["productionSlideIds"]) == PRODUCTION_IDS
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}


@pytest.mark.parametrize(("stage", "expected"), [("sample", 5), ("mvp", 12), ("production", 18)])
def test_template_18_builder_is_deterministic(tmp_path: Path, stage: str, expected: int) -> None:
    """样稿、MVP和生产版构建必须稳定。"""

    outputs = [tmp_path / f"{stage}-{index}.json" for index in (1, 2)]
    for output in outputs:
        result = subprocess.run(
            ["node", str(BUILDER_PATH), "--stage", stage, str(output)],
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
    assert len(first["slides"]) == expected
    assert first["metadata"]["buildStage"] == stage


def test_template_18_assets_are_exact_external_and_valid() -> None:
    """八项发布素材必须全部被引用，并满足尺寸、模式、Alpha和体积契约。"""

    template = _template()
    sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image" and element.get("imageType") == "decoration"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources if "template_18_asset_" in source}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_18_asset_*")}
    assert referenced == published == set(ASSET_CONTRACT)
    for filename, (size, mode, limit) in ASSET_CONTRACT.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


def test_template_18_cover_and_registration_are_valid() -> None:
    """模板选择器封面必须有效，注册项必须唯一。"""

    cover = TEMPLATE_ROOT / "template_18.jpg"
    with Image.open(cover) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
        assert image.format == "JPEG"
    assert cover.stat().st_size < 150_000
    main_source = (TEMPLATE_ROOT.parent / "main.py").read_text(encoding="utf-8")
    assert main_source.count('{ "name": "飞檐雅韵", "id": "template_18"') == 1


def test_template_18_main_api_registration_and_cover_route() -> None:
    """隔离主应用必须公开唯一模板项和有效封面。"""

    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    environment.update({
        "APP_ENV": "test",
        "PERSISTENCE_ENABLED": "false",
        "SSO_ENABLED": "false",
        "BILLING_ENABLED": "false",
        "STORAGE_ENABLED": "false",
        "TASK_WORKER_ENABLED": "false",
        "RELEASE_CHANNEL": "test",
        "RELEASE_COMMIT": "template-18-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_18.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_18']; "
                "print(json.dumps({'templates_status':templates.status_code,'target':target,"
                "'unique':len({item['id'] for item in items})==len(items),"
                "'cover_status':cover.status_code,'cover_type':cover.headers.get('content-type'),"
                "'cover_bytes':len(cover.content)}))"
            ),
        ],
        cwd=REPOSITORY_ROOT / "backend/main_api",
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {
        "templates_status": 200,
        "target": [{
            "name": "飞檐雅韵",
            "id": "template_18",
            "cover": "/api/data/template_18.jpg",
        }],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_18.jpg").stat().st_size,
    }


def test_template_18_ids_fonts_paths_samples_and_rights_are_clean() -> None:
    """生产JSON不得残留源媒体、非商业字体和不安全路径。"""

    template = _template()
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)
    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    assert "data:image/" not in serialized and "file://" not in serialized
    assert "template_12_asset_" not in serialized and "template_17_asset_" not in serialized
    for forbidden in ("包图网", "非商业使用", "文悦古典", "方正清刻", "二维码", "点击输入"):
        assert forbidden not in serialized
    assert "animations" not in serialized
    assert '"chart"' not in serialized.lower()
    for slide in template["slides"]:
        assert slide.get("sourceReferenceSlides")
        assert isinstance(slide.get("sourceFidelity"), dict)
        for element in slide["elements"]:
            slot = _slot_type(element)
            if slot in {"title", "content", "item", "itemTitle"}:
                expected = 35 if slot == "title" else 24 if slot == "itemTitle" else 14
                assert element.get("minimumFontSize", 0) >= expected


def test_template_18_preserves_source_specific_visual_contract() -> None:
    """关键页面必须保留原稿特有构图，而不是退化成泛化中国风。"""

    template = _template()
    by_id = {slide["id"]: slide for slide in template["slides"]}
    cover = by_id["cover-rooftile"]
    assert sum(element.get("type") == "shape" and element.get("path", "").startswith("M 100 0") for element in cover["elements"]) == 5
    assert sum("brand-character" in element["id"] for element in cover["elements"]) == 4
    contents = by_id["contents-4"]
    assert any(element.get("fill") == "#B77D80" and element.get("height") == 562.5 for element in contents["elements"])
    transition = by_id["transition-rose-band"]
    assert any(element.get("src", "").endswith("template_18_asset_medallion_v1.png") for element in transition["elements"])
    assert any(element.get("textType") == "partNumber" and element.get("vertical") is True for element in transition["elements"])
    end = by_id["end-rooftile"]
    assert sum("closing-character" in element["id"] for element in end["elements"]) == 4


@pytest.mark.parametrize(
    ("task_id", "expected_layout"),
    [
        ("template-18-transition-medallion-2", "transition-rose-band"),
        ("template-18-transition-medallion-0", "transition-medallion"),
    ],
)
@pytest.mark.parametrize("title", ["八字章节标题验证", "十字章节标题容量验证", "十二字章节标题自动换行验证", "十四字章节标题自动换行容量验证"])
def test_template_18_transition_layouts_accept_long_chapter_titles(
    task_id: str,
    expected_layout: str,
    title: str,
) -> None:
    """两种章节页都要容纳常见长标题，不能生成两页后因标题容量终止。"""

    page = _renderer().render(
        template_id="template_18",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": title, "text": "承接上一章节并说明下一阶段重点。"},
        }],
        task_id=task_id,
        fallback_title="章节标题",
    )["slides"][0]
    rendered_title = next(
        _plain_text(element)
        for element in page["elements"]
        if _slot_type(element) == "title"
    )
    assert page["templateSlideId"] == expected_layout
    assert rendered_title.replace("\n", "") == title


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_18_selects_exact_contents_capacity(count: int) -> None:
    values = [f"议题 {index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id=f"template-18-contents-{count}",
        fallback_title="目录",
    )["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


def test_template_18_paginates_eleven_contents_without_loss() -> None:
    values = [f"议题 {index}" for index in range(1, 12)]
    document = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id="template-18-contents-eleven",
        fallback_title="目录",
    )
    rendered = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    ]
    assert len(document["slides"]) == 2
    assert rendered == values


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-statement-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_18_selects_exact_text_capacity(count: int, expected: str) -> None:
    page = _render_content(count)["slides"][0]
    assert page["templateSlideId"] == expected
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in page["elements"])


def test_template_18_selects_single_content_image_layout() -> None:
    page = _render_content(1, image_count=1)["slides"][0]
    assert page["templateSlideId"] == "content-image-1"
    content_images = [element for element in page["elements"] if element.get("imageType") == "content"]
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    item_groups = {
        element.get("groupId")
        for element in page["elements"]
        if _slot_type(element) in {"itemTitle", "item"} and element.get("groupId")
    }
    assert len(content_images) == 1
    assert content_images[0]["src"].startswith("https://example.invalid/")
    assert content_images[0].get("groupId") in item_groups
    assert content_images[0].get("width") == content_images[0].get("height")
    assert content_images[0].get("clip", {}).get("shape") == "ellipse"
    assert decorations and all(element["src"].startswith("/api/data/template_18_asset_") for element in decorations)


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_18_crops_horizontal_vertical_and_square_images(width: int, height: int) -> None:
    semantic = {
        "type": "content",
        "data": {"title": "图片裁切", "items": _items(1)},
        "images": _images(1, width=width, height=height),
    }
    page = _renderer().render(
        template_id="template_18",
        semantic_slides=[semantic],
        task_id=f"template-18-crop-{width}-{height}",
        fallback_title="图片裁切",
    )["slides"][0]
    image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert image.get("clip")
    assert image["clip"]["shape"] == "ellipse"
    assert (image.get("originalWidth"), image.get("originalHeight")) == (width, height)


def test_template_18_rejects_missing_image_dimensions() -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_18",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺失尺寸", "items": _items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-18-missing-size",
            fallback_title="缺失尺寸",
        )


def test_template_18_rejects_more_images_than_items() -> None:
    with pytest.raises(TemplateRenderError, match="图片数量超过内容项数量"):
        _renderer().render(
            template_id="template_18",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量错误", "items": _items(1)},
                "images": _images(2),
            }],
            task_id="template-18-too-many-images",
            fallback_title="图片数量错误",
        )


def test_template_18_metrics_selects_metrics_layout() -> None:
    page = _renderer().render(
        template_id="template_18",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "四项指标",
                "items": [
                    {"kind": kind, "title": f"指标 {index}", "text": f"{index * 20}%"}
                    for index, kind in enumerate(("metric", "number", "stat", "metric"), 1)
                ],
            },
        }],
        task_id="template-18-metrics",
        fallback_title="四项指标",
    )["slides"][0]
    assert page["templateSlideId"] == "content-metrics-4"
    assert page.get("layoutKind") == "metrics"
    assert not any(element.get("type") == "chart" for element in page["elements"])


def test_template_18_paginates_eight_items_without_reordering() -> None:
    values = _items(8)
    document = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": values}}],
        task_id="template-18-eight-items",
        fallback_title="八项内容",
    )
    rendered = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    assert rendered == [item["title"] for item in values]


def test_template_18_long_body_is_split_without_loss() -> None:
    body = "飞檐雅韵正文必须完整保留并保持顺序。" * 120
    document = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "content", "data": {"title": "长正文", "items": _items(1, body=body)}}],
        task_id="template-18-long-body",
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


def test_template_18_transition_variants_are_both_reachable() -> None:
    document = _renderer().render(
        template_id="template_18",
        semantic_slides=[
            {"type": "transition", "data": {"title": "第一章节", "text": "说明一"}},
            {"type": "transition", "data": {"title": "第二章节", "text": "说明二"}},
        ],
        task_id="template-18-transitions",
        fallback_title="章节",
    )
    assert {slide["templateSlideId"] for slide in document["slides"]} == {
        "transition-rose-band",
        "transition-medallion",
    }


def test_template_18_cover_variants_select_by_image_presence() -> None:
    without_image = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "cover", "data": {"title": "东方古建", "text": "清晰表达"}}],
        task_id="template-18-cover-no-image",
        fallback_title="东方古建",
    )["slides"][0]
    with_image = _renderer().render(
        template_id="template_18",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "东方古建", "text": "清晰表达"},
            "images": _images(1),
        }],
        task_id="template-18-cover-image",
        fallback_title="东方古建",
    )["slides"][0]
    assert without_image["templateSlideId"] == "cover-rooftile"
    assert with_image["templateSlideId"] == "cover-eaves"


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_18_selects_end_layout_by_action_count(count: int) -> None:
    items = [f"行动 {index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_18",
        semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": items}}],
        task_id=f"template-18-end-{count}",
        fallback_title="下一步",
    )["slides"][0]
    assert page["templateSlideId"] == ("end-rooftile" if count == 0 else "end-action")
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


def test_template_18_rejects_more_than_three_end_actions() -> None:
    with pytest.raises(TemplateRenderError, match="不能超过 3 项"):
        _renderer().render(
            template_id="template_18",
            semantic_slides=[{
                "type": "end",
                "data": {"title": "下一步", "items": [f"行动 {index}" for index in range(4)]},
            }],
            task_id="template-18-end-too-many",
            fallback_title="下一步",
        )


def test_template_18_does_not_require_importer_fix() -> None:
    """模板主线必须能够在不修改通用PPTX导入器的情况下构建和渲染。"""

    result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", "mvp", str(REPOSITORY_ROOT / ".codex-tmp" / "template-18-mvp-test.json")],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
