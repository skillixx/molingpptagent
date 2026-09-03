"""东方水墨雅韵模板的结构、容量、分页、图片保护与资源回归测试。"""

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
TEMPLATE_PATH = TEMPLATE_ROOT / "template_12.json"


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


def _exact_text(seed: str, length: int) -> str:
    """按指定字符数生成可重复的边界文案。"""
    return (seed * (length // len(seed) + 1))[:length]


def _rendered_item_text(document: dict) -> str:
    """按页面和槽位位置连接正文，用于统一验证分页字符完整性。"""
    parts = [
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (
                float(candidate.get("top", 0)),
                float(candidate.get("left", 0)),
            ),
        )
    ]
    return "".join(parts)


def test_template_12_has_complete_production_inventory() -> None:
    """生产模板必须为18页并覆盖五种页面类型。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    counts = {
        slide_type: sum(slide["type"] == slide_type for slide in template["slides"])
        for slide_type in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_12"
    assert template["title"] == "东方水墨雅韵"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(template["slides"]) == 18
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 7, "end": 1}
    assert set(template["metadata"]["mvpSlideIds"]) == {
        "cover-landscape",
        "contents-2",
        "contents-3",
        "contents-4",
        "contents-5",
        "contents-6",
        "contents-10",
        "transition-seal",
        "content-text-2",
        "content-text-3",
        "content-text-4",
        "end-landscape",
    }


def test_template_12_assets_are_exact_external_and_valid() -> None:
    """八项素材必须全部被引用，并满足尺寸、模式、体积和透明通道要求。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_12_asset_*")}
    expected = {
        "template_12_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 350_000),
        "template_12_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_12_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_12_asset_mountain_band_v1.png": ((1800, 550), "RGBA", 1_000_000),
        "template_12_asset_brush_accent_v1.png": ((1800, 420), "RGBA", 800_000),
        "template_12_asset_folding_fan_v1.png": ((1400, 900), "RGBA", 1_200_000),
        "template_12_asset_ink_circle_v1.png": ((1200, 1200), "RGBA", 1_000_000),
        "template_12_asset_seal_red_v1.png": ((512, 512), "RGBA", 300_000),
    }

    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert sources and all(source.startswith("/api/data/template_12_asset_") for source in sources)
    assert all(not source.startswith("data:") for source in sources)
    assert published == referenced == set(expected)

    for filename, (size, mode, limit) in expected.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


def test_template_12_cover_is_valid() -> None:
    """模板列表封面必须是真实16:9 JPEG。"""
    path = TEMPLATE_ROOT / "template_12.jpg"
    with Image.open(path) as image:
        assert image.size == (960, 540)
        assert image.mode == "RGB"
    assert path.stat().st_size < 350_000


def test_template_12_ids_samples_and_paths_are_clean() -> None:
    """ID必须唯一，生产模板不能残留参考稿示例或本机路径。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)

    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    for forbidden in (
        "Lorem ipsum", "点击加入", "加入标题", "XXX", "XX设计", "C:\\Users\\",
        "data:image", ".codex-tmp", ".codex_tmp", "THANK YOU", "蓝金流体",
    ):
        assert forbidden not in serialized


def test_template_12_main_api_registration_and_cover_route() -> None:
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
        "RELEASE_COMMIT": "template-12-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_12.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_12']; "
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
        "target": [{"name": "东方水墨雅韵", "id": "template_12", "cover": "/api/data/template_12.jpg"}],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_12.jpg").stat().st_size,
    }


def test_template_12_respects_typography_minimums() -> None:
    """封面、页面、项目和正文必须满足可读字号。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    buckets = {"cover": [], "page": [], "itemTitle": [], "body": [], "contents": []}
    for slide in template["slides"]:
        for element in slide["elements"]:
            sizes = [float(value) for value in re.findall(r"font-size:\s*([\d.]+)px", str(element.get("content", "")))]
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


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_12_selects_exact_contents_capacity(count: int) -> None:
    """目录必须按输入数量选择精确槽位。"""
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{"type": "contents", "data": {"items": [f"议题 {i}" for i in range(1, count + 1)]}}],
        task_id=f"template-12-contents-{count}",
        fallback_title="目录",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == count


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_template_12_selects_exact_text_capacity(count: int) -> None:
    """无配图普通内容必须选择对应容量的纯文字版式。"""
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{"type": "content", "data": {"title": "核心观点", "items": _semantic_items(count)}}],
        task_id=f"template-12-text-{count}",
        fallback_title="核心观点",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert sum(_slot_type(element) == "itemTitle" for element in slide["elements"]) == count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == count
    assert slide.get("layoutKind") != "metrics"
    assert not any(element.get("imageType") == "content" for element in slide["elements"])


