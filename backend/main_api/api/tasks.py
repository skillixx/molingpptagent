"""T18 当前用户任务进度与计费对账状态 API。"""

from __future__ import annotations

from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from ..core.identity import RequestPrincipal
from ..schemas.presentations import ApiErrorResponse
from ..schemas.tasks import TaskStatusResponse
from ..services.tasks import TaskQueryError, TaskQueryService


def create_tasks_router(
    *,
    service: TaskQueryService,
    principal_dependency: Callable[..., RequestPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get(
        "/{task_id}",
        response_model=TaskStatusResponse,
        responses={404: {"model": ApiErrorResponse, "description": "任务不存在或无权访问"}},
        summary="查询当前用户任务状态",
    )
    def get_task(
        task_id: str,
        request: Request,
        response: Response,
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = getattr(request.state, "request_id", None) or uuid4().hex
        try:
            result = service.get(principal.user_id, task_id)
        except TaskQueryError:
            # 404 不区分不存在与 owner 不匹配，防止通过任务 ID 枚举其他用户。
            return JSONResponse(
                status_code=404,
                content={
                    "code": "TASK_NOT_FOUND",
                    "message": "任务不存在",
                    "retryable": False,
                    "request_id": request_id,
                },
                headers={"X-Request-Id": request_id},
            )
        response.headers["X-Request-Id"] = request_id
        return result

    return router


__all__ = ["create_tasks_router"]
