"""墨灵SSO入口路由。"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from ..core.security import CsrfOriginError, enforce_trusted_origin
from ..integrations.moling import (
    MolingAuthenticationError,
    MolingError,
    MolingIdentityMismatchError,
    MolingUnavailableError,
)
from ..services.auth import AuthService


_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}
logger = logging.getLogger(__name__)


def create_auth_router(
    *,
    auth_service: AuthService,
    cookie_name: str,
    cookie_secure: bool,
    trusted_origins: tuple[str, ...],
) -> APIRouter:
    """构造可注入测试替身的认证路由，主应用只负责装配。"""
    router = APIRouter()

    @router.get("/enter", include_in_schema=True)
    async def enter(request: Request, ticket: str | None = Query(default=None)):
        """消费一次性票据、签发HttpOnly Cookie并清除地址栏中的ticket。"""
        if (
            not ticket
            or ticket.strip() != ticket
            or len(ticket) > 512
            or any(ord(character) < 32 for character in ticket)
        ):
            return _error_response(request, 400, "缺少墨灵启动票据", browser_reason="expired")
        try:
            issued = await auth_service.enter(
                ticket,
                current_session_token=request.cookies.get(cookie_name),
            )
        except MolingIdentityMismatchError as exc:
            logger.warning("auth_enter_scope_mismatch request_id=%s", exc.request_id)
            return _error_response(
                request, 403, "墨灵身份不属于当前应用", exc.request_id, browser_reason="forbidden"
            )
        except MolingAuthenticationError as exc:
            logger.info("auth_enter_rejected request_id=%s", exc.request_id)
            return _error_response(
                request, 401, "启动票据无效，请从墨灵重新进入", exc.request_id,
                browser_reason="expired",
            )
        except MolingUnavailableError as exc:
            logger.warning("auth_enter_platform_unavailable request_id=%s", exc.request_id)
            return _error_response(
                request, 503, "墨灵平台暂时不可用，请重新发起进入", exc.request_id,
                browser_reason="platform",
            )
        except MolingError as exc:
            logger.warning("auth_enter_platform_protocol_error request_id=%s", exc.request_id)
            return _error_response(
                request, 502, "墨灵平台响应异常，请重新发起进入", exc.request_id,
                browser_reason="platform",
            )

        # SSO 只增加身份边界，不替换原 PPTAgent 的主题输入与流式生成主流程。
        response = RedirectResponse(url="/", status_code=302, headers=_SECURITY_HEADERS)
        response.set_cookie(
            key=cookie_name,
            value=issued.raw_token,
            max_age=issued.max_age_seconds,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    @router.get("/auth/me", include_in_schema=True)
    def current_user(request: Request) -> JSONResponse:
        """只从服务端Session恢复当前身份，忽略任何浏览器提交的owner字段。"""
        raw_token = request.cookies.get(cookie_name)
        app_session = auth_service.resolve_session(raw_token) if raw_token else None
        if app_session is None:
            request_id = str(getattr(request.state, "request_id", None) or uuid4().hex)
            response = JSONResponse(
                status_code=401,
                content={
                    "code": "AUTH_SESSION_EXPIRED",
                    "message": "登录已过期，请从墨灵重新进入",
                    "retryable": False,
                    "request_id": request_id,
                },
                headers=_SECURITY_HEADERS,
            )
            _clear_session_cookie(response, cookie_name, cookie_secure)
            return response
        return JSONResponse(
            content={
                "user_id": app_session.user_id,
                "app_id": app_session.app_id,
                "product_id": app_session.product_id,
            },
            headers=_SECURITY_HEADERS,
        )

    @router.post("/auth/logout", include_in_schema=True, status_code=204)
    def logout(request: Request) -> Response:
        """精确校验Origin后幂等撤销当前会话，其他设备Session不受影响。"""
        try:
            enforce_trusted_origin(request.headers.get("origin"), trusted_origins)
        except CsrfOriginError:
            request_id = str(getattr(request.state, "request_id", None) or uuid4().hex)
            return JSONResponse(
                status_code=403,
                content={
                    "code": "AUTH_ORIGIN_REJECTED", "message": "请求来源不受信任",
                    "retryable": False,
                    "request_id": request_id,
                },
                headers=_SECURITY_HEADERS,
            )
        auth_service.logout(request.cookies.get(cookie_name))
        response = Response(status_code=204, headers=_SECURITY_HEADERS)
        _clear_session_cookie(response, cookie_name, cookie_secure)
        return response

    return router


def _clear_session_cookie(response: Response, cookie_name: str, cookie_secure: bool) -> None:
    """删除Cookie时复用原属性，确保浏览器命中同一作用域而不是留下幽灵会话。"""
    response.delete_cookie(
        key=cookie_name,
        path="/",
        secure=cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _error_response(
    request: Request,
    status_code: int,
    message: str,
    request_id: str | None = None,
    *,
    browser_reason: str,
) -> JSONResponse | RedirectResponse:
    """页面导航去安全错误页，API调用保留稳定状态码；两者都不回显ticket。"""
    if "text/html" in request.headers.get("accept", "").lower():
        return RedirectResponse(
            url=f"/auth-failure?reason={browser_reason}",
            status_code=303,
            headers=_SECURITY_HEADERS,
        )
    # 主应用优先使用全局请求ID；独立路由测试仍可使用墨灵上游请求ID作为兼容兜底。
    public_request_id = str(getattr(request.state, "request_id", None) or request_id or "")
    return JSONResponse(
        status_code=status_code,
        content={
            "code": "AUTH_ENTRY_FAILED", "message": message,
            "retryable": status_code >= 500, "request_id": public_request_id,
        },
        headers=_SECURITY_HEADERS,
    )
