"""使用固定语义数据、隔离 SQLite 验证 template_23 的真实处理链。"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.main_api.models.base import Base
from backend.main_api.models.domain import GenerationTask, Presentation
from backend.main_api.repositories.tasks import TaskLeaseRepository
from backend.main_api.workers.presentation_handler import PresentationGenerationHandler
from backend.main_api.workers.runner import PersistentTaskWorker
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
EVIDENCE_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_23_qa"


class CaptureRepository:
    """捕获处理器作品，不接触生产作品数据库。"""

    def __init__(self) -> None:
        self.slides_json = ""
        self.slide_count = 0
        self.preview_updates = 0

    def persist_progress(
        self,
        _task: Any,
        *,
        slides_json: str,
        slide_count: int,
        **_kwargs: Any,
    ) -> bool:
        self.slides_json = slides_json
        self.slide_count = slide_count
        self.preview_updates += 1
        return True

    def persist(
        self,
        _task: Any,
        *,
        slides_json: str,
        slide_count: int,
        **_kwargs: Any,
    ) -> bool:
        self.slides_json = slides_json
        self.slide_count = slide_count
        return True

    def has_persisted_result(self, _task: Any) -> bool:
        return bool(self.slides_json)


class DeterministicContentWrapper:
    """固定上游数据，真实执行 Worker、处理器和模板渲染器。"""

    def generate(self, **_kwargs: Any):
        slides = [
            {
                "type": "cover",
                "data": {"title": "蓝曜星幕商务汇报", "text": "固定数据真实处理链验收"},
            },
            {
                "type": "contents",
                "data": {"items": ["项目背景", "关键成果", "业务指标", "后续计划"]},
            },
            {
                "type": "transition",
                "data": {"sectionIndex": 1, "partNumber": "01", "title": "关键成果", "text": "聚焦阶段价值。"},
            },
            {
                "type": "content",
                "data": {
                    "title": "本阶段四项成果",
                    "items": [
                        {"title": "统一视觉规范", "text": "固化色板、字体、安全区和图片角色。"},
                        {"title": "完善页面库存", "text": "覆盖五种页面类型和二十个稳定版式。"},
                        {"title": "保留编辑能力", "text": "标题正文可编辑，业务图片可替换。"},
                        {"title": "建立验收证据", "text": "验证保存、导出和重新导入。"},
                    ],
                },
            },
            {
                "type": "content",
                "data": {
                    "title": "三项经营指标",
                    "items": [
                        {"kind": "metric", "title": "页面库存", "value": "20", "text": "稳定版式"},
                        {"kind": "metric", "title": "页面类型", "value": "5", "text": "语义类型"},
                        {"kind": "metric", "title": "素材库存", "value": "9", "text": "原创素材"},
                    ],
                },
            },
            {
                "type": "content",
                "data": {
                    "title": "五项质量指标",
                    "items": [
                        {"kind": "metric", "title": f"质量项{index}", "value": f"{index * 20}%", "text": f"检查{index}"}
                        for index in range(1, 6)
                    ],
                },
            },
            {
                "type": "content",
                "data": {
                    "title": "模板应用示例",
                    "items": [{"title": "统一图片协议", "text": "横竖方图保持裁切与装饰隔离。"}],
                },
                "images": [{"src": "/api/data/pexels-photo-1049302.jpeg", "width": 1200, "height": 800}],
            },
            {
                "type": "end",
                "data": {"title": "感谢观看", "text": "候选模板技术验收", "items": ["确认候选", "进入后续交付"]},
            },
        ]

        async def stream():
            for slide in slides:
                yield {"type": "text", "text": json.dumps(slide, ensure_ascii=False)}

        return stream()


async def run() -> None:
    repository = CaptureRepository()
    handler = PresentationGenerationHandler(
        repository=repository,
        outline_factory=lambda _session_id: (_ for _ in ()).throw(RuntimeError("outline should not be called")),
        content_factory=lambda _session_id: DeterministicContentWrapper(),
        max_document_bytes=10 * 1024 * 1024,
        template_renderer=PresentationTemplateRenderer(TEMPLATE_ROOT),
    )
    outline = """# 蓝曜星幕商务汇报真实生成验收

