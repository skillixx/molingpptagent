"""深蓝青棱商务信息图模板的结构、容量、素材、分页和图片协议回归。"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_14.json"


def _renderer() -> PresentationTemplateRenderer:
    """使用生产模板目录创建全新的 renderer，避免测试间缓存。"""
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict) -> str | None:
    """统一读取文本元素与带文字形状的语义槽类型。"""
    value = element.get("textType")
    if isinstance(value, str):
        return value
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("type"), str):
        return text["type"]
    return None


def _plain_html(value: str) -> str:
    """提取纯文本，用于验证分页字符守恒。"""
    return unescape(re.sub(r"<[^>]+>", "", value))


def _element_text(element: dict) -> str:
    """读取文本元素或带文字形状中的 HTML。"""
    if isinstance(element.get("content"), str):
        return _plain_html(element["content"])
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("content"), str):
        return _plain_html(text["content"])
    return ""


def _semantic_items(count: int, *, body: str | None = None, kind: str | None = None) -> list[dict[str, str]]:
    """生成稳定的测试内容项。"""
    values: list[dict[str, str]] = []
    for index in range(1, count + 1):
        item = {
            "title": f"要点 {index}",
            "text": body if body is not None else f"第 {index} 项的完整说明。",
        }
        if kind is not None:
            item["kind"] = kind
        values.append(item)
    return values


def _content_images(count: int) -> list[dict[str, object]]:
    """构造带真实尺寸的内容图描述。"""
    return [
        {
            "src": f"https://example.invalid/content-{index}.jpg",
            "width": 1600,
            "height": 900,
        }
        for index in range(1, count + 1)
    ]


def _rendered_item_text(document: dict) -> str:
    """按页面和坐标顺序连接 item 文本。"""
    return "".join(
        _element_text(element)
        for page in document["slides"]
        for element in sorted(
            [candidate for candidate in page["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (
                float(candidate.get("top", 0)),
                float(candidate.get("left", 0)),
            ),
        )
    )


def test_template_14_has_expected_inventory() -> None:
    """生产模板必须精确实现规格声明的 36 页库存。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    counts = {
        page_type: sum(page["type"] == page_type for page in template["slides"])
        for page_type in ("cover", "contents", "transition", "content", "end")
    }
    assert template["id"] == "template_14"
    assert template["title"] == "深蓝青棱商务信息图"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(template["slides"]) == 36
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 24, "end": 2}
    assert len(template["metadata"]["mvpSlideIds"]) == 18
    assert set(template["metadata"]["mvpSlideIds"]).issubset({page["id"] for page in template["slides"]})


