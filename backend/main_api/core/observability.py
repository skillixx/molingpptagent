"""T21 全局Request ID、用户限流、稳定错误与结构化审计。"""

from __future__ import annotations

import json
import fnmatch
import logging
import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool


_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
audit_logger = logging.getLogger("backend.main_api.audit")
error_logger = logging.getLogger("backend.main_api.error")


def install_safe_exception_handlers(app: FastAPI) -> None:
    """把框架级HTTP/校验错误收敛为同一安全契约，不回显下游detail或用户输入。"""
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code, message, retryable = _safe_http_error(exc.status_code)
        headers = {"Cache-Control": "no-store"}
        # 只保留标准控制头；禁止透传可能由下游拼接的任意响应头。
        for name in ("Retry-After", "WWW-Authenticate"):
            if exc.headers and name in exc.headers:
                headers[name] = exc.headers[name]
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": code, "message": message, "retryable": retryable,
                "request_id": str(getattr(request.state, "request_id", uuid4().hex)),
            },
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 校验错误可能含原始输入，既不记录也不回显字段值。
        return JSONResponse(
            status_code=422,
            content={
                "code": "REQUEST_INVALID", "message": "请求参数无效", "retryable": False,
                "request_id": str(getattr(request.state, "request_id", uuid4().hex)),
            },
            headers={"Cache-Control": "no-store"},
        )


def _safe_http_error(status: int) -> tuple[str, str, bool]:
    mapping = {
        400: ("REQUEST_INVALID", "请求参数无效", False),
        401: ("AUTH_REQUIRED", "登录状态无效，请重新进入", False),
        403: ("ACCESS_DENIED", "无权执行此操作", False),
        404: ("NOT_FOUND", "请求的资源不存在", False),
        409: ("CONFLICT", "资源状态已变化，请刷新后重试", False),
        413: ("PAYLOAD_TOO_LARGE", "请求内容超过容量限制", False),
        429: ("RATE_LIMITED", "请求过于频繁，请稍后重试", True),
    }
    if status in mapping:
        return mapping[status]
    if status >= 500:
        return "SERVICE_UNAVAILABLE", "服务暂时不可用，请稍后重试", True
    return "REQUEST_REJECTED", "请求未被接受", False


class FixedWindowRateLimiter:
    """进程内owner滑动窗口；生产多实例还需由T22网关提供粗粒度外层保护。"""

    def __init__(self, *, limit: int, window_seconds: int, now_factory=time.monotonic) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("限流配置必须大于零")
        self.limit = limit
        self.window_seconds = window_seconds
        self.now_factory = now_factory
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        now = self.now_factory()
        threshold = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= self.limit:
                return False, max(1, int(events[0] + self.window_seconds - now) + 1)
            events.append(now)
            return True, 0


class OperationalSafetyMiddleware(BaseHTTPMiddleware):
    """统一保护关键写请求；从不记录query、Cookie、请求体或异常正文。"""

    def __init__(
        self, app, *, limiter: FixedWindowRateLimiter,
        critical_routes: set[str], principal_resolver: Callable[[Request], object] | None,
        audit_enabled: bool,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.critical_routes = frozenset(critical_routes)
        self.principal_resolver = principal_resolver
        self.audit_enabled = audit_enabled

    async def dispatch(self, request: Request, call_next):
        request_id = self._request_id(request)
        request.state.request_id = request_id
        route_key = f"{request.method.upper()} {request.url.path}"
        user_id = None
        matched_route = next(
            (pattern for pattern in self.critical_routes if fnmatch.fnmatchcase(route_key, pattern)),
            None,
        )
        if matched_route is not None and self.principal_resolver is not None:
            try:
                # Session/数据库身份解析是同步调用，放入线程池避免阻塞异步事件循环。
                principal = await run_in_threadpool(self.principal_resolver, request)
                user_id = principal if isinstance(principal, int) else getattr(principal, "user_id", None)
                request.state.audit_user_id = user_id
            except Exception:
                # 身份失败交给原路由返回401；限流器不能把认证异常改写成429。
                pass
            if user_id is not None:
                # 所有关键写接口共用owner配额，避免切换资源ID或接口类型绕过限制。
                allowed, retry_after = self.limiter.check(f"user:{user_id}")
                if not allowed:
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "code": "RATE_LIMITED", "message": "请求过于频繁，请稍后重试",
                            "retryable": True, "request_id": request_id,
                        },
                        headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
                    )
                    self._audit(request, user_id, response.status_code, request_id)
                    response.headers["X-Request-Id"] = request_id
                    return response
        try:
            response = await call_next(request)
        except Exception as exc:
            # 只记录异常类型和关联ID，异常消息可能含URL、token或用户内容。
            error_logger.error(
                "unhandled_request_error request_id=%s error_type=%s",
                request_id, type(exc).__name__,
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR", "message": "服务暂时不可用，请稍后重试",
                    "retryable": True, "request_id": request_id,
                },
                headers={"Cache-Control": "no-store"},
            )
        self._audit(request, user_id, response.status_code, request_id)
        response.headers["X-Request-Id"] = request_id
        return response

    @staticmethod
    def _request_id(request: Request) -> str:
        candidate = request.headers.get("x-request-id")
        return candidate if candidate and _SAFE_REQUEST_ID.fullmatch(candidate) else uuid4().hex

    def _audit(self, request: Request, user_id: int | None, status: int, request_id: str) -> None:
        if not self.audit_enabled or request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return
        # 审计是安全控制面，不能被其他模块的临时logger配置静默关闭。
        audit_logger.disabled = False
        audit_logger.info(json.dumps({
            "event": "mutation", "request_id": request_id, "user_id": user_id,
            "method": request.method.upper(), "path": request.url.path,
            "status": status, "outcome": "success" if status < 400 else "failure",
        }, ensure_ascii=False, separators=(",", ":")))


__all__ = ["FixedWindowRateLimiter", "OperationalSafetyMiddleware", "install_safe_exception_handlers"]
