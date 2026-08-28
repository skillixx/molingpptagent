"""灰蓝企业宣传模板的结构、容量、分页、图片保护与资源回归测试。"""

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
TEMPLATE_PATH = TEMPLATE_ROOT / "template_13.json"


def _renderer() -> PresentationTemplateRenderer:
    """返回使用生产模板目录的真实渲染器。"""
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _slot_type(element: dict) -> str | None:
    """兼容文本和带文字形状的语义槽位。"""
    value = element.get("textType")
    if isinstance(value, str):
        return value
    text = element.get("text")
    if isinstance(text, dict) and isinstance(text.get("type"), str):
        return text["type"]
    return None


def _plain_html(value: str) -> str:
    """提取纯文本，用于验证分页没有丢字。"""
    return unescape(re.sub(r"<[^>]+>", "", value))


def _semantic_items(count: int) -> list[dict[str, str]]:
    """生成稳定的普通内容项。"""
    return [
        {"title": f"要点 {index}", "text": f"第 {index} 项的完整说明。"}
        for index in range(1, count + 1)
    ]


def _rendered_item_text(document: dict) -> str:
    """按页面顺序连接正文，用于验证拆页后的字符完整性。"""
    return "".join(
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (
                float(candidate.get("top", 0)),
                float(candidate.get("left", 0)),
            ),
        )
    )


def test_template_13_has_expected_inventory() -> None:
    """生产模板必须为18页，并精确覆盖规划中的五类页面。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    counts = {
        slide_type: sum(slide["type"] == slide_type for slide in template["slides"])
        for slide_type in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_13"
    assert template["title"] == "灰蓝企业宣传"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(template["slides"]) == 18
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}
    assert set(template["metadata"]["mvpSlideIds"]) == {
        "cover-architectural",
        "contents-2",
        "contents-3",
        "contents-4",
        "contents-5",
        "contents-6",
        "contents-10",
        "transition-facet",
        "content-text-2",
        "content-text-3",
        "content-text-4",
        "end-corporate",
    }


def test_template_13_assets_are_external_and_valid() -> None:
    """六项素材必须全部被引用，并满足尺寸、模式和体积约束。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_13_asset_*")}
    expected = {
        "template_13_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 350_000),
        "template_13_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_13_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_13_asset_facet_ribbon_v1.png": ((1400, 900), "RGBA", 1_000_000),
        "template_13_asset_arch_line_v1.png": ((1400, 900), "RGBA", 1_000_000),
        "template_13_asset_paper_grain_v1.png": ((1400, 900), "RGBA", 800_000),
    }

    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert sources and all(source.startswith("/api/data/template_13_asset_") for source in sources)
    assert published == referenced == set(expected)
    for filename, (size, mode, limit) in expected.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                low, high = image.getchannel("A").getextrema()
                assert low == 0 and high > 0
        assert path.stat().st_size <= limit


def test_template_13_cover_is_valid() -> None:
    """模板列表封面必须是真实16:9 JPEG。"""
    path = TEMPLATE_ROOT / "template_13.jpg"
    with Image.open(path) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
    assert path.stat().st_size < 350_000


def test_template_13_main_api_registration_and_cover_route() -> None:
    """真实主应用必须公开唯一模板注册项和有效封面资源。"""
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
        "RELEASE_COMMIT": "template-13-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_13.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_13']; "
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
            "name": "灰蓝企业宣传",
            "id": "template_13",
            "cover": "/api/data/template_13.jpg",
        }],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_13.jpg").stat().st_size,
    }


