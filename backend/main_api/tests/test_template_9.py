"""AI 霓虹科技模板的结构、容量、图片保护与资源回归测试。"""

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


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "template"
TEMPLATE_PATH = TEMPLATE_ROOT / "template_9.json"


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


def test_template_9_has_complete_production_inventory() -> None:
    """生产模板必须为18页并覆盖五种页面类型。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    counts = {
        slide_type: sum(slide["type"] == slide_type for slide in template["slides"])
        for slide_type in ("cover", "contents", "transition", "content", "end")
    }

    assert template["id"] == "template_9"
    assert template["title"] == "AI 霓虹科技"
    assert (template["width"], template["height"]) == (1000, 562.5)
    assert len(template["slides"]) == 18
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}
    assert len(template["metadata"]["mvpSlideIds"]) == 12
    assert set(template["metadata"]["mvpSlideIds"]) <= {slide["id"] for slide in template["slides"]}


def test_template_9_assets_are_exact_external_and_valid() -> None:
    """所有发布素材必须被引用，且满足尺寸、模式和体积约束。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    sources = [
        element["src"]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
    ]
    referenced = {source.rsplit("/", 1)[-1] for source in sources}
    published = {path.name for path in TEMPLATE_ROOT.glob("template_9_asset_*")}

    assert TEMPLATE_PATH.stat().st_size < 1_000_000
    assert sources and all(source.startswith("/api/data/") for source in sources)
    assert all(not source.startswith("data:") for source in sources)
    assert published == referenced

    expected = {
        "template_9_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 350_000),
        "template_9_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_9_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 300_000),
        "template_9_asset_orb_cluster_v1.png": ((1600, 800), "RGBA", 1_000_000),
        "template_9_asset_neon_ribbon_v1.png": ((1800, 600), "RGBA", 1_000_000),
        "template_9_asset_particles_v1.png": ((1920, 1080), "RGBA", 1_000_000),
        "template_9_asset_corner_circuit_v1.png": ((1200, 1200), "RGBA", 1_000_000),
        "template_9_asset_ai_core_v1.png": ((1600, 1200), "RGBA", 1_500_000),
    }
    assert published == set(expected)
    for filename, (size, mode, limit) in expected.items():
        path = TEMPLATE_ROOT / filename
        image = Image.open(path)
        assert image.size == size
        assert image.mode == mode
        assert path.stat().st_size <= limit
        if mode == "RGBA":
            low, high = image.getchannel("A").getextrema()
            assert low == 0 and high > 0


def test_template_9_ids_samples_and_paths_are_clean() -> None:
    """ID必须唯一，生产模板不能残留参考稿示例或本机路径。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)

    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    for forbidden in (
        "请在此处", "Add Your", "THANK YOU", "三极极黑简体", "C:\\Users\\",
        "data:image", ".codex-tmp", ".codex_tmp",
    ):
        assert forbidden not in serialized


def test_template_9_main_api_registration_and_cover_route() -> None:
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
        "RELEASE_COMMIT": "template-9-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_9.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_9']; "
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
        "target": [{"name": "AI 霓虹科技", "id": "template_9", "cover": "/api/data/template_9.jpg"}],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_9.jpg").stat().st_size,
    }


def test_template_9_respects_typography_minimums() -> None:
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
def test_template_9_selects_exact_contents_capacity(count: int) -> None:
    """目录必须按输入数量选择精确槽位。"""
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{"type": "contents", "data": {"items": [f"议题 {i}" for i in range(1, count + 1)]}}],
        task_id=f"template-9-contents-{count}",
        fallback_title="目录",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert sum(_slot_type(element) == "itemNumber" for element in slide["elements"]) == count


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_template_9_selects_exact_text_capacity(count: int) -> None:
    """无配图内容必须选择纯文字版式。"""
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{"type": "content", "data": {"title": "核心观点", "items": _semantic_items(count)}}],
        task_id=f"template-9-text-{count}",
        fallback_title="核心观点",
    )
    slide = document["slides"][0]
    assert sum(_slot_type(element) == "item" for element in slide["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in slide["elements"])


@pytest.mark.parametrize("image_count", [0, 1, 2])
def test_template_9_fills_only_content_images(image_count: int) -> None:
    """Agent图片只能替换内容槽，装饰必须保持项目地址。"""
    sources = [f"https://example.invalid/content-{i}.jpg" for i in range(image_count)]
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文说明", "items": _semantic_items(max(1, image_count))},
            "images": [
                {"src": source, "alt": f"内容图 {i + 1}", "width": 1600, "height": 900}
                for i, source in enumerate(sources)
            ],
        }],
        task_id=f"template-9-images-{image_count}",
        fallback_title="图文说明",
    )
    images = [element for element in document["slides"][0]["elements"] if element.get("type") == "image"]
    content = [element for element in images if element.get("imageType") == "content"]
    decorations = [element for element in images if element.get("imageType") == "decoration"]
    assert [element["src"] for element in content] == sources
    assert decorations
    assert all(element["src"].startswith("/api/data/template_9_asset_") for element in decorations)


def test_template_9_rejects_more_images_than_content_items() -> None:
    """图片多于正文项时无法建立语义对应，必须显式失败。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_9",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量边界", "items": _semantic_items(1)},
                "images": [
                    {"src": f"https://example.invalid/{index}.jpg", "width": 800, "height": 1200}
                    for index in range(2)
                ],
            }],
            task_id="template-9-too-many-images",
            fallback_title="图片数量边界",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