def test_template_12_reports_missing_content_slots(tmp_path: Path) -> None:
    """内容版式缺少正文槽时必须显式失败，不能静默生成空页。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    for slide in template["slides"]:
        if slide["type"] != "content":
            continue
        slide["elements"] = [
            element for element in slide["elements"]
            if _slot_type(element) not in {"item", "content"}
        ]
    (tmp_path / "template_12.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )
    for asset in TEMPLATE_ROOT.glob("template_12_asset_*"):
        shutil.copy2(asset, tmp_path / asset.name)

    with pytest.raises(TemplateRenderError) as captured:
        PresentationTemplateRenderer(tmp_path).render(
            template_id="template_12",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "必要槽位", "items": _semantic_items(1)},
            }],
            task_id="template-12-missing-slot",
            fallback_title="必要槽位",
        )
    assert captured.value.code == "TEMPLATE_MISSING_SLOT"


def test_template_12_removes_unused_groups_from_larger_layout(tmp_path: Path) -> None:
    """只剩四项候选版式时，渲染两项内容必须完整删除另外两组槽位。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    four_item_slide = next(slide for slide in template["slides"] if slide["id"] == "content-text-4")
    template["slides"] = [four_item_slide]
    template["metadata"]["mvpSlideIds"] = []
    (tmp_path / "template_12.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )
    for asset in TEMPLATE_ROOT.glob("template_12_asset_*"):
        shutil.copy2(asset, tmp_path / asset.name)

    document = PresentationTemplateRenderer(tmp_path).render(
        template_id="template_12",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "两项内容", "items": _semantic_items(2)},
        }],
        task_id="template-12-unused-groups",
        fallback_title="两项内容",
    )
    elements = document["slides"][0]["elements"]
    assert sum(_slot_type(element) == "item" for element in elements) == 2
    assert sum(_slot_type(element) == "itemTitle" for element in elements) == 2
    assert sum(_slot_type(element) == "itemNumber" for element in elements) == 2
    remaining_groups = {
        element.get("groupId")
        for element in elements
        if _slot_type(element) in {"item", "itemTitle", "itemNumber"}
        and element.get("groupId")
    }
    assert len(remaining_groups) == 2


def test_template_12_metrics_selects_metrics_layout() -> None:
    """数字语义必须进入指标页。"""
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "关键指标",
                "items": [
                    {"kind": "metric", "title": "信息识别", "text": "72%"},
                    {"kind": "number", "title": "阅读效率", "text": "84%"},
                    {"kind": "stat", "title": "行动转化", "text": "63%"},
                ],
            },
        }],
        task_id="template-12-metrics",
        fallback_title="关键指标",
    )
    assert document["slides"][0].get("layoutKind") == "metrics"


@pytest.mark.parametrize("image_count", [0, 1])
def test_template_12_fills_only_content_images(image_count: int) -> None:
    """Agent图片只能替换内容槽，装饰必须保持项目地址。"""
    sources = [f"https://example.invalid/content-{index}.jpg" for index in range(image_count)]
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文说明", "items": _semantic_items(1)},
            "images": [
                {"src": source, "alt": "内容图", "width": 1600, "height": 900}
                for source in sources
            ],
        }],
        task_id=f"template-12-images-{image_count}",
        fallback_title="图文说明",
    )
    images = [element for element in document["slides"][0]["elements"] if element.get("type") == "image"]
    content = [element for element in images if element.get("imageType") == "content"]
    decorations = [element for element in images if element.get("imageType") == "decoration"]
    assert [element["src"] for element in content] == sources
    assert all("groupId" not in element for element in content)
    assert decorations
    assert all(element["src"].startswith("/api/data/template_12_asset_") for element in decorations)


