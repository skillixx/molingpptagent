"""抽象油彩商务汇报模板的探针、素材、语义和图片协议测试。"""

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
TEMPLATE_PATH = TEMPLATE_ROOT / "template_20.json"
BUILDER_PATH = REPOSITORY_ROOT / "utils" / "build_abstract_oil_business_template.mjs"
ASSET_CONTRACT = {
    "template_20_asset_bg_cover_v1.jpg": ((1920, 1080), "RGB", 450_000),
    "template_20_asset_bg_content_v1.jpg": ((1920, 1080), "RGB", 280_000),
    "template_20_asset_bg_section_v1.jpg": ((1920, 1080), "RGB", 380_000),
    "template_20_asset_bg_end_v1.jpg": ((1920, 1080), "RGB", 420_000),
    "template_20_asset_teal_brush_band_v1.png": ((1800, 520), "RGBA", 900_000),
    "template_20_asset_orange_brush_sweep_v1.png": ((1500, 420), "RGBA", 700_000),
    "template_20_asset_yellow_highlight_v1.png": ((1200, 260), "RGBA", 450_000),
    "template_20_asset_paint_corner_v1.png": ((1200, 900), "RGBA", 850_000),
    "template_20_asset_pigment_speckles_v1.png": ((1600, 900), "RGBA", 650_000),
}
MVP_IDS = {
    "cover-abstract-paint", "contents-2", "contents-3", "contents-4", "contents-5",
    "contents-6", "contents-10", "transition-teal-paint", "content-text-2",
    "content-text-3", "content-text-4", "end-abstract-paint",
}
PRODUCTION_IDS = MVP_IDS | {
    "cover-image", "transition-orange-stroke", "content-statement-1", "content-image-1",
    "content-metrics-4", "end-action",
}


def _renderer() -> PresentationTemplateRenderer:
    return PresentationTemplateRenderer(TEMPLATE_ROOT)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _slot_type(element: dict) -> str | None:
    value = element.get("textType")
    if isinstance(value, str):
        return value
    text_value = element.get("text")
    if isinstance(text_value, dict) and isinstance(text_value.get("type"), str):
        return text_value["type"]
    return None


def _plain_text(element: dict) -> str:
    value = element.get("content")
    if not isinstance(value, str):
        text_value = element.get("text")
        value = text_value.get("content") if isinstance(text_value, dict) else ""
    return unescape(re.sub(r"<[^>]+>", "", value or ""))


def _items(count: int) -> list[dict[str, str]]:
    return [
        {"title": f"完整业务标题第{index}项需要安全展示", "text": f"第{index}项完整说明。"}
        for index in range(1, count + 1)
    ]


def _images(count: int, *, width: int = 1600, height: int = 900) -> list[dict[str, object]]:
    return [
        {"src": f"https://example.invalid/template-20-{index}.jpg", "width": width, "height": height}
        for index in range(1, count + 1)
    ]


def test_template_20_probe_builder_is_deterministic(tmp_path: Path) -> None:
    """同一探针连续构建两次必须得到完全相同的JSON。"""

    outputs = [tmp_path / f"probe-{index}.json" for index in (1, 2)]
    for output in outputs:
        result = subprocess.run(
            ["node", str(BUILDER_PATH), "--stage", "probe", str(output)],
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
    assert first["metadata"]["buildStage"] == "probe"
    assert {slide["id"] for slide in first["slides"]} == {
        "cover-abstract-paint",
        "content-text-4",
        "content-image-1",
    }


def test_template_20_four_item_probe_keeps_four_item_density() -> None:
    """真实长度标题仍应保留四项密度，不能退化成单项页。"""

    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "四项内容", "items": _items(4)},
        }],
        task_id="template-20-probe-four",
        fallback_title="四项内容",
    )["slides"][0]
    assert page["templateSlideId"] == "content-text-4"
    assert sum(element.get("textType") == "itemTitle" for element in page["elements"]) == 4
    assert sum(element.get("textType") == "item" for element in page["elements"]) == 4