@pytest.mark.parametrize(("item_count", "image_count"), [(2, 1), (3, 1), (3, 3)])
def test_template_9_paginates_image_and_text_items_without_loss(
    item_count: int, image_count: int
) -> None:
    """图片少于正文项或超过单页容量时，必须分页保留全部图片和正文。"""
    items = _semantic_items(item_count)
    sources = [f"https://example.invalid/{index}.jpg" for index in range(image_count)]
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文分页", "items": items},
            "images": [
                {"src": source, "width": 800, "height": 1200}
                for source in sources
            ],
        }],
        task_id=f"template-9-image-pagination-{item_count}-{image_count}",
        fallback_title="图文分页",
    )
    rendered = json.dumps(document, ensure_ascii=False)
    content_sources = [
        element["src"]
        for slide in document["slides"]
        for element in slide["elements"]
        if element.get("type") == "image" and element.get("imageType") == "content"
    ]
    assert content_sources == sources
    assert all(item["text"] in rendered for item in items)
    assert "/api/data/template_9_asset_bg_cover_v1.jpg" not in content_sources


def test_template_9_content_image_uses_center_crop_without_distortion() -> None:
    """竖图进入横向内容框时，裁剪区域比例必须与容器一致。"""
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "裁剪验证", "items": _semantic_items(1)},
            "images": [{"src": "https://example.invalid/portrait.jpg", "width": 800, "height": 1200}],
        }],
        task_id="template-9-image-crop",
        fallback_title="裁剪验证",
    )
    image = next(
        element for element in document["slides"][0]["elements"]
        if element.get("type") == "image" and element.get("imageType") == "content"
    )
    start, end = image["clip"]["range"]
    cropped_width = 800 * (end[0] - start[0]) / 100
    cropped_height = 1200 * (end[1] - start[1]) / 100
    assert image["clip"]["shape"] == "rect"
    assert cropped_width / cropped_height == pytest.approx(image["width"] / image["height"], rel=0.01)


def test_template_9_ultrawide_image_uses_horizontal_center_crop() -> None:
    """超宽图进入内容框时必须左右对称裁剪，覆盖横向裁剪分支。"""
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "横向裁剪", "items": _semantic_items(1)},
            "images": [{"src": "https://example.invalid/ultrawide.jpg", "width": 4000, "height": 500}],
        }],
        task_id="template-9-ultrawide-crop",
        fallback_title="横向裁剪",
    )
    image = next(
        element for element in document["slides"][0]["elements"]
        if element.get("type") == "image" and element.get("imageType") == "content"
    )
    start, end = image["clip"]["range"]
    cropped_width = 4000 * (end[0] - start[0]) / 100
    cropped_height = 500 * (end[1] - start[1]) / 100
    assert start[0] == pytest.approx(100 - end[0])
    assert start[1] == pytest.approx(0)
    assert end[1] == pytest.approx(100)
    assert cropped_width / cropped_height == pytest.approx(image["width"] / image["height"], rel=0.01)


def test_template_9_rejects_content_image_without_dimensions() -> None:
    """缺少源图尺寸时无法安全裁剪，必须拒绝而不是拉伸图片。"""
    with pytest.raises(TemplateRenderError) as captured:
        _renderer().render(
            template_id="template_9",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺少尺寸", "items": _semantic_items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-9-image-without-size",
            fallback_title="缺少尺寸",
        )
    assert captured.value.code == "TEMPLATE_DATA_INVALID"


def test_template_9_declared_variants_are_reachable_deterministically() -> None:
    """封面、章节和结束页的两套生产版式都必须可被稳定选择。"""
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    renderer = _renderer()
    for slide_type in ("cover", "transition", "end"):
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