def test_template_13_ids_fonts_and_paths_are_clean() -> None:
    """ID必须唯一，模板不得残留参考示例、旧模板资源或本机路径。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)

    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    for forbidden in (
        "template_12_asset_", "东方水墨", "Lorem ipsum", "点击添加", "XXX",
        "C:\\Users\\", "data:image", ".codex-tmp", ".codex_tmp",
        "方正兰亭黑简体", "华文黑体",
    ):
        assert forbidden not in serialized


def test_template_13_respects_typography_minimums() -> None:
    """封面、页面、项目和正文必须满足可读字号。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    buckets = {"cover": [], "page": [], "itemTitle": [], "body": [], "contents": []}
    for slide in template["slides"]:
        for element in slide["elements"]:
            html = str(element.get("content", ""))
            sizes = [float(value) for value in re.findall(r"font-size:\s*([\d.]+)px", html)]
            if not sizes:
                continue
            size = min(sizes)
            slot = _slot_type(element)
            if slide["type"] == "cover" and slot == "title":
                buckets["cover"].append(size)
            elif slot == "title":
                buckets["page"].append(size)
            elif slot == "itemTitle":
                buckets["itemTitle"].append(size)
            elif slot in {"item", "content"}:
                buckets["body"].append(size)
            if slide["type"] == "contents" and slot == "item":
                buckets["contents"].append(size)

    assert min(buckets["cover"]) >= 50
    assert min(buckets["page"]) >= 35
    assert min(buckets["itemTitle"]) >= 24
    assert min(buckets["body"]) >= 16
    assert min(buckets["contents"]) >= 16


def test_template_13_builder_is_reproducible(tmp_path: Path) -> None:
    """构建脚本重复运行必须生成等价模板数据。"""
    node = shutil.which("node")
    assert node is not None
    repository_root = Path(__file__).resolve().parents[3]
    output = tmp_path / "template_13.json"
    result = subprocess.run(
        [
            node,
            str(repository_root / "utils/build_grayblue_corporate_template.mjs"),
            str(TEMPLATE_ROOT / "template_12.json"),
            str(output),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        TEMPLATE_PATH.read_text(encoding="utf-8")
    )


def test_template_13_builder_requires_input_and_output_paths() -> None:
    """构建脚本缺少必需参数时必须显示用法并返回失败。"""
    node = shutil.which("node")
    assert node is not None
    repository_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [node, str(repository_root / "utils/build_grayblue_corporate_template.mjs")],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    # Windows 子进程可能按本地代码页解码中文，使用稳定的 ASCII 片段验证用法提示。
    assert "build_grayblue_corporate_template.mjs" in result.stderr


def test_template_13_builder_rejects_invalid_source_json(tmp_path: Path) -> None:
    """源模板不是有效JSON时必须非零退出，不能生成半成品。"""
    node = shutil.which("node")
    assert node is not None
    repository_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "invalid.json"
    source.write_text("{invalid", encoding="utf-8")
    output = tmp_path / "template_13.json"
    result = subprocess.run(
        [
            node,
            str(repository_root / "utils/build_grayblue_corporate_template.mjs"),
            str(source),
            str(output),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0
    assert not output.exists()


def test_template_13_image_layouts_use_strict_protocol() -> None:
    """单图文和双图文页面必须要求图片与正文数量精确匹配。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    for slide_id, expected_count in (("content-image-1", 1), ("content-image-2", 2)):
        slide = next(slide for slide in template["slides"] if slide["id"] == slide_id)
        content_images = [
            element for element in slide["elements"]
            if element.get("type") == "image" and element.get("imageType") == "content"
        ]
        assert len(content_images) == expected_count
        assert all(element.get("strictImageCount") is True for element in content_images)
        assert all(element.get("requireSourceDimensions") is True for element in content_images)


def test_template_13_cover_and_end_have_safe_text_zones() -> None:
    """第二封面标题保持单行空间，结束页使用高对比安全底板。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    cover = next(slide for slide in template["slides"] if slide["id"] == "cover-light-image")
    cover_title = next(element for element in cover["elements"] if _slot_type(element) == "title")
    assert cover_title["width"] >= 600
    assert cover_title["height"] <= 110

    for slide_id in ("end-corporate", "end-contact"):
        slide = next(slide for slide in template["slides"] if slide["id"] == slide_id)
        panels = [
            element for element in slide["elements"]
            if element.get("type") == "shape" and "end-safe-panel" in element.get("id", "")
        ]
        assert len(panels) == 1
        assert panels[0]["width"] >= 760
        title = next(element for element in slide["elements"] if _slot_type(element) == "title")
        assert title["top"] >= 180


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_13_selects_exact_contents_capacity(count: int) -> None:
    """目录必须按输入数量选择精确槽位。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{
            "type": "contents",
            "data": {"items": [f"议题 {index}" for index in range(1, count + 1)]},
        }],
        task_id=f"template-13-contents-{count}",
        fallback_title="目录",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == count


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_template_13_selects_exact_text_capacity(count: int) -> None:
    """无配图普通内容必须选择对应容量的纯文字页面。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "核心观点", "items": _semantic_items(count)},
        }],
        task_id=f"template-13-text-{count}",
        fallback_title="核心观点",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in slide["elements"])


