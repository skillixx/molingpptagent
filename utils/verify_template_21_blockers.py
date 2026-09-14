"""用固定语义数据构建验收样本；不连接数据库、Agent 或模型服务。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


def main():
    output = Path(sys.argv[1]).resolve()
    # 只写调用方明确给出的私有验收目录，避免覆盖旧冻结证据。
    output.mkdir(parents=True, exist_ok=True)
    metrics = [{"kind": "metric", "title": title, "value": value, "text": description} for title, value, description in [
        ("收入增长", "12.5%", "本季度收入保持稳定增长"), ("新增客户", "1,234", "新增客户规模稳步扩大"),
        ("客户流失", "0", "重点客户均已完成续约"), ("单位成本", "-8%", "单位交付成本持续下降"),
    ]]
    actions = ["明确负责人并确认交付时间", "复核指标口径并跟进执行", "汇总结果并安排下一次复盘"]
    semantic = [
        {"type": "cover", "data": {"title": "业务汇报", "text": "固定数据验收样本"}},
        {"type": "contents", "data": {"items": ["业务概览", "关键指标", "实施计划", "下一步行动"]}},
        {"type": "transition", "data": {"title": "业务概览", "text": "以完整信息支持业务决策"}},
        {"type": "content", "data": {"title": "四项业务重点", "items": [{"title": f"业务重点{i}", "text": "保留原始标题与正文信息，确保所有项目按顺序展示。"} for i in range(1, 5)]}},
        {"type": "content", "data": {"title": "关键业务指标", "layoutKind": "metrics", "items": metrics}},
        {"type": "content", "data": {"title": "图文说明", "items": [{"title": "业务图片", "text": "图片可替换，固定装饰不受影响"}]}, "images": [{"src": "/api/data/template_21_asset_marble_tile_blue_v1.jpg", "width": 1200, "height": 1200}]},
        {"type": "end", "data": {"title": "下一步行动", "text": "请各团队按计划执行", "items": actions}},
        {"type": "end", "data": {"title": "感谢观看", "text": "期待下次交流"}},
    ]
    document = PresentationTemplateRenderer(ROOT / "backend/main_api/template").render(
        template_id="template_21", semantic_slides=semantic, task_id="fixed-blocker-qa", fallback_title="业务汇报",
    )
    assert len(document["slides"]) == 8
    assert document["slides"][4]["templateSlideId"] == "content-metrics-4"
    assert document["slides"][6]["templateSlideId"] == "end-action"
    (output / "document.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "expected.json").write_text(json.dumps([m["value"] for m in metrics] + actions, ensure_ascii=False), encoding="utf-8")
    print("PASS: 8 fixed pages, metrics and action layout reached; no external calls")


if __name__ == "__main__":
    main()