## 项目背景
- 创建二十页生产模板。
- 保留文字编辑和图片替换能力。

## 关键成果
- 五种页面类型实际生成。
- 内容和顺序完整保留。
"""
    now = datetime.now(UTC).replace(tzinfo=None)
    task_id = "template-23-worker-qa"
    presentation_id = "template-23-worker-presentation"
    task_input = {
        "operation": "generate_presentation",
        "title": "蓝曜星幕商务汇报真实生成验收",
        "content": outline,
        "language": "zh-CN",
        "template_id": "template_23",
        "generate_from_uploaded_file": False,
        "generate_from_web_search": False,
    }

    with tempfile.TemporaryDirectory(prefix="template-23-worker-qa-") as temp_dir:
        engine = create_engine(
            f"sqlite:///{(Path(temp_dir) / 'worker.db').as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 5},
        )
        Base.metadata.create_all(engine)
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory.begin() as db:
            db.add(Presentation(
                id=presentation_id,
                owner_user_id=1,
                title=task_input["title"],
                status="generating",
                slides_json="{}",
                current_version=1,
                slide_count=0,
                created_at=now,
                updated_at=now,
            ))
            db.add(GenerationTask(
                id=task_id,
                presentation_id=presentation_id,
                owner_user_id=1,
                request_id="template-23-worker-request",
                status="pending",
                stage="queued",
                progress=0,
                input_json=json.dumps(task_input, ensure_ascii=False),
                retryable=True,
                attempt=0,
                max_attempts=1,
                next_attempt_at=now,
                created_at=now,
                updated_at=now,
            ))
        worker = PersistentTaskWorker(
            repository=TaskLeaseRepository(engine),
            handler=handler,
            worker_id="template-23-qa-worker",
            lease_seconds=120,
            heartbeat_seconds=10,
            retry_backoff_seconds=10,
            claim_batch_size=1,
            agent_timeout_seconds=180,
        )
        claimed = await worker.run_once()
        with factory() as db:
            task_row = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
            worker_status = task_row.status if task_row else "missing"
            worker_stage = task_row.stage if task_row else "missing"
        engine.dispose()

    if not claimed or worker_status != "succeeded" or not repository.slides_json:
        raise RuntimeError(f"真实 Worker 未成功完成 QA：{worker_status}/{worker_stage}")
    document = json.loads(repository.slides_json)
    slides = document.get("slides", [])
    slide_types = {
        kind: sum(slide.get("type") == kind for slide in slides)
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    if any(count == 0 for count in slide_types.values()):
        raise RuntimeError(f"未覆盖五种页面类型：{slide_types}")
    summary = {
        "schemaVersion": 1,
        "templateId": "template_23",
        "status": "PASS",
        "executionMode": "fixed-upstream-real-handler-renderer-and-persistent-worker",
        "databaseWrites": "isolated-temporary-sqlite-only",
        "productionQueueWrites": False,
        "billingOperations": False,
        "realTextModelCalls": False,
        "realImageModelCalls": False,
        "taskId": task_id,
        "workerClaimed": claimed,
        "workerStatus": worker_status,
        "workerStage": worker_stage,
        "slideCount": len(slides),
        "slideTypes": slide_types,
        "reachedStableLayoutIds": sorted({slide.get("templateSlideId") for slide in slides if slide.get("templateSlideId")}),
        "fixedDecorationCount": sum(
            element.get("imageType") == "decoration"
            for slide in slides for element in slide.get("elements", [])
        ),
        "contentImageCount": sum(
            element.get("imageType") == "content"
            for slide in slides for element in slide.get("elements", [])
        ),
        "previewUpdates": repository.preview_updates,
    }
    if summary["contentImageCount"] < 1 or summary["fixedDecorationCount"] < 1:
        raise RuntimeError("真实处理链未保留业务图片或固定装饰")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "real-handler-document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EVIDENCE_ROOT / "real-handler-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
