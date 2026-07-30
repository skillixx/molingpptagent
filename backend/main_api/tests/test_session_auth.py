"""T04 `/enter`、持久Session与Cookie安全契约测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.main_api.api.auth import create_auth_router
from backend.main_api.core.security import (
    CsrfOriginError,
    enforce_trusted_origin,
    trusted_origin_from_url,
    uvicorn_access_log_enabled,
)
from backend.main_api.integrations.moling import (
    LaunchClaims,
    MolingAuthenticationError,
    MolingIdentityMismatchError,
    MolingProtocolError,
    MolingUnavailableError,
)
from backend.main_api.models.auth import AppSession, Base
from backend.main_api.repositories.sessions import SessionRepository, SessionSchemaError
from backend.main_api.services.auth import AuthService
from backend.main_api.tests.test_db_and_migrations import _alembic_config


NOW = datetime(2026, 7, 23, 1, 30, tzinfo=UTC)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class FakeMolingClient:
    """只记录消费次数，不保存或输出真实票据。"""

    def __init__(self, result: LaunchClaims | Exception) -> None:
        self.result = result
        self.calls = 0

    async def verify_launch_ticket(self, launch_ticket: str) -> LaunchClaims:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture()
def repository(tmp_path) -> SessionRepository:
    """每个测试使用独立SQLite数据库，不接触当前MySQL。"""
    engine = create_engine(f"sqlite:///{(tmp_path / 'sessions.db').as_posix()}")
    Base.metadata.create_all(engine)
    repo = SessionRepository(engine)
    yield repo
    engine.dispose()


def _claims() -> LaunchClaims:
    return LaunchClaims(
        user_id=9,
        app_id=15,
        product_id=73,
        entitlement_id=990306,
        request_id="req_verify_1",
    )


def _service(repository: SessionRepository, client: FakeMolingClient) -> AuthService:
    return AuthService(
        moling_client=client,
        session_repository=repository,
        absolute_ttl=timedelta(hours=24),
        idle_ttl=timedelta(hours=2),
        token_factory=lambda: "raw-session-secret",
        now_factory=lambda: NOW,
    )


def _app(service: AuthService, *, secure: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_auth_router(
            auth_service=service,
            cookie_name="trainppt_session",
            cookie_secure=secure,
            trusted_origins=("https://ppt.example.com",),
        )
    )
    return app


def test_enter_creates_hashed_session_and_secure_cookie(repository: SessionRepository) -> None:
    """浏览器只收到原始随机ID，数据库只能保存SHA-256哈希。"""
    service = _service(repository, FakeMolingClient(_claims()))

    with TestClient(_app(service)) as client:
        response = client.get("/enter?ticket=lt_one_time", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    cookie = response.headers["set-cookie"]
    assert "trainppt_session=raw-session-secret" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie

    stored = repository.get_by_raw_token("raw-session-secret")
    assert stored is not None
    assert stored.id != "raw-session-secret"
    assert len(stored.id) == 64
    assert stored.user_id == 9
    assert stored.entitlement_id == 990306


def test_missing_ticket_is_rejected_without_cookie(repository: SessionRepository) -> None:
    """缺少ticket必须在调用平台前失败，错误响应同样禁止缓存和Referrer。"""
    platform = FakeMolingClient(_claims())
    with TestClient(_app(_service(repository, platform))) as client:
        response = client.get("/enter", follow_redirects=False)

    assert response.status_code == 400
    assert platform.calls == 0
    assert "set-cookie" not in response.headers
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            MolingAuthenticationError(
                "鉴权失败", request_id="req_auth", retryable=False, platform_code=40003
            ),
            401,
        ),
        (
            MolingIdentityMismatchError("身份不匹配", request_id="req_scope", retryable=False),
            403,
        ),
        (MolingUnavailableError("平台不可用", request_id="req_timeout", retryable=True), 503),
        (MolingProtocolError("协议错误", request_id="req_protocol", retryable=False), 502),
    ],
)
def test_platform_failure_never_creates_session(
    repository: SessionRepository,
    error: Exception,
    expected_status: int,
    caplog,
) -> None:
    """无效、错域或终态未知票据都不能降级成匿名Session。"""
    platform = FakeMolingClient(error)
    with TestClient(_app(_service(repository, platform))) as client:
        response = client.get("/enter?ticket=lt_hidden", follow_redirects=False)

    assert response.status_code == expected_status
    assert platform.calls == 1
    assert repository.count() == 0
    assert "lt_hidden" not in response.text
    assert "lt_hidden" not in caplog.text
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (
            MolingAuthenticationError(
                "鉴权失败", request_id="req_auth_html", retryable=False, platform_code=40003
            ),
            "expired",
        ),
        (MolingUnavailableError("平台不可用", request_id="req_down_html", retryable=True), "platform"),
    ],
)
def test_browser_entry_failure_redirects_to_safe_auth_page(
    repository: SessionRepository,
    error: Exception,
    reason: str,
) -> None:
    """浏览器导航不展示原始JSON，且重定向地址不能携带一次性ticket。"""
    with TestClient(_app(_service(repository, FakeMolingClient(error)))) as client:
        response = client.get(
            "/enter?ticket=lt_hidden",
            headers={"Accept": "text/html,application/xhtml+xml"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == f"/auth-failure?reason={reason}"
    assert "lt_hidden" not in response.headers["location"]
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("ticket", ["   ", "x" * 513])
def test_malformed_ticket_is_rejected_before_platform_call(
    repository: SessionRepository,
    ticket: str,
) -> None:
    """空白或异常超长ticket不得进入下游请求，也不得创建Session。"""
    platform = FakeMolingClient(_claims())
    with TestClient(_app(_service(repository, platform))) as client:
        response = client.get("/enter", params={"ticket": ticket}, follow_redirects=False)

    assert response.status_code == 400
    assert platform.calls == 0
    assert repository.count() == 0


def test_replayed_ticket_does_not_create_second_session(repository: SessionRepository) -> None:
    """平台拒绝重放后，本地不能留下第二条Session。"""
    class ReplayAwareClient(FakeMolingClient):
        async def verify_launch_ticket(self, launch_ticket: str) -> LaunchClaims:
            self.calls += 1
            if self.calls > 1:
                raise MolingAuthenticationError(
                    "票据已消费", request_id="req_replay", retryable=False, platform_code=40003
                )
            return _claims()

    platform = ReplayAwareClient(_claims())
    app = _app(_service(repository, platform))
    with TestClient(app) as client:
        first = client.get("/enter?ticket=lt_once", follow_redirects=False)
        replay = client.get("/enter?ticket=lt_once", follow_redirects=False)

    assert first.status_code == 302
    assert replay.status_code == 401
    assert repository.count() == 1


def test_successful_relogin_revokes_only_cookie_session(repository: SessionRepository) -> None:
    """同一浏览器成功重新登录后旧Cookie失效，新Cookie对应会话可恢复。"""
    tokens = iter(("browser-old", "browser-new"))
    service = AuthService(
        moling_client=FakeMolingClient(_claims()),
        session_repository=repository,
        absolute_ttl=timedelta(hours=24),
        idle_ttl=timedelta(hours=2),
        token_factory=lambda: next(tokens),
        now_factory=lambda: NOW,
    )
    # TestClient使用HTTP；关闭Secure仅用于验证Cookie往返，生产Secure由独立测试覆盖。
    app = _app(service, secure=False)
    with TestClient(app) as client:
        first = client.get("/enter?ticket=lt_first", follow_redirects=False)
        second = client.get("/enter?ticket=lt_second", follow_redirects=False)

    assert first.status_code == 302
    assert second.status_code == 302
    assert service.resolve_session("browser-old", now=NOW + timedelta(minutes=1)) is None
    assert service.resolve_session("browser-new", now=NOW + timedelta(minutes=1)) is not None


def test_session_absolute_and_idle_expiration_are_fail_closed(repository: SessionRepository) -> None:
    """绝对过期或空闲过期任一满足时都不得恢复用户身份。"""
    tokens = iter(("idle-session", "absolute-session"))
    service = AuthService(
        moling_client=FakeMolingClient(_claims()),
        session_repository=repository,
        absolute_ttl=timedelta(hours=24),
        idle_ttl=timedelta(hours=2),
        token_factory=lambda: next(tokens),
        now_factory=lambda: NOW,
    )
    issued = service.create_session(_claims())

    assert service.resolve_session(issued.raw_token, now=NOW + timedelta(hours=1)) is not None
    assert service.resolve_session(issued.raw_token, now=NOW + timedelta(hours=3)) is None

    second = service.create_session(_claims(), now=NOW)
    assert service.resolve_session(second.raw_token, now=NOW + timedelta(hours=25)) is None


def test_new_login_rotates_session_token(repository: SessionRepository) -> None:
    """同一浏览器再次登录必须撤销旧值并签发新值，其他设备会话不受影响。"""
    tokens = iter(("session-first", "session-second"))
    service = AuthService(
        moling_client=FakeMolingClient(_claims()),
        session_repository=repository,
        absolute_ttl=timedelta(hours=24),
        idle_ttl=timedelta(hours=2),
        token_factory=lambda: next(tokens),
        now_factory=lambda: NOW,
    )

    first = service.create_session(_claims())
    second = service.create_session(_claims())
    service.rotate_existing_session(first.raw_token, now=NOW + timedelta(minutes=1))

    assert first.raw_token != second.raw_token
    assert repository.count() == 2
    assert service.resolve_session(first.raw_token, now=NOW + timedelta(minutes=2)) is None
    assert service.resolve_session(second.raw_token, now=NOW + timedelta(minutes=2)) is not None


def test_session_issue_repr_hides_raw_cookie_value(repository: SessionRepository) -> None:
    """日志或调试输出Session签发结果时不得泄漏原始Cookie值。"""
    issue = _service(repository, FakeMolingClient(_claims())).create_session(_claims())

    assert "raw-session-secret" not in repr(issue)


def test_out_of_order_touches_never_move_last_seen_backwards(repository: SessionRepository) -> None:
    """并发请求乱序提交时，较旧时间不能覆盖已提交的新活动时间。"""
    issue = _service(repository, FakeMolingClient(_claims())).create_session(_claims())
    row = repository.get_by_raw_token(issue.raw_token)
    assert row is not None

    repository.touch(row.id, NOW.replace(tzinfo=None) + timedelta(minutes=20))
    repository.touch(row.id, NOW.replace(tzinfo=None) + timedelta(minutes=10))

    refreshed = repository.get_by_raw_token(issue.raw_token)
    assert refreshed is not None
    assert refreshed.last_seen_at == NOW.replace(tzinfo=None) + timedelta(minutes=20)


def test_repository_never_persists_raw_session_token(repository: SessionRepository) -> None:
    """直接检查持久层，确保原始Cookie值没有进入任意Session列。"""
    service = _service(repository, FakeMolingClient(_claims()))
    service.create_session(_claims())

    with Session(repository.engine) as db:
        row = db.scalar(select(AppSession))
        assert row is not None
        assert "raw-session-secret" not in "|".join(str(value) for value in row.__dict__.values())


@pytest.mark.parametrize("origin", ["https://evil.example", "null", None])
def test_cross_site_or_missing_origin_is_rejected(origin: str | None) -> None:
    """Cookie写接口必须校验可信Origin，CORS不能代替CSRF防护。"""
    with pytest.raises(CsrfOriginError):
        enforce_trusted_origin(origin, ("https://ppt.example.com",))


def test_exact_trusted_origin_is_allowed() -> None:
    """仅完整匹配scheme、host和port的应用Origin可执行写操作。"""
    enforce_trusted_origin("https://ppt.example.com", ("https://ppt.example.com",))


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://PPT.EXAMPLE.com:443/app", "https://ppt.example.com"),
        ("http://ppt.example.com:8080/base", "http://ppt.example.com:8080"),
    ],
)
def test_app_base_url_is_normalized_to_browser_origin(base_url: str, expected: str) -> None:
    """Origin不含路径且会省略默认端口，部署地址必须按浏览器规则规范化。"""
    assert trusted_origin_from_url(base_url) == expected


def test_sso_disables_uvicorn_request_line_logs() -> None:
    """避免`/enter?ticket=`在应用访问日志中落盘；非SSO开发模式仍可保留日志。"""
    assert uvicorn_access_log_enabled(sso_enabled=True) is False
    assert uvicorn_access_log_enabled(sso_enabled=False) is True

    dockerfile = (REPOSITORY_ROOT / "backend/main_api/Dockerfile").read_text(encoding="utf-8")
    assert "--no-access-log" in dockerfile


def test_session_migration_creates_expected_table_and_indexes(tmp_path) -> None:
    """T04迁移必须显式创建Session表、哈希主键和过期/用户索引。"""
    from alembic import command
    from sqlalchemy import inspect

    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert "app_sessions" in inspector.get_table_names()
        assert {column["name"] for column in inspector.get_columns("app_sessions")} == {
            "id",
            "user_id",
            "app_id",
            "product_id",
            "entitlement_id",
            "created_at",
            "expires_at",
            "last_seen_at",
            "revoked_at",
        }
        assert {index["name"] for index in inspector.get_indexes("app_sessions")} == {
            "ix_app_sessions_user_id",
            "ix_app_sessions_expires_at",
        }
    finally:
        engine.dispose()


def test_sso_schema_check_fails_before_serving_when_migration_is_missing(tmp_path) -> None:
    """开启SSO前必须确认Session迁移已执行，禁止等首个真实用户进入才500。"""
    engine = create_engine(f"sqlite:///{(tmp_path / 'missing.db').as_posix()}")
    try:
        repository = SessionRepository(engine)
        with pytest.raises(SessionSchemaError) as exc_info:
            repository.ensure_schema()
        assert str(exc_info.value) == "Session数据库结构未就绪"
    finally:
        engine.dispose()