@pytest.mark.parametrize(
    ("count", "title", "expected_layout"),
    [
        (3, "业务协同目标管理体系升级", "content-text-3"),
        (4, "业务协同目标管理体系", "content-text-4"),
    ],
)
def test_template_20_accepts_declared_item_title_limits(
    count: int,
    title: str,
    expected_layout: str,
) -> None:
    """三项和四项版式必须容纳公共协议允许的12字和10字标题。"""

    assert len(title) == (12 if count == 3 else 10)
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "标题容量边界",
                "items": [
                    {"title": title, "text": f"第{index}项完整说明。"}
                    for index in range(1, count + 1)
                ],
            },
        }],
        task_id=f"template-20-title-limit-{count}",
        fallback_title="标题容量边界",
    )["slides"][0]

    assert page["templateSlideId"] == expected_layout
    rendered_titles = [
        _plain_text(element)
        for element in page["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    assert rendered_titles == [title] * count


def test_template_20_probe_assets_are_valid() -> None:
    """探针使用的三项原创素材必须满足发布尺寸、模式、Alpha和体积。"""

    for filename, (size, mode, limit) in ASSET_CONTRACT.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image:
            assert image.size == size
            assert image.mode == mode
            if mode == "RGBA":
                assert image.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


@pytest.mark.parametrize(("width", "height"), [(1600, 900), (900, 1600), (1000, 1000)])
def test_template_20_probe_crops_business_images(width: int, height: int) -> None:
    """横图、竖图和方图都进入业务图片槽，固定装饰保持原资源。"""

    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "图文探针", "items": _items(1)},
            "images": _images(1, width=width, height=height),
        }],
        task_id=f"template-20-probe-image-{width}-{height}",
        fallback_title="图文探针",
    )["slides"][0]
    content_image = next(element for element in page["elements"] if element.get("imageType") == "content")
    assert content_image["src"].startswith("https://example.invalid/")
    assert content_image.get("clip", {}).get("shape") == "rect"
    assert (content_image.get("originalWidth"), content_image.get("originalHeight")) == (width, height)
    decorations = [element for element in page["elements"] if element.get("imageType") == "decoration"]
    assert decorations
    assert all(element["src"].startswith("/api/data/template_20_asset_") for element in decorations)


def test_template_20_probe_rejects_missing_image_dimensions() -> None:
    with pytest.raises(TemplateRenderError):
        _renderer().render(
            template_id="template_20",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "缺少尺寸", "items": _items(1)},
                "images": [{"src": "https://example.invalid/no-size.jpg"}],
            }],
            task_id="template-20-probe-missing-size",
            fallback_title="缺少尺寸",
        )


def test_template_20_probe_rejects_extra_images() -> None:
    with pytest.raises(TemplateRenderError, match="图片数量超过内容项数量"):
        _renderer().render(
            template_id="template_20",
            semantic_slides=[{
                "type": "content",
                "data": {"title": "图片数量", "items": _items(1)},
                "images": _images(2),
            }],
            task_id="template-20-probe-extra-images",
            fallback_title="图片数量",
        )


def test_template_20_production_inventory_matches_goal() -> None:
    """生产模板必须精确包含18页，并覆盖规划的五种页面类型。"""

    template = _template()
    counts = {
        kind: sum(slide["type"] == kind for slide in template["slides"])
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    assert template["metadata"]["buildStage"] == "production"
    assert set(template["metadata"]["mvpSlideIds"]) == MVP_IDS
    assert set(template["metadata"]["productionSlideIds"]) == PRODUCTION_IDS
    assert {slide["id"] for slide in template["slides"]} == PRODUCTION_IDS
    assert counts == {"cover": 2, "contents": 6, "transition": 2, "content": 6, "end": 2}
    assert template["paginationGrowthPolicy"] == {"factor": 1.75, "slack": 5}


@pytest.mark.parametrize(
    ("stage", "expected"),
    [("probe", 3), ("sample", 5), ("mvp", 12), ("production", 18)],
)
def test_template_20_all_builder_stages_are_deterministic(
    tmp_path: Path,
    stage: str,
    expected: int,
) -> None:
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
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    assert len(json.loads(outputs[0].read_text(encoding="utf-8"))["slides"]) == expected


def test_template_20_checked_in_production_matches_builder(tmp_path: Path) -> None:
    output = tmp_path / "template_20_production.json"
    result = subprocess.run(
        ["node", str(BUILDER_PATH), "--stage", "production", str(output)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == TEMPLATE_PATH.read_bytes()


def test_template_20_assets_are_exact_external_and_valid() -> None:
    """九项素材必须全部由生产模板引用，并满足尺寸、模式、Alpha和体积契约。"""

    template = _template()
    referenced = {
        element["src"].rsplit("/", 1)[-1]
        for slide in template["slides"]
        for element in slide["elements"]
        if element.get("type") == "image"
        and element.get("imageType") == "decoration"
        and "template_20_asset_" in element.get("src", "")
    }
    published = {path.name for path in TEMPLATE_ROOT.glob("template_20_asset_*")}
    assert referenced == published == set(ASSET_CONTRACT)
    for filename, (size, mode, limit) in ASSET_CONTRACT.items():
        path = TEMPLATE_ROOT / filename
        with Image.open(path) as image_value:
            assert image_value.size == size
            assert image_value.mode == mode
            if mode == "RGBA":
                assert image_value.getchannel("A").getextrema() == (0, 255)
        assert path.stat().st_size <= limit


def test_template_20_ids_paths_fonts_and_rights_are_clean() -> None:
    template = _template()
    slide_ids = [slide["id"] for slide in template["slides"]]
    element_ids = [element["id"] for slide in template["slides"] for element in slide["elements"]]
    serialized = json.dumps(template, ensure_ascii=False)
    assert len(slide_ids) == len(set(slide_ids))
    assert len(element_ids) == len(set(element_ids))
    assert "data:image/" not in serialized and "file://" not in serialized
    assert "animations" not in serialized and '"chart"' not in serialized.lower()
    assert all(slide.get("sourceReferenceSlides") for slide in template["slides"])
    for forbidden in ("Agency FB", "Arial Rounded MT Bold", "Helvetica Light", "思源宋体 CN Heavy"):
        assert forbidden not in serialized


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6, 10])
def test_template_20_selects_exact_contents_capacity(count: int) -> None:
    values = [f"议题 {index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id=f"template-20-contents-{count}",
        fallback_title="目录",
    )["slides"][0]
    assert page["templateSlideId"] == f"contents-{count}"
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "content-statement-1"), (2, "content-text-2"), (3, "content-text-3"), (4, "content-text-4")],
)
def test_template_20_selects_exact_text_capacity(count: int, expected: str) -> None:
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "content", "data": {"title": "核心观点", "items": _items(count)}}],
        task_id=f"template-20-text-{count}",
        fallback_title="核心观点",
    )["slides"][0]
    assert page["templateSlideId"] == expected
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count
    assert not any(element.get("imageType") == "content" for element in page["elements"])