def test_template_9_paginates_eight_items_without_reordering() -> None:
    """8项内容必须无损拆为两页。"""
    items = _semantic_items(8)
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": items}}],
        task_id="template-9-eight-items",
        fallback_title="八项内容",
    )
    rendered = "".join(str(element.get("content", "")) for slide in document["slides"] for element in slide["elements"])
    assert len(document["slides"]) == 2
    assert [rendered.index(item["text"]) for item in items] == sorted(rendered.index(item["text"]) for item in items)


def test_template_9_splits_long_body_without_truncation() -> None:
    """长正文拆分后必须保持全部字符和顺序。"""
    long_text = "复杂信息需要先确定结论，再按层级组织证据和行动。" * 24
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{"type": "content", "data": {"title": "完整说明", "items": [{"title": "核心结论", "text": long_text}]}}],
        task_id="template-9-long-body",
        fallback_title="完整说明",
    )
    parts = [
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        )
    ]
    assert len(document["slides"]) > 1
    assert "".join(parts) == long_text


def test_template_9_splits_long_body_with_image_only_on_first_part() -> None:
    """带图长正文拆页后，图片只出现一次，续页按顺序保留全部字符。"""
    long_text = "先给结论，再展开证据，最后明确行动与责任人。" * 20
    source = "https://example.invalid/long-body.jpg"
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文长正文", "items": [{"title": "核心结论", "text": long_text}]},
            "images": [{"src": source, "width": 1600, "height": 900}],
        }],
        task_id="template-9-long-body-with-image",
        fallback_title="图文长正文",
    )
    image_sources = [
        element["src"]
        for slide in document["slides"]
        for element in slide["elements"]
        if element.get("type") == "image" and element.get("imageType") == "content"
    ]
    parts = [
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        )
    ]
    assert len(document["slides"]) > 1
    assert image_sources == [source]
    assert "".join(parts) == long_text
    assert document["slides"][0]["type"] == "content"
    assert all("（续）" in json.dumps(slide, ensure_ascii=False) for slide in document["slides"][1:])


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_9_accepts_agent_directory_contract(count: int) -> None:
    """每种目录必须容纳14字中英文混排项目。"""
    items = [(f"{number}、AIGC驱动教学创新路径升级")[:14] for number in "一二三四五六七八九十"[:count]]
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{"type": "contents", "data": {"items": items}}],
        task_id=f"template-9-directory-contract-{count}",
        fallback_title="目录",
    )
    rendered = json.dumps(document, ensure_ascii=False)
    assert all(item in rendered for item in items)


def test_template_9_accepts_transition_and_end_boundaries() -> None:
    """章节和结束页必须容纳Agent可能返回的安全长文案。"""
    transition_text = "".join(_exact_text(seed, 23) + "。" for seed in ("本章说明核心变化", "随后回答落地问题", "最终形成行动依据"))
    end_title = _exact_text("感谢观看并欢迎继续交流", 80)
    end_text = _exact_text("围绕本次主题继续讨论实施路径与下一步协作安排", 100)
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[
            {"type": "transition", "data": {"title": "AIGC在教育领域的应用边界", "text": transition_text}},
            {"type": "end", "data": {"title": end_title, "text": end_text}},
        ],
        task_id="template-9-boundaries",
        fallback_title="边界测试",
    )
    rendered = json.dumps(document, ensure_ascii=False)
    assert transition_text in rendered
    assert end_title in rendered and end_text in rendered


@pytest.mark.parametrize("count,body_length", [(1, 90), (2, 90), (3, 60), (4, 45)])
def test_template_9_preserves_body_contract(count: int, body_length: int) -> None:
    """正文达到Agent上限时可以分页，但不能丢字。"""
    bodies = [_exact_text(f"第{i}项围绕业务目标组织证据并明确执行责任", body_length) for i in range(1, count + 1)]
    titles = [_exact_text(f"第{i}项业务能力建设与落地路径", 30) for i in range(1, count + 1)]
    document = _renderer().render(
        template_id="template_9",
        semantic_slides=[{
            "type": "content",
            "data": {"title": _exact_text("人工智能驱动组织转型实践路径", 40), "items": [{"title": title, "text": body} for title, body in zip(titles, bodies, strict=True)]},
        }],
        task_id=f"template-9-body-{count}-{body_length}",
        fallback_title="正文容量契约",
    )
    parts = [
        _plain_html(str(element.get("content", "")))
        for slide in document["slides"]
        for element in sorted(
            [candidate for candidate in slide["elements"] if _slot_type(candidate) == "item"],
            key=lambda candidate: (float(candidate.get("top", 0)), float(candidate.get("left", 0))),
        )
    ]
    assert "".join(parts) == "".join(
        f"{title}。{body}" for title, body in zip(titles, bodies, strict=True)
    )
