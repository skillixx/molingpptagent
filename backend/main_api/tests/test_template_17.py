"""蓝菱商务汇报模板的结构、容量、图片保护与资源回归测试。"""

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
TEMPLATE_PATH = TEMPLATE_ROOT / "template_17.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_blue_diamond_business_template.mjs"

MVP_IDS = {
    "cover-diamond",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-banner",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "end-diamond",
}

PRODUCTION_IDS = MVP_IDS | {
    "cover-image",
    "transition-side",
    "content-focus-1",
    "content-image-1",
    "content-image-2",
    "end-action",
}

ASSET_CONTRACT = {
    "template_17_asset_bg_light_v1.jpg": ((1920, 1080), "RGB", 350_000),
    "template_17_asset_world_map_dots_v1.png": ((1600, 900), "RGBA", 650_000),
    "template_17_asset_cover_diamond_cluster_v1.png": ((1400, 1000), "RGBA", 1_000_000),
    "template_17_asset_diamond_footer_v1.png": ((1600, 520), "RGBA", 900_000),
    "template_17_asset_diamond_corner_v1.png": ((900, 900), "RGBA", 700_000),
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
        {"src": f"https://example.invalid/content-{index}.jpg", "width": width, "height": height}
        for index in range(1, count + 1)
    ]


def _render_content(count: int, *, image_count: int = 0) -> dict:
    semantic: dict[str, object] = {
        "type": "content",
        "data": {"title": "蓝菱商务关键洞察", "items": _items(count)},
    }
    if image_count:
        semantic["images"] = _images(image_count)
    return _renderer().render(
        template_id="template_17",
        semantic_slides=[semantic],
        task_id=f"template-17-{count}-{image_count}",
        fallback_title="蓝菱商务洞察",
    )


def test_template_17_inventory_matches_goal() -> None:
    """生产版必须为 18 页，MVP 必须精确包含 12 个稳定 ID。"""
    template = _template()
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_17"
    assert template["title"] == "蓝菱商务汇报"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert template["metadata"]["buildStage"] == "production"
    assert set(template["metadata"]["mvpSlideIds"]) == MVP_IDS
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}


@pytest.mark.parametrize(("stage", "expected"), [("mvp", 12), ("production", 18)])
def test_template_17_builder_is_deterministic(tmp_path: Path, stage: str, expected: int) -> None:
    """构建器必须稳定生成 MVP 与生产库存。"""
    first = tmp_path / f"template_17_{stage}.json"
    second = tmp_path / f"template_17_{stage}_second.json"
    for output in (first, second):
        result = subprocess.run(
            ["node", str(BUILDER_PATH), "--stage", stage, str(output)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    first_value = json.loads(first.read_text(encoding="utf-8"))
    second_value = json.loads(second.read_text(encoding="utf-8"))
    assert first_value == second_value
    assert len(first_value["slides"]) == expected
    assert first_value["metadata"]["buildStage"] == stage


def test_template_17_assets_are_external_and_valid() -> None:
    """五项素材必须全部被引用并满足尺寸、模式、Alpha 与体积契约。"""
    template = _template()
    sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image" and element.get("imageType") == "decoration"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources if "template_17_asset_" in source}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_17_asset_*")}

    assert published == referenced == set(ASSET_CONTRACT)
    for filename, (size, mode, limit) in ASSET_CONTRACT.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


def test_template_17_cover_and_registration_are_valid() -> None:
    """模板选择器必须只注册一次，并使用有效的 16:9 JPEG 封面。"""
    cover = TEMPLATE_ROOT / "template_17.jpg"
    with Image.open(cover) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
        assert image.format == "JPEG"
    assert cover.stat().st_size < 150_000

    main_source = (TEMPLATE_ROOT.parent / "main.py").read_text(encoding="utf-8")
    assert main_source.count('{ "name": "蓝菱商务汇报", "id": "template_17"') == 1


def test_template_17_main_api_registration_and_cover_route() -> None:
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
        "RELEASE_COMMIT": "template-17-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_17.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_17']; "
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
            "name": "蓝菱商务汇报",
            "id": "template_17",
            "cover": "/api/data/template_17.jpg",
        }],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_17.jpg").stat().st_size,
    }


