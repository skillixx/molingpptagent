"""使用固定语义数据、隔离 SQLite 验证 template_29 的真实处理链。"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
EVIDENCE_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_29_qa"


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
        # 固定上游响应，不调用文本模型；真实执行任务租约、处理器和模板渲染。
        slides = json.loads((EVIDENCE_ROOT / 'semantic-input.json').read_text(encoding='utf-8'))

        async def stream():
            for slide in slides:
                yield {"type": "text", "text": json.dumps(slide, ensure_ascii=False)}

        return stream()


async def run() -> None:
    # 先使旧成功摘要失效，避免失败重跑被归档程序错误当成通过。
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / 'real-handler-summary.json').write_text(json.dumps({'status': 'RUNNING'}), encoding='utf-8')
    # 所有可失败的外部依赖在状态失效后再加载。
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from backend.main_api.models.base import Base
    from backend.main_api.models.domain import GenerationTask, Presentation
    from backend.main_api.repositories.tasks import TaskLeaseRepository
    from backend.main_api.workers.presentation_handler import PresentationGenerationHandler
    from backend.main_api.workers.runner import PersistentTaskWorker
    from backend.main_api.workers.template_renderer import PresentationTemplateRenderer
    repository = CaptureRepository()
    handler = PresentationGenerationHandler(
        repository=repository,
        outline_factory=lambda _session_id: (_ for _ in ()).throw(RuntimeError("outline should not be called")),
        content_factory=lambda _session_id: DeterministicContentWrapper(),
        max_document_bytes=10 * 1024 * 1024,
        template_renderer=PresentationTemplateRenderer(TEMPLATE_ROOT),
    )
    outline = """# 乐章雅韵清新商务固定数据验证真实生成验收

## 项目背景
- 创建十八页生产模板。
- 保留文字编辑和图片替换能力。

## 关键成果
- 五种页面类型实际生成。
- 内容和顺序完整保留。
"""
    now = datetime.now(UTC).replace(tzinfo=None)
    task_id = "template-29-worker-qa"
    presentation_id = "template-29-worker-presentation"
    task_input = {
        "operation": "generate_presentation",
        "title": "乐章雅韵清新商务固定数据验证真实生成验收",
        "content": outline,
        "language": "zh-CN",
        "template_id": "template_29",
        "generate_from_uploaded_file": False,
        "generate_from_web_search": False,
    }

    with tempfile.TemporaryDirectory(prefix="template-29-worker-qa-") as temp_dir:
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
                request_id="template-29-worker-request",
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
            worker_id="template-29-qa-worker",
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
    expected_ids = json.loads((TEMPLATE_ROOT / 'template_29.json').read_text(encoding='utf-8'))['metadata']['productionSlideIds']
    if [slide.get('templateSlideId') for slide in slides] != expected_ids:
        raise RuntimeError('实际 Worker 输出没有按顺序覆盖全部 18 个版式')
    slide_types = {
        kind: sum(slide.get("type") == kind for slide in slides)
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    if any(count == 0 for count in slide_types.values()):
        raise RuntimeError(f"未覆盖五种页面类型：{slide_types}")
    summary = {
        "schemaVersion": 1,
        "templateId": "template_29",
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
