"""T09 作品 CRUD 路由与稳定错误响应。"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Callable, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..core.identity import RequestPrincipal
from ..core.security import CsrfOriginError, enforce_trusted_origin
from ..models.domain import GenerationTask, Presentation
from ..schemas.presentations import (
    ApiErrorResponse,
    CreateCheckpointRequest,
    CreatePresentationRequest,
    CreatePresentationResponse,
    DuplicatePresentationRequest,
    PresentationDetail,
    PresentationListResponse,
    PresentationSummary,
    PresentationVersionListResponse,
    PresentationVersionSummary,
    RestoreCheckpointRequest,
    SavePresentationRequest,
    SaveDraftPresentationRequest,
    SaveDraftPresentationResponse,
    TaskSummary,
)
from ..services.presentations import PresentationService, PresentationServiceError


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
PresentationStatus = Literal["draft", "generating", "ready", "failed", "billing_pending"]
PresentationSort = Literal["updated_desc", "updated_asc", "created_desc", "title_asc"]


def create_presentations_router(
    *,
    service: PresentationService,
    principal_dependency: Callable[..., RequestPrincipal],
    trusted_origins: tuple[str, ...],
    csrf_enabled: bool,
) -> APIRouter:
    """构造可注入真实仓储和测试身份的作品路由。"""
    # 反向代理统一移除外部 /api 前缀；测试和OpenAPI可在挂载时补回公共前缀。
    router = APIRouter(prefix="/presentations", tags=["presentations"])
    error_responses = {
        400: {"model": ApiErrorResponse, "description": "幂等键或请求参数无效"},
        403: {"model": ApiErrorResponse, "description": "请求来源不受信任"},
        404: {"model": ApiErrorResponse, "description": "作品不存在或不属于当前用户"},
        409: {"model": ApiErrorResponse, "description": "幂等请求或容量冲突"},
        413: {"model": ApiErrorResponse, "description": "当前编辑稿超过配置上限"},
        500: {"model": ApiErrorResponse, "description": "已存作品数据损坏"},
    }

    @router.post(
        "",
        response_model=CreatePresentationResponse,
        status_code=202,
        responses=error_responses,
        summary="创建作品和持久生成任务",
    )
    def create_presentation(
        payload: CreatePresentationRequest,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        if idempotency_key is None or not _SAFE_IDENTIFIER.fullmatch(idempotency_key):
            return _error(
                400,
                "PRESENTATION_IDEMPOTENCY_KEY_INVALID",
                "Idempotency-Key格式无效",
                request_id,
            )
        try:
            result = service.create(
                principal.user_id,
                idempotency_key,
                payload,
                billing_entitlement_id=principal.entitlement_id,
            )
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        return CreatePresentationResponse(
            presentation=_summary(result.presentation),
            task=_task_summary(result.task),
            reused=result.reused,
        )

    @router.post(
        "/drafts",
        response_model=SaveDraftPresentationResponse,
        status_code=201,
        responses=error_responses,
        summary="把临时编辑稿保存到当前用户作品库",
    )
    def save_draft_presentation(
        payload: SaveDraftPresentationRequest,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        if idempotency_key is None or not _SAFE_IDENTIFIER.fullmatch(idempotency_key):
            return _error(
                400,
                "PRESENTATION_IDEMPOTENCY_KEY_INVALID",
                "Idempotency-Key格式无效",
                request_id,
            )
        try:
            result = service.save_draft(
                principal.user_id, idempotency_key, payload
            )
            detail = _detail(result.presentation)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.status_code = 200 if result.reused else 201
        response.headers["X-Request-Id"] = request_id
        return SaveDraftPresentationResponse(
            presentation=detail,
            reused=result.reused,
        )

    @router.get(
        "",
        response_model=PresentationListResponse,
        responses={404: error_responses[404]},
        summary="分页查询当前用户作品",
    )
    def list_presentations(
        response: Response,
        request: Request,
        principal: RequestPrincipal = Depends(principal_dependency),
        page: int = Query(default=1, ge=1, le=10_000),
        page_size: int = Query(default=20, ge=1, le=100),
        search: str | None = Query(default=None, max_length=100),
        status: PresentationStatus | None = Query(default=None),
        sort: PresentationSort = Query(default="updated_desc"),
    ) -> PresentationListResponse:
        result = service.list(
            principal.user_id,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            sort=sort,
        )
        response.headers["X-Request-Id"] = _request_id(request)
        return PresentationListResponse(
            items=[_summary(item) for item in result.page.items],
            page=result.page_number,
            page_size=result.page_size,
            total=result.page.total,
            has_more=result.page_number * result.page_size < result.page.total,
        )

    @router.get(
        "/{presentation_id}",
        response_model=PresentationDetail,
        responses={404: error_responses[404], 500: error_responses[500]},
        summary="加载当前用户作品编辑稿",
    )
    def get_presentation(
        presentation_id: str,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        try:
            presentation = service.get(principal.user_id, presentation_id)
            task = service.get_latest_generation_task(principal.user_id, presentation_id)
            detail = _detail(presentation, task)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        return detail

    @router.patch(
        "/{presentation_id}",
        response_model=PresentationDetail,
        responses={
            403: error_responses[403],
            404: error_responses[404],
            409: {"model": ApiErrorResponse, "description": "作品版本冲突或状态不可编辑"},
            413: error_responses[413],
            422: {"model": ApiErrorResponse, "description": "当前编辑稿结构无效"},
        },
        summary="保存当前作品编辑稿",
    )
    def save_presentation(
        presentation_id: str,
        payload: SavePresentationRequest,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        try:
            detail = _detail(service.save(principal.user_id, presentation_id, payload))
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        return detail

    @router.post(
        "/{presentation_id}/duplicate",
        response_model=PresentationDetail,
        status_code=201,
        responses=error_responses,
        summary="另存当前作品副本",
    )
    def duplicate_presentation(
        presentation_id: str,
        payload: DuplicatePresentationRequest,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        try:
            presentation = service.duplicate(
                principal.user_id, presentation_id, payload.title, payload.slides
            )
            detail = _detail(presentation)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        return detail

    @router.get(
        "/{presentation_id}/versions",
        response_model=PresentationVersionListResponse,
        responses={404: error_responses[404], 500: error_responses[500]},
        summary="查询作品检查点版本",
    )
    def list_presentation_versions(
        presentation_id: str,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        try:
            records = service.list_checkpoints(principal.user_id, presentation_id)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        return PresentationVersionListResponse(
            items=[_version_summary(record) for record in records], total=len(records)
        )

    @router.post(
        "/{presentation_id}/versions",
        response_model=PresentationVersionSummary,
        status_code=201,
        responses={
            200: {"model": PresentationVersionSummary, "description": "同版本检查点已存在"},
            403: error_responses[403],
            404: error_responses[404],
            409: {"model": ApiErrorResponse, "description": "作品版本冲突或状态不可编辑"},
            503: {"model": ApiErrorResponse, "description": "大检查点需要尚未启用的对象存储"},
        },
        summary="为当前作品版本创建检查点",
    )
    def create_presentation_checkpoint(
        presentation_id: str,
        payload: CreateCheckpointRequest,
        request: Request,
        response: Response,
        background_tasks: BackgroundTasks,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        try:
            record = service.create_checkpoint(principal.user_id, presentation_id, payload)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.status_code = 201 if record.created else 200
        response.headers["X-Request-Id"] = request_id
        background_tasks.add_task(service.prune_checkpoints, principal.user_id, presentation_id)
        return _version_summary(record)

    @router.post(
        "/{presentation_id}/versions/{version}/restore",
        response_model=PresentationDetail,
        responses={
            403: error_responses[403],
            404: error_responses[404],
            409: {"model": ApiErrorResponse, "description": "作品版本冲突或状态不可编辑"},
            500: error_responses[500],
        },
        summary="把历史检查点恢复为新的当前版本",
    )
    def restore_presentation_checkpoint(
        presentation_id: str,
        version: int,
        payload: RestoreCheckpointRequest,
        request: Request,
        response: Response,
        background_tasks: BackgroundTasks,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        try:
            presentation = service.restore_checkpoint(
                principal.user_id, presentation_id, version, payload
            )
            detail = _detail(presentation)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        response.headers["X-Request-Id"] = request_id
        background_tasks.add_task(service.prune_checkpoints, principal.user_id, presentation_id)
        return detail

    @router.delete(
        "/{presentation_id}",
        status_code=204,
        response_model=None,
        responses=error_responses,
        summary="幂等软删除当前用户作品",
    )
    def delete_presentation(
        presentation_id: str,
        request: Request,
        principal: RequestPrincipal = Depends(principal_dependency),
    ) -> Response:
        request_id = _request_id(request)
        origin_error = _check_origin(request, trusted_origins, csrf_enabled, request_id)
        if origin_error:
            return origin_error
        try:
            service.delete(principal.user_id, presentation_id)
        except PresentationServiceError as exc:
            return _service_error(exc, request_id)
        return Response(status_code=204, headers={"X-Request-Id": request_id})

    return router


def _summary(presentation: Presentation) -> PresentationSummary:
    return PresentationSummary(
        id=presentation.id,
        title=presentation.title,
        status=presentation.status,
        current_version=presentation.current_version,
        slide_count=presentation.slide_count,
        template_id=presentation.template_id,
        thumbnail_file_id=presentation.thumbnail_file_id,
        created_at=_utc(presentation.created_at),
        updated_at=_utc(presentation.updated_at),
    )


def _detail(
    presentation: Presentation, task: GenerationTask | None = None
) -> PresentationDetail:
    try:
        slides = json.loads(presentation.slides_json)
    except (TypeError, json.JSONDecodeError):
        raise PresentationServiceError(
            "PRESENTATION_DATA_INVALID", "作品数据暂时无法读取", 500
        ) from None
    return PresentationDetail(
        **_summary(presentation).model_dump(),
        slides=slides,
        generation_task_id=task.id if task is not None else None,
        generation_progress=task.progress if task is not None else None,
        # 只返回数据库中的稳定错误码，绝不暴露error_message或Agent正文。
        generation_error_code=task.last_error_code if task is not None else None,
    )


def _version_summary(record) -> PresentationVersionSummary:
    checkpoint = record.checkpoint
    return PresentationVersionSummary(
        id=checkpoint.id,
        version=checkpoint.version,
        reason=checkpoint.reason,
        created_at=_utc(checkpoint.created_at),
        content_sha256=record.content_sha256,
        uncompressed_bytes=record.uncompressed_bytes,
    )


def _task_summary(task: GenerationTask) -> TaskSummary:
    return TaskSummary(
        id=task.id,
        status=task.status,
        stage=task.stage,
        progress=task.progress,
        retryable=task.retryable,
    )


def _check_origin(
    request: Request,
    trusted_origins: tuple[str, ...],
    enabled: bool,
    request_id: str,
) -> JSONResponse | None:
    if not enabled:
        return None
    try:
        enforce_trusted_origin(request.headers.get("origin"), trusted_origins)
    except CsrfOriginError:
        return _error(403, "AUTH_ORIGIN_REJECTED", "请求来源不受信任", request_id)
    return None


def _request_id(request: Request) -> str:
    # 全局中间件已完成格式校验；优先复用它生成的关联ID，保证响应体与响应头一致。
    state_request_id = getattr(request.state, "request_id", None)
    if state_request_id:
        return str(state_request_id)
    candidate = request.headers.get("x-request-id")
    return candidate if candidate and _SAFE_IDENTIFIER.fullmatch(candidate) else uuid.uuid4().hex


def _service_error(exc: PresentationServiceError, request_id: str) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message, request_id, details=exc.details)


def _error(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    *,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    content = {
        "code": code,
        "message": message,
        "retryable": False,
        "request_id": request_id,
    }
    if details:
        content.update(details)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers={"X-Request-Id": request_id, "Cache-Control": "no-store"},
    )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


__all__ = ["create_presentations_router"]
