"""生成覆盖 template_18 全部关键版式的可重复 QA 文档。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
OUTPUT = REPOSITORY_ROOT / "doc" / "assets" / "template_18_qa" / "e2e-document.json"


def items(count: int) -> list[dict[str, str]]:
    return [
        {
            "title": f"标题 {index}",
            "text": f"第 {index} 项完整说明。",
        }
        for index in range(1, count + 1)
    ]


semantic_slides = [
    {"type": "cover", "data": {"title": "飞檐雅韵项目验收", "text": "让东方意境承载清晰表达"}},
    {"type": "contents", "data": {"items": ["项目回顾", "关键洞察", "实施路径", "下一步行动"]}},
    {"type": "transition", "data": {"title": "项目回顾", "text": "从目标、过程与结果三个层次复盘。"}},
    {"type": "content", "data": {"title": "核心结论", "items": items(1)}},
    {
        "type": "content",
        "data": {"title": "单图文验证", "items": items(1)},
        "images": [{
            "src": "/api/data/template_18_asset_bg_section_v1.jpg",
            "width": 1920,
            "height": 1080,
            "alt": "古建内容图",
        }],
    },
    {"type": "content", "data": {"title": "双项内容", "items": items(2)}},
    {"type": "content", "data": {"title": "三项内容", "items": items(3)}},
    {"type": "content", "data": {"title": "四项内容", "items": items(4)}},
    {
        "type": "content",
        "data": {
            "title": "四项指标",
            "items": [
                {"kind": "metric", "title": "完成率", "text": "92%"},
                {"kind": "number", "title": "覆盖率", "text": "86%"},
                {"kind": "stat", "title": "满意度", "text": "95%"},
                {"kind": "metric", "title": "行动项", "text": "12"},
            ],
        },
    },
    {"type": "transition", "data": {"title": "实施路径", "text": "把核心洞察转化为可执行步骤。"}},
    {"type": "end", "data": {"title": "下一步行动", "items": ["确认目标", "明确负责人", "约定复盘"]}},
]


document = PresentationTemplateRenderer(TEMPLATE_ROOT).render(
    template_id="template_18",
    semantic_slides=semantic_slides,
    task_id="template-18-controlled-e2e",
    fallback_title="飞檐雅韵项目验收",
)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "output": str(OUTPUT),
    "slides": len(document["slides"]),
    "templateSlideIds": [slide.get("templateSlideId") for slide in document["slides"]],
}, ensure_ascii=False))
