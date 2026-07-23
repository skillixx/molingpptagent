"""T20 导出归档、缩略图和鉴权下载API。"""

from __future__ import annotations

import re
import uuid
from datetime import UTC
from typing import Callable
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, Response

from ..core.identity import RequestPrincipal
from ..core.security import CsrfOriginError, enforce_trusted_origin
from ..schemas.exports import ExportListResponse, ExportResponse, ThumbnailResponse
from ..schemas.presentations import ApiErrorResponse
from ..services.exports import ArchivedExport, ExportService, ExportServiceError, PPTX_MIME


def create_exports_router(*, service: ExportService, principal_dependency: Callable[..., RequestPrincipal], trusted_origins: tuple[str, ...], csrf_enabled: bool) -> APIRouter:
    router = APIRouter(tags=["exports"])
    errors = {
        400: {"model": ApiErrorResponse, "description": "摘要、签名或请求头无效"},
        403: {"model": ApiErrorResponse, "description": "请求来源不受信任"},
        404: {"model": ApiErrorResponse, "description": "作品或文件不存在"},
        409: {"model": ApiErrorResponse, "description": "版本或幂等请求冲突"},
        410: {"model": ApiErrorResponse, "description": "下载地址已过期"},
        413: {"model": ApiErrorResponse, "description": "导出文件超过容量上限"},
        415: {"model": ApiErrorResponse, "description": "请求二进制类型不受支持"},
        503: {"model": ApiErrorResponse, "description": "对象存储暂时不可用"},
    }

    @router.post(
        "/presentations/{presentation_id}/exports/pptx", status_code=201,
        response_model=ExportResponse, responses=errors,
        summary="归档浏览器生成的同一PPTX Blob",
    )
    async def archive_pptx(
        presentation_id: str, request: Request,
        body: bytes = Body(media_type=PPTX_MIME),
        principal: RequestPrincipal = Depends(principal_dependency),
        idempotency_key: str = Header(alias="Idempotency-Key"),
        presentation_version: int = Header(alias="X-Presentation-Version", ge=1),
        content_sha256: str = Header(alias="X-Content-SHA256"),
    ):
        request_id = _request_id(request)
        origin = _origin(request, trusted_origins, csrf_enabled, request_id)
        if origin: return origin
        if request.headers.get("content-type", "").split(";", 1)[0] != PPTX_MIME:
            return _error(415, "EXPORT_CONTENT_TYPE_INVALID", "仅支持PPTX文件", request_id=request_id)
        try:
            result = service.archive(principal.user_id, presentation_id, presentation_version, idempotency_key, content_sha256, body)
            return _payload(result)
        except ExportServiceError as exc:
            return _error(exc.status_code, exc.code, exc.message, exc.retryable, request_id)

    @router.get(
        "/presentations/{presentation_id}/exports",
        response_model=ExportListResponse, responses={404: errors[404]},
        summary="查询当前用户作品的PPTX归档",
    )
    def list_exports(presentation_id: str, request: Request, principal: RequestPrincipal = Depends(principal_dependency)):
        request_id = _request_id(request)
        try:
            items = [_payload(item) for item in service.list(principal.user_id, presentation_id)]
            return {"items": items, "total": len(items)}
        except ExportServiceError as exc:
            return _error(exc.status_code, exc.code, exc.message, exc.retryable, request_id)

    @router.put(
        "/presentations/{presentation_id}/thumbnail",
        response_model=ThumbnailResponse, responses=errors,
        summary="更新作品PNG缩略图",
    )
    async def upload_thumbnail(
        presentation_id: str, request: Request,
        body: bytes = Body(media_type="image/png"),
        principal: RequestPrincipal = Depends(principal_dependency),
        content_sha256: str = Header(alias="X-Content-SHA256"),
    ):
        request_id = _request_id(request)
        origin = _origin(request, trusted_origins, csrf_enabled, request_id)
        if origin: return origin
        if request.headers.get("content-type", "").split(";", 1)[0] != "image/png":
            return _error(415, "EXPORT_CONTENT_TYPE_INVALID", "仅支持PNG缩略图", request_id=request_id)
        try:
            return {"file_id": service.store_thumbnail(principal.user_id, presentation_id, content_sha256, body)}
        except ExportServiceError as exc:
            return _error(exc.status_code, exc.code, exc.message, exc.retryable, request_id)

    @router.get(
        "/files/{file_id}/download",
        responses={
            200: {"content": {PPTX_MIME: {}}, "description": "PPTX原始字节"},
            400: errors[400], 404: errors[404], 410: errors[410], 503: errors[503],
        },
        summary="使用owner绑定短期地址下载历史PPTX",
    )
    def download(
        file_id: str, request: Request,
        expires: int = Query(ge=1), signature: str = Query(min_length=64, max_length=64),
        principal: RequestPrincipal = Depends(principal_dependency),
    ):
        request_id = _request_id(request)
        try:
            body, row = service.download(principal.user_id, file_id, expires, signature)
        except ExportServiceError as exc:
            return _error(exc.status_code, exc.code, exc.message, exc.retryable, request_id)
        safe_ascii = re.sub(r"[^A-Za-z0-9._-]+", "_", row.title).strip("_") or "presentation"
        # RFC 5987文件名也移除路径分隔符，浏览器不能把作品标题解释为目录。
        safe_utf8 = re.sub(r"[\\/:*?\"<>|]+", "_", row.title).strip() or "presentation"
        utf8_name = quote(f"{safe_utf8}-v{row.export.presentation_version}.pptx")
        disposition = f'attachment; filename="{safe_ascii}-v{row.export.presentation_version}.pptx"; filename*=UTF-8\'\'{utf8_name}'
        return Response(body, media_type=PPTX_MIME, headers={
            "Content-Disposition": disposition, "Cache-Control": "no-store",
            "X-Content-SHA256": row.file.sha256,
        })

    return router


def _payload(item: ArchivedExport) -> dict[str, object]:
    row = item.record
    return {
        "id": row.export.id, "presentation_id": row.export.presentation_id,
        "presentation_version": row.export.presentation_version, "file_id": row.file.id,
        "sha256": row.file.sha256, "size_bytes": row.file.size_bytes,
        "created_at": row.export.created_at.replace(tzinfo=UTC).isoformat(),
        "download_url": item.download_url, "reused": item.reused,
    }


def _origin(request: Request, trusted: tuple[str, ...], enabled: bool, request_id: str):
    if not enabled: return None
    try:
        enforce_trusted_origin(request.headers.get("origin"), trusted)
    except CsrfOriginError:
        return _error(403, "AUTH_ORIGIN_REJECTED", "请求来源不受信任", request_id=request_id)
    return None


def _request_id(request: Request) -> str:
    # 复用全局中间件的安全关联ID，避免响应头与响应体出现两个不同ID。
    return str(getattr(request.state, "request_id", None) or uuid.uuid4().hex)


def _error(
    status: int, code: str, message: str, retryable: bool = False,
    request_id: str | None = None,
) -> JSONResponse:
    request_id = request_id or uuid.uuid4().hex
    return JSONResponse(status_code=status, content={
        "code": code, "message": message, "retryable": retryable, "request_id": request_id,
    }, headers={"X-Request-Id": request_id, "Cache-Control": "no-store"})


__all__ = ["create_exports_router"]