def test_template_14_assets_are_external_and_valid() -> None:
    """五项素材必须全部被引用并满足规格的确定性属性。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    sources = [
        element["src"]
        for page in template["slides"]
        for element in page["elements"]
        if element.get("type") == "image"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_14_asset_*")}
    expected = {
        "template_14_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 350_000),
        "template_14_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 320_000),
        "template_14_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 320_000),
        "template_14_asset_facet_corner_v1.png": ((1400, 900), "RGBA", 1_000_000),
        "template_14_asset_line_particle_v1.png": ((1400, 900), "RGBA", 800_000),
    }
    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert sources and all(source.startswith("/api/data/template_14_asset_") for source in sources)
    assert published == referenced == set(expected)
    for filename, (size, mode, limit) in expected.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


def test_template_14_cover_is_valid() -> None:
    """模板选择器封面必须是 16:9 RGB JPEG。"""
    path = TEMPLATE_ROOT / "template_14.jpg"
    with Image.open(path) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
        assert image.format == "JPEG"
    assert path.stat().st_size < 220_000


def test_template_14_main_api_registration_and_cover_route() -> None:
    """真实主应用必须公开唯一注册项与有效封面。"""
    repository_root = Path(__file__).resolve().parents[3]
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
        "RELEASE_COMMIT": "template-14-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_14.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_14']; "
                "print(json.dumps({'templates_status':templates.status_code,'target':target,"
                "'unique':len({item['id'] for item in items})==len(items),"
                "'cover_status':cover.status_code,'cover_type':cover.headers.get('content-type'),"
                "'cover_bytes':len(cover.content)}))"
            ),
        ],
        cwd=repository_root / "backend/main_api",
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {
        "templates_status": 200,
        "target": [{
            "name": "深蓝青棱商务信息图",
            "id": "template_14",
            "cover": "/api/data/template_14.jpg",
        }],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_14.jpg").stat().st_size,
    }


def test_template_14_ids_fonts_and_paths_are_clean() -> None:
    """ID、字体、资源命名空间和示例文本必须满足生产要求。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    page_ids = [page["id"] for page in template["slides"]]
    element_ids = [element["id"] for page in template["slides"] for element in page["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)
    assert len(page_ids) == len(set(page_ids))
    assert len(element_ids) == len(set(element_ids))
    for forbidden in (
        "template_13_asset_", "Lorem ipsum", "点击添加", "XXX", "FEI ER SHE JI",
        "C:\\Users\\", "file://", "data:image", ".codex-tmp", ".codex_tmp",
        "方正兰亭刊黑_GBK", "时尚中黑简体", "Nexa Bold", "Agency FB",
    ):
        assert forbidden not in serialized


def test_template_14_respects_typography_minimums() -> None:
    """所有语义文字必须满足规格中的最小字号。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    buckets = {"cover": [], "page": [], "part": [], "itemTitle": [], "metric": [], "body": [], "caption": []}
    for page in template["slides"]:
        for element in page["elements"]:
            html = str(element.get("content", ""))
            sizes = [float(value) for value in re.findall(r"font-size:\s*([\d.]+)px", html)]
            if not sizes:
                continue
            size = min(sizes)
            slot = _slot_type(element)
            if page["type"] == "cover" and slot == "title":
                buckets["cover"].append(size)
            elif slot == "title":
                buckets["page"].append(size)
            elif slot == "partNumber":
                buckets["part"].append(size)
            elif slot == "itemTitle":
                buckets["itemTitle"].append(size)
                if page.get("layoutKind") == "metrics":
                    buckets["metric"].append(size)
            elif slot in {"item", "content"}:
                buckets["body"].append(size)
    assert min(buckets["cover"]) >= 44
    assert min(buckets["page"]) >= 28
    assert min(buckets["part"]) >= 60
    assert min(buckets["itemTitle"]) >= 18
    assert min(buckets["metric"]) >= 24
    assert min(buckets["body"]) >= 16


def test_template_14_builder_is_reproducible(tmp_path: Path) -> None:
    """生产构建脚本重复运行必须生成等价 JSON。"""
    node = shutil.which("node")
    assert node is not None
    repository_root = Path(__file__).resolve().parents[3]
    output = tmp_path / "template_14.json"
    result = subprocess.run(
        [
            node,
            str(repository_root / "utils/build_deepblue_infographic_template.mjs"),
            "--stage",
            "production",
            str(output),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_template_14_builder_requires_output_path() -> None:
    """构建脚本缺少输出路径时必须失败并显示稳定用法。"""
    node = shutil.which("node")
    assert node is not None
    repository_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [node, str(repository_root / "utils/build_deepblue_infographic_template.mjs")],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    assert "build_deepblue_infographic_template.mjs" in result.stderr


def test_template_14_image_layouts_use_strict_protocol() -> None:
    """1 至 6 图版式必须要求图片和正文数量精确匹配。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    for count in range(1, 7):
        page = next(candidate for candidate in template["slides"] if candidate["id"] == f"content-image-{count}")
        content_images = [
            element for element in page["elements"]
            if element.get("type") == "image" and element.get("imageType") == "content"
        ]
        assert len(content_images) == count
        assert all(element.get("strictImageCount") is True for element in content_images)
        assert all(element.get("requireSourceDimensions") is True for element in content_images)
        assert all("groupId" not in element for element in content_images)


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_14_selects_exact_contents_capacity(count: int) -> None:
    """目录必须按输入数量选择精确槽位。"""
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "contents", "data": {"items": [f"议题 {index}" for index in range(1, count + 1)]}}],
        task_id=f"template-14-contents-{count}",
        fallback_title="目录",
    )
    page = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count
    assert sum(_slot_type(element) == "itemNumber" for element in page["elements"]) == count


def test_template_14_paginates_eleven_contents_without_loss() -> None:
    """11 项目录必须拆成 10+1，并连续编号且不丢内容。"""
    values = [f"议题 {index}" for index in range(1, 12)]
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id="template-14-contents-11",
        fallback_title="目录",
    )
    assert len(document["slides"]) == 2
    item_values = [
        _element_text(element)
        for page in document["slides"]
        for element in page["elements"]
        if _slot_type(element) == "item"
    ]
    number_values = [
        _element_text(element)
        for page in document["slides"]
        for element in page["elements"]
        if _slot_type(element) == "itemNumber"
    ]
    assert item_values == values
    assert number_values == [str(index).zfill(2) for index in range(1, 12)]


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_template_14_selects_exact_text_capacity_without_specialty_leak(count: int) -> None:
    """普通无图内容必须精确选版，不能误入显式专项版式。"""
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "content", "data": {"title": "核心观点", "items": _semantic_items(count)}}],
        task_id=f"template-14-text-{count}",
        fallback_title="核心观点",
    )
    page = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in page["elements"])
    assert page.get("layoutKind") in ({"focus"} if count == 1 else {"text"})


