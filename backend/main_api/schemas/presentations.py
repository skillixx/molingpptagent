"""T09 作品 API 的公开请求、响应和 OpenAPI 示例。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreatePresentationRequest(BaseModel):
    """客户端只能描述生成意图，不能提交owner、状态或任务字段。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255, examples=["2026年季度经营汇报"])
    content: str = Field(min_length=1, max_length=20_000, examples=["生成一份季度经营汇报"])
    language: str = Field(default="chinese", min_length=1, max_length=32)
    model: str = Field(default="deepseek-chat", min_length=1, max_length=64)
    template_id: str | None = Field(default=None, min_length=1, max_length=64)
    generate_from_uploaded_file: bool = False
    generate_from_web_search: bool = True


class SaveDraftPresentationRequest(BaseModel):
    """把浏览器中的临时编辑稿保存为当前用户可继续编辑的云端作品。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    template_id: str | None = Field(default=None, min_length=1, max_length=64)
    slides: dict[str, Any]


class DuplicatePresentationRequest(BaseModel):
    """普通复制可只给标题；冲突另存允许携带当前用户的本地稿。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=255)
    slides: dict[str, Any] | None = None


class SavePresentationRequest(BaseModel):
    """T12当前稿保存；owner、状态和版本均不能由浏览器覆盖。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    base_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    slides: dict[str, Any]


CheckpointReason = Literal["manual", "ai", "export", "periodic"]


class CreateCheckpointRequest(BaseModel):
    """检查点只引用当前服务端版本，不接受浏览器直接注入历史正文。"""

    model_config = ConfigDict(extra="forbid")

    base_version: int = Field(ge=1)
    reason: CheckpointReason


class RestoreCheckpointRequest(BaseModel):
    """恢复同样执行乐观锁，避免用历史稿覆盖其他标签的新修改。"""

    model_config = ConfigDict(extra="forbid")

    base_version: int = Field(ge=1)


class PresentationSummary(BaseModel):
    id: str
    title: str
    status: str
    current_version: int
    slide_count: int
    template_id: str | None
    thumbnail_file_id: str | None
    created_at: datetime
    updated_at: datetime


class PresentationDetail(PresentationSummary):
    slides: Any


class PresentationVersionSummary(BaseModel):
    id: str
    version: int
    reason: str
    created_at: datetime
    content_sha256: str
    uncompressed_bytes: int


class PresentationVersionListResponse(BaseModel):
    items: list[PresentationVersionSummary]
    total: int


class TaskSummary(BaseModel):
    id: str
    status: str
    stage: str
    progress: int
    retryable: bool


class CreatePresentationResponse(BaseModel):
    presentation: PresentationSummary
    task: TaskSummary
    reused: bool


class SaveDraftPresentationResponse(BaseModel):
    presentation: PresentationDetail
    reused: bool


class PresentationListResponse(BaseModel):
    items: list[PresentationSummary]
    page: int
    page_size: int
    total: int
    has_more: bool


class PresentationConflictSummary(BaseModel):
    title: str
    current_version: int
    updated_at: datetime


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str
    latest: PresentationConflictSummary | None = None


__all__ = [
    "ApiErrorResponse",
    "CreatePresentationRequest",
    "SaveDraftPresentationRequest",
    "SaveDraftPresentationResponse",
    "CreatePresentationResponse",
    "CreateCheckpointRequest",
    "DuplicatePresentationRequest",
    "PresentationDetail",
    "PresentationConflictSummary",
    "PresentationListResponse",
    "PresentationSummary",
    "PresentationVersionListResponse",
    "PresentationVersionSummary",
    "RestoreCheckpointRequest",
    "SavePresentationRequest",
    "TaskSummary",
]
