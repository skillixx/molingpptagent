"""旧工具接口的可信请求主体解析。"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from fastapi import HTTPException, Request

from ..models.auth import AppSession


_GENERATION_CONTEXT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class SessionResolver(Protocol):
    """避免核心身份模块依赖具体 Session 仓储实现。"""

    def resolve_session(self, raw_token: str | None) -> AppSession | None: ...


@dataclass(frozen=True)
class RequestPrincipal:
    """服务端确认的资源 owner 与知识库主体。"""

    user_id: int
    app_id: int | None
    product_id: int | None
    knowledge_subject: str


def knowledge_subject(app_env: str, app_id: int, user_id: int) -> str:
    """包含环境、平台应用和用户三维，防止跨环境或跨应用集合碰撞。"""
    if app_env not in {"development", "test", "staging", "production"}:
        raise ValueError("应用环境不受支持")
    if app_id <= 0 or user_id <= 0:
        raise ValueError("平台主体必须是正整数")
    return f"moling:{app_env}:{app_id}:{user_id}"


def generation_context_id(client_value: str | None, fallback: str) -> str:
    """旧 sessionId 仅作为 Agent 上下文；非法值降级为服务端随机值。"""
    if client_value and _GENERATION_CONTEXT_PATTERN.fullmatch(client_value):
        return client_value
    return fallback


class LegacyIdentityResolver:
    """SSO 模式只信任 Cookie；本地模式使用固定主体保持单机旧流程。"""

    def __init__(
        self,
        *,
        sso_enabled: bool,
        app_env: str,
        cookie_name: str,
        auth_service: SessionResolver | None,
    ) -> None:
        self._sso_enabled = sso_enabled
        self._app_env = app_env
        self._cookie_name = cookie_name
        self._auth_service = auth_service

    def resolve(self, request: Request) -> RequestPrincipal:
        """不读取 query、form 或 JSON 中的 user_id，切断客户端 owner 注入。"""
        if not self._sso_enabled:
            return RequestPrincipal(
                user_id=0,
                app_id=None,
                product_id=None,
                knowledge_subject=f"local:{self._app_env}:trainppt",
            )

        app_session = None
        if self._auth_service is not None:
            app_session = self._auth_service.resolve_session(request.cookies.get(self._cookie_name))
        if app_session is None:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_SESSION_EXPIRED", "message": "登录已过期，请从墨灵重新进入"},
            )
        return RequestPrincipal(
            user_id=app_session.user_id,
            app_id=app_session.app_id,
            product_id=app_session.product_id,
            knowledge_subject=knowledge_subject(
                self._app_env,
                app_session.app_id,
                app_session.user_id,
            ),
        )


__all__ = [
    "LegacyIdentityResolver",
    "RequestPrincipal",
    "generation_context_id",
    "knowledge_subject",
]