@pytest.mark.parametrize("image_count", [1, 2])
def test_template_13_selects_exact_image_layout(image_count: int) -> None:
    """一张和两张图片必须选择精确的图文页面。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文说明", "items": _semantic_items(image_count)},
            "images": [
                {
                    "src": f"https://example.invalid/content-{index}.jpg",
                    "width": 1600,
                    "height": 900,
                }
                for index in range(image_count)
            ],
        }],
        task_id=f"template-13-images-{image_count}",
        fallback_title="图文说明",
    )
    slide = document["slides"][0]
    content = [element for element in slide["elements"] if element.get("imageType") == "content"]
    decorations = [element for element in slide["elements"] if element.get("imageType") == "decoration"]
    assert len(content) == image_count
    assert [element["src"] for element in content] == [
        f"https://example.invalid/content-{index}.jpg" for index in range(image_count)
    ]
    assert decorations and all(
        element["src"].startswith("/api/data/template_13_asset_")
        for element in decorations
    )


def test_template_13_cover_selects_layout_by_image_presence() -> None:
    """无图封面不能泄露占位图，有图封面必须保留用户图片。"""
    without_image = _renderer().render(
        template_id="template_13",
        semantic_slides=[{"type": "cover", "data": {"title": "无图封面"}}],
        task_id="template-13-cover-without-image",
        fallback_title="无图封面",
    )["slides"][0]
    assert not any(element.get("imageType") == "content" for element in without_image["elements"])

    source = "https://example.invalid/cover.jpg"
    with_image = _renderer().render(
        template_id="template_13",
        semantic_slides=[{"type": "cover", "data": {"title": "有图封面"}, "images": [{
            "src": source,
            "width": 1600,
            "height": 900,
        }]}],
        task_id="template-13-cover-with-image",
        fallback_title="有图封面",
    )["slides"][0]
    content = [element for element in with_image["elements"] if element.get("imageType") == "content"]
    assert len(content) == 1
    assert content[0]["src"] == source


def test_template_13_rejects_unmatched_cover_image_count() -> None:
    """显式封面协议没有匹配图片数时必须明确失败。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_13",
            semantic_slides=[{
                "type": "cover",
                "data": {"title": "双图封面"},
                "images": [
                    {
                        "src": f"https://example.invalid/cover-{index}.jpg",
                        "width": 1600,
                        "height": 900,
                    }
                    for index in range(2)
                ],
            }],
            task_id="template-13-cover-two-images",
            fallback_title="双图封面",
        )
    assert captured.value.code == "TEMPLATE_MISSING_SLOT"
    assert captured.value.context == {"image_count": "2"}


