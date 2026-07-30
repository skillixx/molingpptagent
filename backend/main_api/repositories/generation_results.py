"""生成结果的租约围栏持久化仓储。"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from ..models.domain import GenerationTask, Presentation
from ..workers.runner import TaskExecution


class GenerationResultRepository:
    """只允许当前 Worker 租约把完整生成结果写入所属作品。"""

    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def persist(
        self,
        task: TaskExecution,
        *,
        slides_json: str,
        slide_count: int,
        now: datetime,
    ) -> bool:
        """在同一事务中核对任务、租约、owner 和作品状态后写入结果。"""
        if not task.lock_token:
            return False
        with self._session_factory.begin() as db:
            generation_task = db.scalar(
                select(GenerationTask)
                .where(
                    GenerationTask.id == task.task_id,
                    GenerationTask.presentation_id == task.presentation_id,
                    GenerationTask.owner_user_id == task.owner_user_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == task.lock_token,
                    GenerationTask.locked_until > now,
                )
                .with_for_update()
            )
            if generation_task is None:
                return False
            presentation = db.scalar(
                select(Presentation)
                .where(
                    Presentation.id == task.presentation_id,
                    Presentation.owner_user_id == task.owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if presentation is None:
                return False
            if presentation.status == "ready":
                return presentation.slides_json == slides_json
            if presentation.status != "generating":
                return False
            presentation.slides_json = slides_json
            presentation.slide_count = slide_count
            presentation.status = "ready"
            presentation.updated_at = now
            return True

    def has_persisted_result(self, task: TaskExecution) -> bool:
        """只读确认目标作品已经形成结构完整且非空的可编辑文档。"""
        with self._session_factory() as db:
            presentation = db.scalar(
                select(Presentation)
                .join(
                    GenerationTask,
                    GenerationTask.presentation_id == Presentation.id,
                )
                .where(
                    GenerationTask.id == task.task_id,
                    GenerationTask.owner_user_id == task.owner_user_id,
                    Presentation.id == task.presentation_id,
                    Presentation.owner_user_id == task.owner_user_id,
                    Presentation.deleted_at.is_(None),
                    # 结算结果未知时作品会暂时转为 billing_pending，但已落库产物仍必须被识别并继续 settle。
                    Presentation.status.in_(("ready", "billing_pending")),
                    Presentation.slide_count > 0,
                )
            )
            if presentation is None:
                return False
            try:
                document = json.loads(presentation.slides_json)
            except (TypeError, json.JSONDecodeError):
                return False
            slides = document.get("slides") if isinstance(document, dict) else None
            return isinstance(slides, list) and len(slides) == presentation.slide_count


__all__ = ["GenerationResultRepository"]