def test_template_17_ids_fonts_paths_and_samples_are_clean() -> None:
    """ID、字体、资源命名空间和示例文字必须满足生产要求。"""
    template = _template()
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)

    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    assert "data:image/" not in serialized and "file://" not in serialized
    assert "template_14_asset_" not in serialized and "template_16_asset_" not in serialized
    for forbidden in ("方正兰亭", "华文黑体", "201X", "Apple", "二维码", "MacBook"):
        assert forbidden not in serialized
    for slide in template["slides"]:
        assert "animations" not in slide
        assert "chart" not in json.dumps(slide, ensure_ascii=False).lower()
        for element in slide["elements"]:
            slot = _slot_type(element)
            if slot in {"title", "content", "item", "itemTitle"}:
                assert element.get("minimumFontSize", 0) >= (16 if slot != "title" else 35)


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_17_selects_exact_contents_capacity(count: int) -> None:
    """目录必须按输入数量选择精确槽位。"""
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "contents", "data": {"items": [f"议题 {index}" for index in range(count)]}}],
        task_id=f"template-17-contents-{count}",
        fallback_title="目录",
    )
    page = document["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


def test_template_17_paginates_non_exact_contents_without_loss() -> None:
    """超过最大十项版式时必须分页，并保持目录顺序和字符完整。"""
    values = [f"议题 {index}" for index in range(1, 12)]
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id="template-17-contents-eleven",
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


@pytest.mark.parametrize(("count", "expected"), [(1, "content-focus-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")])
def test_template_17_selects_exact_text_capacity(count: int, expected: str) -> None:
    document = _render_content(count)
    page = document["slides"][0]
    assert page["templateSlideId"] == expected
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in page["elements"])


@pytest.mark.parametrize(("count", "expected"), [(1, "content-image-1"), (2, "content-image-2")])
def test_template_17_fills_only_content_image_slots(count: int, expected: str) -> None:
    document = _render_content(count, image_count=count)
    page = document["slides"][0]
    assert page["templateSlideId"] == expected
    content_images = [element for element in page["elements"] if element.get("imageType") == "content"]
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    item_groups = {
        element.get("groupId")
        for element in page["elements"]
        if _slot_type(element) in {"itemTitle", "item"} and element.get("groupId")
    }
    assert len(content_images) == count
    assert all(element["src"].startswith("https://example.invalid/") for element in content_images)
    assert all(element.get("groupId") for element in content_images)
    assert {element["groupId"] for element in content_images} == item_groups
    assert all((element.get("originalWidth"), element.get("originalHeight")) == (1600, 900) for element in content_images)
    assert decorations and all(element["src"].startswith("/api/data/template_17_asset_") for element in decorations)


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_17_crops_horizontal_vertical_and_square_images(width: int, height: int) -> None:
    semantic = {"type": "content", "data": {"title": "图片裁切", "items": _items(1)}, "images": _images(1, width=width, height=height)}
    page = _renderer().render(
        template_id="template_17",
        semantic_slides=[semantic],
        task_id=f"template-17-crop-{width}-{height}",
        fallback_title="图片裁切",
    )["slides"][0]
    image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert image["src"].startswith("https://example.invalid/")
    assert image.get("clip")


def test_template_17_rejects_missing_image_dimensions() -> None:
    semantic = {
        "type": "content",
        "data": {"title": "缺失尺寸", "items": _items(1)},
        "images": [{"src": "https://example.invalid/no-size.jpg"}],
    }
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_17",
            semantic_slides=[semantic],
            task_id="template-17-missing-size",
            fallback_title="缺失尺寸",
        )


def test_template_17_rejects_more_images_than_items() -> None:
    """内容图片不能脱离内容项单独进入模板。"""
    semantic = {
        "type": "content",
        "data": {"title": "图片数量错误", "items": _items(1)},
        "images": _images(2),
    }
    with pytest.raises(TemplateRenderError, match="图片数量超过内容项数量"):
        _renderer().render(
            template_id="template_17",
            semantic_slides=[semantic],
            task_id="template-17-too-many-images",
            fallback_title="图片数量错误",
        )