@pytest.mark.parametrize(
    ("layout_kind", "count"),
    [
        ("metrics", 3), ("metrics", 4), ("metrics", 5),
        ("process", 4), ("process", 5),
        ("compare", 2), ("compare", 4),
        ("hub-spoke", 5), ("timeline", 4), ("focus", 1),
    ],
)
def test_template_14_specialty_layouts_are_reachable(layout_kind: str, count: int) -> None:
    """无图专项版式必须由显式 layoutKind 或指标语义确定到达。"""
    data: dict[str, object] = {
        "title": "专项版式",
        "items": _semantic_items(count, kind="metric" if layout_kind == "metrics" else None),
    }
    if layout_kind != "metrics":
        data["layoutKind"] = layout_kind
    page = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "content", "data": data}],
        task_id=f"template-14-specialty-{layout_kind}-{count}",
        fallback_title="专项版式",
    )["slides"][0]
    assert page.get("layoutKind") == layout_kind
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


@pytest.mark.parametrize("count", [3, 4, 5, 6])
def test_template_14_gallery_layouts_are_reachable(count: int) -> None:
    """3 至 6 图画廊必须按显式语义和图片数精确到达。"""
    page = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "场景画廊", "layoutKind": "gallery", "items": _semantic_items(count)},
            "images": _content_images(count),
        }],
        task_id=f"template-14-gallery-{count}",
        fallback_title="场景画廊",
    )["slides"][0]
    assert page.get("layoutKind") == "gallery"
    assert sum(element.get("imageType") == "content" for element in page["elements"]) == count


@pytest.mark.parametrize("image_count", [1, 2, 3, 4, 5, 6])
def test_template_14_selects_exact_image_layout(image_count: int) -> None:
    """一至六张图片必须选择精确内容图槽位。"""
    page = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文说明", "items": _semantic_items(image_count)},
            "images": _content_images(image_count),
        }],
        task_id=f"template-14-images-{image_count}",
        fallback_title="图文说明",
    )["slides"][0]
    content = [element for element in page["elements"] if element.get("imageType") == "content"]
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    assert len(content) == image_count
    assert [element["src"] for element in content] == [image["src"] for image in _content_images(image_count)]
    assert decorations and all(element["src"].startswith("/api/data/template_14_asset_") for element in decorations)


def test_template_14_paginates_seven_images_as_six_plus_one() -> None:
    """七张内容图必须无损拆为六图页和单图页。"""
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "七个场景", "items": _semantic_items(7)},
            "images": _content_images(7),
        }],
        task_id="template-14-seven-images",
        fallback_title="七个场景",
    )
    assert len(document["slides"]) == 2
    assert [sum(element.get("imageType") == "content" for element in page["elements"]) for page in document["slides"]] == [6, 1]


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_14_content_images_preserve_crop_ratio(width: int, height: int) -> None:
    """横图、竖图和方图必须按内容框比例中心裁切。"""
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "裁切验证", "items": _semantic_items(1)},
            "images": [{"src": f"https://example.invalid/{width}x{height}.jpg", "width": width, "height": height}],
        }],
        task_id=f"template-14-crop-{width}-{height}",
        fallback_title="裁切验证",
    )
    image = next(element for element in document["slides"][0]["elements"] if element.get("imageType") == "content")
    start, end = image["clip"]["range"]
    cropped_width = width * (end[0] - start[0]) / 100
    cropped_height = height * (end[1] - start[1]) / 100
    assert cropped_width / cropped_height == pytest.approx(image["width"] / image["height"], rel=0.01)


def test_template_14_rejects_content_image_without_dimensions() -> None:
    """缺少源图尺寸时必须拒绝，而不是拉伸。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_14",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺少尺寸", "items": _semantic_items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-14-image-without-size",
            fallback_title="缺少尺寸",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_14_rejects_more_images_than_content_items() -> None:
    """图片多于正文项时必须明确失败。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_14",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量边界", "items": _semantic_items(1)},
                "images": _content_images(2),
            }],
            task_id="template-14-too-many-images",
            fallback_title="图片数量边界",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_14_cover_selects_by_image_presence_and_rejects_two_images() -> None:
    """封面必须按 0/1 图精确选版，并拒绝两张图。"""
    renderer = _renderer()
    without_image = renderer.render(
        template_id="template_14",
        semantic_slides=[{"type": "cover", "data": {"title": "无图封面"}}],
        task_id="template-14-cover-no-image",
        fallback_title="无图封面",
    )["slides"][0]
    assert not any(element.get("imageType") == "content" for element in without_image["elements"])

    with_image = renderer.render(
        template_id="template_14",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "单图封面"},
            "images": _content_images(1),
        }],
        task_id="template-14-cover-one-image",
        fallback_title="单图封面",
    )["slides"][0]
    assert sum(element.get("imageType") == "content" for element in with_image["elements"]) == 1

    with pytest.raises(TemplateRenderError) as captured:
        renderer.render(
            template_id="template_14",
            semantic_slides=[{
                "type": "cover",
                "data": {"title": "双图封面"},
                "images": _content_images(2),
            }],
            task_id="template-14-cover-two-images",
            fallback_title="双图封面",
        )
    assert captured.value.code == "TEMPLATE_MISSING_SLOT"


