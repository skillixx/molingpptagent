"""调用真实 Content Agent 与生产处理器生成 template_19 QA 作品。"""

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

from backend.main_api.content_client import A2AContentClientWrapper
from backend.main_api.models.base import Base
from backend.main_api.models.domain import GenerationTask, Presentation
from backend.main_api.repositories.tasks import TaskLeaseRepository
from backend.main_api.workers.presentation_handler import PresentationGenerationHandler
from backend.main_api.workers.runner import PersistentTaskWorker, TaskExecution
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


EVIDENCE_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_19_qa"
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"


class CaptureRepository:
    """只捕获处理器输出，不写入生产数据库或用户作品。"""

    def __init__(self) -> None:
        self.slides_json = ""
        self.slide_count = 0
        self.preview_updates = 0

    def persist_progress(
        self,
        _task: TaskExecution,
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
        _task: TaskExecution,
        *,
        slides_json: str,
        slide_count: int,
        **_kwargs: Any,
    ) -> bool:
        self.slides_json = slides_json
        self.slide_count = slide_count
        return True

    def has_persisted_result(self, _task: TaskExecution) -> bool:
        return bool(self.slides_json)


async def run() -> None:
    repository = CaptureRepository()
    handler = PresentationGenerationHandler(
        repository=repository,
        # 输入已经是 Markdown 大纲，正常路径不会调用 Outline Agent。
        outline_factory=lambda _session_id: (_ for _ in ()).throw(
            RuntimeError("outline should not be called")
        ),
        content_factory=lambda session_id: A2AContentClientWrapper(
            session_id=session_id,
            agent_url="http://127.0.0.1:10011",
        ),
        max_document_bytes=10 * 1024 * 1024,
        template_renderer=PresentationTemplateRenderer(TEMPLATE_ROOT),
    )
    outline = """# 水彩绿植轻商务真实生成验收

## 项目回顾

### 核心成果
- 完成统一视觉规范和模板页面库存。
- 建立可编辑文字与可替换业务图片协议。
- 保持水彩植物装饰不被业务图片覆盖。
- 完成导出和重新导入验证。

### 关键洞察
- 模板必须优先保证真实内容容量。
- 多项页面不能因标题偏长退化成单项页面。
- 固定装饰和业务图片必须使用不同语义角色。
- 正式证据只在候选版本冻结后生成。

## 实施路径

### 优先任务
- 先完成三页技术探针并验证公共能力。
- 再生产核心素材和代表性视觉样稿。
- 逐步扩展到十二页MVP和十八页生产版。
- 最后集中执行真实Worker和四视口验收。

### 责任与节奏
- 每阶段自动检查并记录可复核证据。
- 普通失败自动定位、修复和重新验证。
- 重大范围扩展保持为独立任务。
- 最终确认只在自动检测通过后请求。
"""
    task_input = {
        "operation": "generate_presentation",
        "title": "水彩绿植轻商务真实生成验收",
        "content": outline,
        "language": "zh-CN",
        "template_id": "template_19",
        "generate_from_uploaded_file": False,
        "generate_from_web_search": False,
    }
    now = datetime.now(UTC).replace(tzinfo=None)
    task_id = "template-19-worker-qa"
    presentation_id = "template-19-worker-presentation"

    # 临时 SQLite 验证真实租约领取、生产处理器派发和终态，不污染生产队列与计费。
    with tempfile.TemporaryDirectory(prefix="template-19-worker-qa-") as temp_dir:
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
                request_id="template-19-worker-request",
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
            worker_id="template-19-qa-worker",
            lease_seconds=120,
            heartbeat_seconds=10,
            retry_backoff_seconds=10,
            claim_batch_size=1,
            agent_timeout_seconds=180,
        )
        claimed = await worker.run_once()
        with factory() as db:
            task_row = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
            worker_status = task_row.status if task_row is not None else "missing"
            worker_stage = task_row.stage if task_row is not None else "missing"
            worker_attempt = task_row.attempt if task_row is not None else 0
        engine.dispose()
    if not claimed or worker_status != "succeeded":
        raise RuntimeError(f"真实 Worker 未成功完成 QA 任务: {worker_status}/{worker_stage}")
    if not repository.slides_json:
        raise RuntimeError("处理器没有持久化最终作品")

    document = json.loads(repository.slides_json)
    slides = document.get("slides", [])
    slide_types = {
        kind: sum(slide.get("type") == kind for slide in slides)
        for kind in ("cover", "contents", "transition", "content", "end")
    }
    if any(slide_types[kind] == 0 for kind in slide_types):
        raise RuntimeError(f"真实作品没有覆盖五种页面类型: {slide_types}")
    summary = {
        "schemaVersion": 1,
        "templateId": "template_19",
        "status": "PASS",
        "executionMode": "real-content-agent-production-handler-and-persistent-worker",
        "databaseWrites": "isolated-temporary-sqlite-only",
        "productionQueueWrites": False,
        "billingOperations": False,
        "taskId": task_id,
        "presentationId": presentation_id,
        "workerClaimed": claimed,
        "workerStatus": worker_status,
        "workerStage": worker_stage,
        "workerAttempt": worker_attempt,
        "slideCount": len(slides),
        "slideTypes": slide_types,
        "reachedStableLayoutIds": sorted(
            {slide.get("templateSlideId") for slide in slides if slide.get("templateSlideId")}
        ),
        "fixedDecorationCount": sum(
            element.get("imageType") == "decoration"
            for slide in slides
            for element in slide.get("elements", [])
        ),
        "contentImageCount": sum(
            element.get("imageType") == "content"
            for slide in slides
            for element in slide.get("elements", [])
        ),
        "previewUpdates": repository.preview_updates,
    }
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "real-handler-document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_ROOT / "real-handler-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
