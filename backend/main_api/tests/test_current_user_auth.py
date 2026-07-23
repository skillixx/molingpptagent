"""T05 当前用户、退出与多标签失效契约测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.main_api.api.auth import create_auth_router
from backend.main_api.integrations.moling import LaunchClaims
from backend.main_api.models.auth import Base
from backend.main_api.repositories.sessions import SessionRepository
from backend.main_api.services.auth import AuthService


NOW = datetime(2026, 7, 23, 2, 0, tzinfo=UTC)
TRUSTED_ORIGIN = "https://ppt.example.com"
COOKIE_NAME = "trainppt_session"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class UnusedMolingClient:
    """T05接口只解析本地Session，绝不能回调平台verify。"""

    async def verify_launch_ticket(self, _launch_ticket: str) -> LaunchClaims:
        raise AssertionError("T05当前用户和退出不应调用墨灵verify")


@pytest.fixture()
def auth_context(tmp_path):
    """使用隔离SQLite装配真实Repository与Service。"""

    engine = create_engine(f"sqlite:///{(tmp_path / 'auth.db').as_posix()}")
    Base.metadata.create_all(engine)
    repository = SessionRepository(engine)
    tokens = iter(("browser-session", "other-device-session"))
    service = AuthService(
        moling_client=UnusedMolingClient(),
        session_repository=repository,
        absolute_ttl=timedelta(hours=24),
        idle_ttl=timedelta(hours=2),
        token_factory=lambda: next(tokens),
        now_factory=lambda: NOW,
    )
    app = FastAPI()
    app.include_router(
        create_auth_router(
            auth_service=service,
            cookie_name=COOKIE_NAME,
            cookie_secure=False,
            trusted_origins=(TRUSTED_ORIGIN,),
        )
    )
    yield app, service
    engine.dispose()


def _claims(user_id: int = 9) -> LaunchClaims:
    return LaunchClaims(user_id=user_id, app_id=15, product_id=73, request_id="req_t05")


def test_me_returns_only_server_session_identity(auth_context) -> None:
    """浏览器不能指定owner；当前用户只能来自服务端Session。"""

    app, service = auth_context
    issued = service.create_session(_claims())
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issued.raw_token)
        response = client.get("/auth/me?user_id=999")

    assert response.status_code == 200
    assert response.json() == {"user_id": 9, "app_id": 15, "product_id": 73}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("cookie", [None, "unknown-session"])
def test_me_rejects_missing_or_invalid_session(auth_context, cookie: str | None) -> None:
    """缺失、过期或伪造Cookie统一返回稳定401，不泄露Session查找细节。"""

    app, _service = auth_context
    with TestClient(app) as client:
        if cookie:
            client.cookies.set(COOKIE_NAME, cookie)
        response = client.get("/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "AUTH_SESSION_EXPIRED"
    assert body["message"] == "登录已过期，请从墨灵重新进入"
    assert body["retryable"] is False
    assert body["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_requires_exact_trusted_origin_and_preserves_session_on_failure(auth_context) -> None:
    """退出属于Cookie写操作，缺失或跨站Origin必须在撤销前失败。"""

    app, service = auth_context
    issued = service.create_session(_claims())
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issued.raw_token)
        missing = client.post("/auth/logout")
        cross_site = client.post("/auth/logout", headers={"Origin": "https://evil.example"})

    assert missing.status_code == 403
    assert cross_site.status_code == 403
    assert service.resolve_session(issued.raw_token, now=NOW + timedelta(minutes=1)) is not None


def test_logout_is_idempotent_clears_cookie_and_invalidates_other_tabs(auth_context) -> None:
    """共享同一Cookie的标签页在任一标签退出后都必须立即失效。"""

    app, service = auth_context
    issued = service.create_session(_claims())
    with TestClient(app) as first_tab, TestClient(app) as second_tab:
        first_tab.cookies.set(COOKIE_NAME, issued.raw_token)
        second_tab.cookies.set(COOKIE_NAME, issued.raw_token)
        logout = first_tab.post("/auth/logout", headers={"Origin": TRUSTED_ORIGIN})
        other_tab = second_tab.get("/auth/me")
        repeated = first_tab.post("/auth/logout", headers={"Origin": TRUSTED_ORIGIN})

    assert logout.status_code == 204
    assert logout.headers["cache-control"] == "no-store"
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert other_tab.status_code == 401
    assert repeated.status_code == 204
    assert service.resolve_session(issued.raw_token, now=NOW + timedelta(minutes=1)) is None


def test_logout_revokes_only_current_device(auth_context) -> None:
    """退出当前浏览器不能按用户批量撤销其他设备Session。"""

    app, service = auth_context
    browser = service.create_session(_claims())
    other_device = service.create_session(_claims())
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, browser.raw_token)
        response = client.post("/auth/logout", headers={"Origin": TRUSTED_ORIGIN})

    assert response.status_code == 204
    assert service.resolve_session(browser.raw_token, now=NOW + timedelta(minutes=1)) is None
    assert service.resolve_session(other_device.raw_token, now=NOW + timedelta(minutes=1)) is not None


def test_external_api_prefix_is_rewritten_once_by_dev_and_nginx_proxies() -> None:
    """浏览器请求`/api/auth/*`，两套代理都只移除一次`/api`前缀。"""

    frontend_service = (REPOSITORY_ROOT / "frontend/src/services/auth.ts").read_text(encoding="utf-8")
    vite_config = (REPOSITORY_ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    nginx_config = (REPOSITORY_ROOT / "frontend/nginx.conf").read_text(encoding="utf-8")

    assert "'/api/auth/me'" in frontend_service
    assert "'/api/auth/logout'" in frontend_service
    assert "path.replace(/^\\/api/, '')" in vite_config
    assert "location /api/" in nginx_config
    # T22正式容器只走内部服务名，不依赖桌面Docker专用host网关。
    assert "proxy_pass http://${MAIN_API_UPSTREAM}/;" in nginx_config
    assert "host.docker.internal" not in nginx_config


def test_dev_enter_proxy_preserves_the_one_time_ticket_path() -> None:
    """开发入口必须交给主 API 校验，不能落入无对应路由的 Vue 页面形成白屏。"""

    vite_config = (REPOSITORY_ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")

    assert "'/enter': {" in vite_config
    enter_proxy = vite_config.split("'/enter': {", 1)[1].split("}", 1)[0]
    assert "target: 'http://127.0.0.1:6800'" in enter_proxy
    assert "rewrite" not in enter_proxy