def test_template_14_paginates_eight_items_without_reordering() -> None:
    """八项正文必须无损拆页且保持顺序。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-14-eight-items",
        fallback_title="八项内容",
    )
    assert len(document["slides"]) == 2
    for item in items:
        assert item["text"] in _rendered_item_text(document)


def test_template_14_splits_long_body_without_truncation() -> None:
    """长正文拆页后连接结果必须与原文一致。"""
    body = "以统一指标连接业务目标、事实证据和下一步动作，" * 18
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{"type": "content", "data": {"title": "长正文", "items": _semantic_items(1, body=body)}}],
        task_id="template-14-long-body",
        fallback_title="长正文",
    )
    rendered = _rendered_item_text(document)
    assert body == rendered
    assert len(document["slides"]) > 1


def test_template_14_long_body_with_image_keeps_image_once() -> None:
    """带图长正文只在首段保留内容图。"""
    body = "围绕同一场景持续补充事实、影响和行动建议，" * 18
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "带图长正文", "items": _semantic_items(1, body=body)},
            "images": _content_images(1),
        }],
        task_id="template-14-long-body-image",
        fallback_title="带图长正文",
    )
    assert _rendered_item_text(document) == body
    assert sum(
        element.get("imageType") == "content"
        for page in document["slides"]
        for element in page["elements"]
    ) == 1


def test_template_14_decorations_survive_content_image_replacement() -> None:
    """内容图替换后固定装饰数量与来源必须保持。"""
    document = _renderer().render(
        template_id="template_14",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "装饰保护", "items": _semantic_items(2)},
            "images": _content_images(2),
        }],
        task_id="template-14-decoration-protection",
        fallback_title="装饰保护",
    )
    page = document["slides"][0]
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    content = [element for element in page["elements"] if element.get("imageType") == "content"]
    assert len(content) == 2
    assert decorations
    assert all(element["src"].startswith("/api/data/template_14_asset_") for element in decorations)


def test_template_14_declared_variants_are_reachable() -> None:
    """封面、章节、结束和普通正文同容量变体必须可确定性到达。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    renderer = _renderer()
    cover_candidates = [page for page in template["slides"] if page["type"] == "cover"]
    selected_covers = {
        renderer._select(
            cover_candidates,
            "cover",
            {},
            0,
            prefer_images=prefer_images,
            image_count=image_count,
            variant_seed=seed,
        )["id"]
        for prefer_images, image_count, seed in ((False, 0, 0), (True, 1, 1))
    }
    assert selected_covers == {page["id"] for page in cover_candidates}

    for page_type in ("transition", "end"):
        candidates = [page for page in template["slides"] if page["type"] == page_type]
        selected = {
            renderer._select(candidates, page_type, {}, 0, prefer_images=False, image_count=0, variant_seed=seed)["id"]
            for seed in range(4)
        }
        assert selected == {page["id"] for page in candidates}

    content_candidates = [page for page in template["slides"] if page["type"] == "content"]
    selected_text_2 = {
        renderer._select(
            content_candidates,
            "content",
            {"items": _semantic_items(2)},
            index,
            prefer_images=False,
            image_count=0,
        )["id"]
        for index in range(4)
    }
    assert {"content-text-2", "content-text-2-alt"}.issubset(selected_text_2)


def test_template_14_cover_and_end_respect_safe_zones() -> None:
    """封面标题与结束页文字必须位于批准安全区内。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    for page_id in ("cover-minimal", "cover-with-image"):
        page = next(candidate for candidate in template["slides"] if candidate["id"] == page_id)
        title = next(element for element in page["elements"] if _slot_type(element) == "title")
        assert title["left"] >= 88
        assert title["left"] + title["width"] <= 760
        assert title["top"] >= 184
        assert title["top"] + title["height"] <= 398
    for page_id in ("end-action", "end-contact"):
        page = next(candidate for candidate in template["slides"] if candidate["id"] == page_id)
        title = next(element for element in page["elements"] if _slot_type(element) == "title")
        content = next(element for element in page["elements"] if _slot_type(element) == "content")
        assert title["top"] >= 180
        assert content["top"] + content["height"] <= 516