def test_template_20_metrics_and_variants_are_reachable() -> None:
    metrics = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": "四项指标",
                "items": [
                    {"kind": kind, "title": f"指标 {index}", "text": f"{70 + index}%"}
                    for index, kind in enumerate(("metric", "number", "stat", "metric"), 1)
                ],
            },
        }],
        task_id="template-20-metrics",
        fallback_title="四项指标",
    )["slides"][0]
    cover_with_image = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "业务增长", "text": "清晰表达"},
            "images": _images(1),
        }],
        task_id="template-20-cover-image",
        fallback_title="业务增长",
    )["slides"][0]
    transitions = _renderer().render(
        template_id="template_20",
        semantic_slides=[
            {"type": "transition", "data": {"title": "第一章节", "text": "说明一"}},
            {"type": "transition", "data": {"title": "第二章节", "text": "说明二"}},
        ],
        task_id="template-20-transitions",
        fallback_title="章节",
    )["slides"]
    assert metrics["templateSlideId"] == "content-metrics-4"
    assert cover_with_image["templateSlideId"] == "cover-image"
    assert {slide["templateSlideId"] for slide in transitions} == {
        "transition-teal-paint", "transition-orange-stroke"
    }


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_template_20_selects_end_layout_by_action_count(count: int) -> None:
    items = [f"行动 {index}" for index in range(1, count + 1)]
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "end", "data": {"title": "下一步", "items": items}}],
        task_id=f"template-20-end-{count}",
        fallback_title="下一步",
    )["slides"][0]
    assert page["templateSlideId"] == ("end-abstract-paint" if count == 0 else "end-action")
    assert sum(_slot_type(element) == "item" for element in page["elements"]) == count


def test_template_20_paginates_without_losing_item_order() -> None:
    values = _items(8)
    document = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "content", "data": {"title": "八项内容", "items": values}}],
        task_id="template-20-eight-items",
        fallback_title="八项内容",
    )
    rendered = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "itemTitle"
    ]
    assert rendered == [f"核心要点{index:02d}" for index in range(1, 9)]


def test_template_20_preserves_long_titles_in_body_without_reordering() -> None:
    """展示标题缩短时，完整原题必须按原顺序进入正文，不能截断后丢失。"""

    values = _items(4)
    document = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "content", "data": {"title": "四项内容", "items": values}}],
        task_id="template-20-title-preservation",
        fallback_title="四项内容",
    )
    rendered_bodies = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "item"
    ]
    assert len(rendered_bodies) == 4
    for index, body in enumerate(rendered_bodies):
        assert values[index]["title"] in body
        assert values[index]["text"] in body


def test_template_20_paginates_eleven_contents_without_loss() -> None:
    values = [f"议题 {index}" for index in range(1, 12)]
    document = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "contents", "data": {"items": values}}],
        task_id="template-20-contents-eleven",
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


def test_template_20_long_body_is_split_without_loss() -> None:
    body = "抽象油彩正文必须完整保留观点、依据、执行方法和后续行动。" * 18
    document = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {"title": "长正文", "items": [{"title": "完整说明", "text": body}]},
        }],
        task_id="template-20-long-body",
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


