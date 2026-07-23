"""T18 用户任务状态查询服务。"""

from __future__ import annotations

from ..repositories.reconciliation import BillingReconciliationRepository
from ..schemas.tasks import BillingTaskStatus, TaskStatusResponse


class TaskQueryError(RuntimeError):
    """不存在与跨用户访问统一映射为 404，避免资源枚举。"""


class TaskQueryService:
    def __init__(self, repository: BillingReconciliationRepository) -> None:
        self.repository = repository

    def get(self, owner_user_id: int, task_id: str) -> TaskStatusResponse:
        record = self.repository.get_task_status(owner_user_id, task_id)
        if record is None:
            raise TaskQueryError("TASK_NOT_FOUND")
        billing = None
        if record.billing_status is not None and record.billing_action is not None:
            billing = BillingTaskStatus(
                status=record.billing_status,
                action=record.billing_action,
                retry_count=record.billing_retry_count or 0,
                next_retry_at=record.billing_next_retry_at,
                manual_required=record.billing_status == "manual_required",
            )
        return TaskStatusResponse(
            id=record.task_id,
            presentation_id=record.presentation_id,
            status=record.status,
            stage=record.stage,
            progress=record.progress,
            retryable=record.retryable,
            error_code=record.error_code,
            updated_at=record.updated_at,
            billing=billing,
        )


__all__ = ["TaskQueryError", "TaskQueryService"]
