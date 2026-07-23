"""T18 任务查询公开模型；仅暴露用户可理解的对账进度。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BillingTaskStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    action: str
    retry_count: int
    next_retry_at: datetime | None
    manual_required: bool


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    presentation_id: str
    status: str
    stage: str
    progress: int
    retryable: bool
    error_code: str | None
    updated_at: datetime
    billing: BillingTaskStatus | None


__all__ = ["BillingTaskStatus", "TaskStatusResponse"]