def test_template_12_rejects_more_images_than_content_items() -> None:
    """图片多于正文项时必须显式失败。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_12",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量边界", "items": _semantic_items(1)},
                "images": [
                    {"src": f"https://example.invalid/{index}.jpg", "width": 800, "height": 1200}
                    for index in range(2)
                ],
            }],
            task_id="template-12-too-many-images",
            fallback_title="图片数量边界",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


@pytest.mark.parametrize(
    ("width", "height", "label"),
    [(800, 1200, "portrait"), (1600, 900, "landscape"), (1000, 1000, "square")],
)
def test_template_12_content_images_use_center_crop(
    width: int,
    height: int,
    label: str,
) -> None:
    """横图、竖图和方图都必须保持容器比例，不能拉伸。"""
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "多比例裁剪验证", "items": _semantic_items(1)},
            "images": [{"src": f"https://example.invalid/{label}.jpg", "width": width, "height": height}],
        }],
        task_id=f"template-12-image-crop-{label}",
        fallback_title="多比例裁剪验证",
    )
    image = next(
        element for element in document["slides"][0]["elements"]
        if element.get("type") == "image" and element.get("imageType") == "content"
    )
    start, end = image["clip"]["range"]
    cropped_width = width * (end[0] - start[0]) / 100
    cropped_height = height * (end[1] - start[1]) / 100
    assert cropped_width / cropped_height == pytest.approx(image["width"] / image["height"], rel=0.01)


def test_template_12_rejects_content_image_without_dimensions() -> None:
    """缺少源图尺寸时必须拒绝而不是拉伸图片。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_12",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺少尺寸", "items": _semantic_items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-12-image-without-size",
            fallback_title="缺少尺寸",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_12_declared_variants_are_reachable_deterministically() -> None:
    """两套封面和章节版式必须可被稳定选择。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    renderer = _renderer()
    for slide_type in ("cover", "transition"):
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


def test_template_12_paginates_eight_items_without_reordering() -> None:
    """8项内容必须无损拆为两页。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-12-eight-items",
        fallback_title="八项内容",
    )
    rendered = "".join(str(element.get("content", "")) for slide in document["slides"] for element in slide["elements"])
    assert len(document["slides"]) == 2
    assert [rendered.index(item["text"]) for item in items] == sorted(rendered.index(item["text"]) for item in items)


def test_template_12_splits_long_body_without_truncation() -> None:
    """长正文拆分后必须保持全部字符和顺序。"""
    long_text = "从真实问题出发，连接目标、证据、行动与结果。" * 24
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{"type": "content", "data": {"title": "完整说明", "items": [{"title": "实施路径", "text": long_text}]}}],
        task_id="template-12-long-body",
        fallback_title="完整说明",
    )
    assert len(document["slides"]) > 1
    assert _rendered_item_text(document) == long_text


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_12_accepts_agent_directory_contract(count: int) -> None:
    """每种目录必须容纳14字中英文混排项目。"""
    items = [(f"{number}、AIGC驱动表达结构升级")[:14] for number in "一二三四五六七八九十"[:count]]
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{"type": "contents", "data": {"items": items}}],
        task_id=f"template-12-directory-contract-{count}",
        fallback_title="目录",
    )
    rendered = json.dumps(document, ensure_ascii=False)
    assert all(item in rendered for item in items)


@pytest.mark.parametrize("count,body_length", [(1, 90), (2, 90), (3, 60), (4, 45)])
def test_template_12_preserves_body_contract(count: int, body_length: int) -> None:
    """正文达到Agent上限时可以分页，但不能丢字。"""
    bodies = [_exact_text(f"第{index}项围绕目标组织证据并形成行动", body_length) for index in range(1, count + 1)]
    titles = [_exact_text(f"第{index}项表达能力与行动路径", 30) for index in range(1, count + 1)]
    document = _renderer().render(
        template_id="template_12",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": _exact_text("东方水墨信息表达与实施路径", 40),
                "items": [
                    {"title": title, "text": body}
                    for title, body in zip(titles, bodies, strict=True)
                ],
            },
        }],
        task_id=f"template-12-body-{count}-{body_length}",
        fallback_title="正文容量契约",
    )
    assert _rendered_item_text(document) == "".join(
        f"{title}。{body}" for title, body in zip(titles, bodies, strict=True)
    )