@pytest.mark.parametrize(
    ("width", "height"),
    [(1600, 900), (900, 1600), (1000, 1000)],
)
def test_template_13_content_images_preserve_crop_ratio(width: int, height: int) -> None:
    """横图、竖图和方图都必须中心裁切到内容框比例。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "裁切验证", "items": _semantic_items(1)},
            "images": [{
                "src": f"https://example.invalid/{width}x{height}.jpg",
                "width": width,
                "height": height,
            }],
        }],
        task_id=f"template-13-crop-{width}-{height}",
        fallback_title="裁切验证",
    )
    image = next(
        element for element in document["slides"][0]["elements"]
        if element.get("imageType") == "content"
    )
    start, end = image["clip"]["range"]
    cropped_width = width * (end[0] - start[0]) / 100
    cropped_height = height * (end[1] - start[1]) / 100
    assert cropped_width / cropped_height == pytest.approx(
        image["width"] / image["height"], rel=0.01
    )


def test_template_13_rejects_content_image_without_dimensions() -> None:
    """缺少源图尺寸时必须拒绝，而不是拉伸内容图。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_13",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺少尺寸", "items": _semantic_items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-13-image-without-size",
            fallback_title="缺少尺寸",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_13_rejects_more_images_than_content_items() -> None:
    """图片多于正文项时必须明确失败。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_13",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量边界", "items": _semantic_items(1)},
                "images": [
                    {"src": f"https://example.invalid/{index}.jpg", "width": 1600, "height": 900}
                    for index in range(2)
                ],
            }],
            task_id="template-13-too-many-images",
            fallback_title="图片数量边界",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_13_declared_variants_are_reachable() -> None:
    """两套封面、章节和结束页必须可被确定性选择。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    renderer = _renderer()
    cover_candidates = [slide for slide in template["slides"] if slide["type"] == "cover"]
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
    assert selected_covers == {slide["id"] for slide in cover_candidates}

    for slide_type in ("transition", "end"):
        candidates = [slide for slide in template["slides"] if slide["type"] == slide_type]
        selected = {
            renderer._select(
                candidates,
                slide_type,
                {},
                0,
                prefer_images=False,
                image_count=0,
                variant_seed=seed,
            )["id"]
            for seed in (0, 1)
        }
        assert selected == {slide["id"] for slide in candidates}


def test_template_13_paginates_eight_items_without_reordering() -> None:
    """八项内容必须无损拆页。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-13-eight-items",
        fallback_title="八项内容",
    )
    rendered = json.dumps(document, ensure_ascii=False)
    assert len(document["slides"]) == 2
    assert [rendered.index(item["text"]) for item in items] == sorted(
        rendered.index(item["text"]) for item in items
    )


def test_template_13_splits_long_body_without_truncation() -> None:
    """长正文拆分后必须保持全部字符和顺序。"""
    long_text = "从真实问题出发，连接目标、证据、行动与结果。" * 80
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "完整说明", "items": [{"title": "实施路径", "text": long_text}]},
        }],
        task_id="template-13-long-body",
        fallback_title="完整说明",
    )
    assert len(document["slides"]) > 1
    assert _rendered_item_text(document) == long_text


def test_template_13_end_ignores_punctuation_only_title() -> None:
    """Agent返回纯标点结束标题时，应保留模板的可读结束文案。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{"type": "end", "data": {"title": "..."}}],
        task_id="template-13-end-punctuation",
        fallback_title="灰蓝企业宣传",
    )
    title = next(
        element for element in document["slides"][0]["elements"]
        if _slot_type(element) == "title"
    )
    assert "..." not in _plain_html(title["content"])
    assert "让清晰表达推动下一步行动" in _plain_html(title["content"])


def test_template_13_end_ignores_punctuation_only_content() -> None:
    """纯标点结束正文不能覆盖模板默认感谢文案。"""
    document = _renderer().render(
        template_id="template_13",
        semantic_slides=[{"type": "end", "data": {"title": "完成", "text": "..."}}],
        task_id="template-13-end-content-punctuation",
        fallback_title="灰蓝企业宣传",
    )
    content = next(
        element for element in document["slides"][0]["elements"]
        if _slot_type(element) == "content"
    )
    assert "..." not in _plain_html(content["content"])
    assert "感谢" in _plain_html(content["content"])