def test_template_17_rejects_unknown_explicit_layout() -> None:
    """调用方指定不存在的显式版式时必须显式失败，不能静默回退。"""
    semantic = {
        "type": "content",
        "data": {"title": "显式版式错误", "items": _items(1), "layoutKind": "not-supported"},
    }
    with pytest.raises(TemplateRenderError, match="显式内容版式"):
        _renderer().render(
            template_id="template_17",
            semantic_slides=[semantic],
            task_id="template-17-invalid-layout",
            fallback_title="显式版式错误",
        )


def test_template_17_paginates_eight_items_without_reordering() -> None:
    values = _items(8)
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": values}}],
        task_id="template-17-eight-items",
        fallback_title="八项内容",
    )
    rendered = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    assert rendered == [item["title"] for item in values]


def test_template_17_long_body_is_split_without_loss() -> None:
    body = "蓝菱商务内容必须完整保留。" * 20
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "content", "data": {"title": "长正文", "items": _items(1, body=body)}}],
        task_id="template-17-long-body",
        fallback_title="长正文",
    )
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert rendered == body
    assert len(document["slides"]) > 1


def test_template_17_long_body_keeps_image_only_on_first_segment() -> None:
    """带图长正文分页后，业务图只留在首段，续页不得残留内容图占位。"""
    body = "带图正文必须完整分页并保护装饰。" * 18
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "带图长正文", "items": _items(1, body=body)},
            "images": _images(1),
        }],
        task_id="template-17-long-body-image",
        fallback_title="带图长正文",
    )
    content_images = [
        [element for element in slide["elements"] if element.get("imageType") == "content"]
        for slide in document["slides"]
    ]
    rendered = "".join(
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    )
    assert rendered == body
    assert len(document["slides"]) > 1
    assert len(content_images[0]) == 1
    assert all(not images for images in content_images[1:])


def test_template_17_transition_variants_are_both_reachable() -> None:
    semantic = [
        {"type": "transition", "data": {"title": "第一章节", "text": "说明一"}},
        {"type": "transition", "data": {"title": "第二章节", "text": "说明二"}},
    ]
    document = _renderer().render(
        template_id="template_17",
        semantic_slides=semantic,
        task_id="template-17-transitions",
        fallback_title="章节",
    )
    assert {slide["templateSlideId"] for slide in document["slides"]} == {
        "transition-banner",
        "transition-side",
    }


def test_template_17_cover_variants_select_by_image_presence() -> None:
    without_image = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "cover", "data": {"title": "年度经营复盘", "text": "让行动更清晰"}}],
        task_id="template-17-cover-no-image",
        fallback_title="年度经营复盘",
    )["slides"][0]
    with_image = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "cover", "data": {"title": "年度经营复盘", "text": "让行动更清晰"}, "images": _images(1)}],
        task_id="template-17-cover-image",
        fallback_title="年度经营复盘",
    )["slides"][0]
    assert without_image["templateSlideId"] == "cover-diamond"
    assert with_image["templateSlideId"] == "cover-image"


def test_template_17_rejects_cover_with_multiple_images() -> None:
    """封面只允许零图或单图，不能静默丢弃额外业务图片。"""
    with pytest.raises(TemplateRenderError, match="封面图片版式"):
        _renderer().render(
            template_id="template_17",
            semantic_slides=[{
                "type": "cover",
                "data": {"title": "多图封面", "text": "应显式失败"},
                "images": _images(2),
            }],
            task_id="template-17-cover-too-many-images",
            fallback_title="多图封面",
        )


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_17_selects_end_layout_by_action_count(count: int) -> None:
    """结束页按行动项数量选择标准页或行动页，并删除未使用分组。"""
    items = [f"行动 {index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_17",
        semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": items}}],
        task_id=f"template-17-end-{count}",
        fallback_title="下一步",
    )["slides"][0]
    assert page["templateSlideId"] == ("end-diamond" if count == 0 else "end-action")
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


def test_template_17_rejects_more_than_three_end_actions() -> None:
    """行动结束页最多容纳三项，超量必须给出明确错误。"""
    with pytest.raises(TemplateRenderError, match="不能超过 3 项"):
        _renderer().render(
            template_id="template_17",
            semantic_slides=[{
                "type": "end",
                "data": {"title": "下一步", "items": [f"行动 {index}" for index in range(4)]},
            }],
            task_id="template-17-end-too-many",
            fallback_title="下一步",
        )