def test_template_20_long_four_item_page_keeps_a_renderable_continuation_title() -> None:
    """四项正文拆出续页时，不得因“（续）”触发标题框二次换行而失败。"""

    title = "业务协同目标管理体系"
    assert len(title) == 10
    body = "完整正文需要保留全部信息并在必要时无损拆分。" * 12
    document = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "content",
            "data": {
                "title": title,
                "items": [
                    {"title": "关键行动一", "text": body},
                    {"title": "关键行动二", "text": "第二项完整说明。"},
                    {"title": "关键行动三", "text": "第三项完整说明。"},
                    {"title": "关键行动四", "text": "第四项完整说明。"},
                ],
            },
        }],
        task_id="template-20-continuation-title",
        fallback_title=title,
    )

    assert len(document["slides"]) > 1
    rendered_titles = [
        _plain_text(element)
        for slide in document["slides"]
        for element in slide["elements"]
        if _slot_type(element) == "title"
    ]
    assert rendered_titles == [title] * len(document["slides"])


@pytest.mark.parametrize(
    ("variant", "expected_layout"),
    [
        ("horizon", "transition-teal-paint"),
        ("particle", "transition-teal-paint"),
        ("spectrum", "transition-orange-stroke"),
        ("stage", "transition-orange-stroke"),
    ],
)
def test_template_20_maps_all_agent_transition_variants(
    variant: str,
    expected_layout: str,
) -> None:
    """正文 Agent 的四种章节变体必须都能映射到模板 20 的两个视觉版式。"""

    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "transition",
            "data": {"title": "章节目标", "text": "章节说明", "variant": variant},
        }],
        task_id=f"template-20-transition-{variant}",
        fallback_title="章节目标",
    )["slides"][0]

    assert page["templateSlideId"] == expected_layout


def test_template_20_rejects_more_than_three_end_actions() -> None:
    with pytest.raises(TemplateRenderError, match="不能超过 3 项"):
        _renderer().render(
            template_id="template_20",
            semantic_slides=[{
                "type": "end",
                "data": {"title": "下一步", "items": [f"行动 {index}" for index in range(4)]},
            }],
            task_id="template-20-end-too-many",
            fallback_title="下一步",
        )


def test_template_20_cover_accepts_real_worker_title() -> None:
    """真实 Content Agent 返回的15字封面标题必须在50px最小字号下完整显示。"""

    title = "抽象油彩商务汇报真实生成验收稿"
    assert len(title) == 15
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{"type": "cover", "data": {"title": title, "text": "冻结候选版本验收"}}],
        task_id="template-20-real-cover-title",
        fallback_title=title,
    )["slides"][0]
    rendered = [
        _plain_text(element)
        for element in page["elements"]
        if _slot_type(element) == "title"
    ]
    assert rendered == [title]


def test_template_20_cover_accepts_real_worker_subtitle_capacity() -> None:
    """生产日志中的35字封面副标题必须在声明的最小字号下完整显示。"""

    subtitle = "业务增长" * 8 + "成果稳"
    assert len(subtitle) == 35
    page = _renderer().render(
        template_id="template_20",
        semantic_slides=[{
            "type": "cover",
            "data": {"title": "抽象油彩商务汇报", "text": subtitle},
        }],
        task_id="template-20-real-cover-subtitle",
        fallback_title="抽象油彩商务汇报",
    )["slides"][0]
    rendered = [
        _plain_text(element)
        for element in page["elements"]
        if _slot_type(element) == "content"
    ]
    assert rendered == [subtitle]


def test_template_20_cover_and_registration_are_valid() -> None:
    cover = TEMPLATE_ROOT / "template_20.jpg"
    with Image.open(cover) as image_value:
        assert image_value.size == (960, 540)
        assert image_value.mode == "RGB"
        assert image_value.format == "JPEG"
    assert cover.stat().st_size < 250_000
    main_source = (TEMPLATE_ROOT.parent / "main.py").read_text(encoding="utf-8")
    assert main_source.count('{ "name": "抽象油彩商务汇报", "id": "template_20"') == 1


def test_template_20_main_api_registration_and_cover_route() -> None:
    """隔离测试环境必须能唯一列出模板，并通过资源接口返回选择器封面。"""

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
        "RELEASE_COMMIT": "template-20-test",
    })
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; client=TestClient(main.app); "
                "templates=client.get('/templates'); cover=client.get('/data/template_20.jpg'); "
                "items=templates.json()['data']; target=[item for item in items if item['id']=='template_20']; "
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
            "name": "抽象油彩商务汇报",
            "id": "template_20",
            "cover": "/api/data/template_20.jpg",
        }],
        "unique": True,
        "cover_status": 200,
        "cover_type": "image/jpeg",
        "cover_bytes": (TEMPLATE_ROOT / "template_20.jpg").stat().st_size,
    }
