"""T21 Request ID、限流、审计和依赖健康公开行为测试。"""

from __future__ import annotations

import json
import logging
import pytest

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from backend.main_api.api.health import create_health_router
from backend.main_api.core.health import DependencyProbe, HealthService
from backend.main_api.core.observability import (
    FixedWindowRateLimiter, OperationalSafetyMiddleware, install_safe_exception_handlers,
)


def _app(*, limit: int = 2) -> FastAPI:
    app = FastAPI()
    install_safe_exception_handlers(app)

    @app.post("/critical")
    def critical(request: Request):
        return {"user": request.state.audit_user_id}

    @app.post("/critical/{resource_id}")
    def critical_resource(resource_id: str):
        return {"resource_id": resource_id}

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret-token-must-not-leak")

    @app.get("/downstream")
    def downstream():
        raise HTTPException(status_code=502, detail="https://secret-host/token")

    @app.get("/validated")
    def validated(count: int):
        return {"count": count}

    app.add_middleware(
        OperationalSafetyMiddleware,
        limiter=FixedWindowRateLimiter(limit=limit, window_seconds=60),
        critical_routes={"POST /critical", "POST /critical/*"},
        principal_resolver=lambda request: int(request.headers.get("x-test-user", "1001")),
        audit_enabled=True,
    )
    return app


def test_request_id_is_global_and_unhandled_error_is_stable_chinese() -> None:
    client = TestClient(_app())
    accepted = client.post("/critical", headers={"X-Request-Id": "safe-request-1"})
    assert accepted.headers["x-request-id"] == "safe-request-1"
    generated = client.post("/critical", headers={"X-Request-Id": "bad request id"})
    assert generated.headers["x-request-id"] != "bad request id"

    failed = client.get("/boom")
    assert failed.status_code == 500
    assert failed.json()["code"] == "INTERNAL_ERROR"
    assert failed.json()["message"] == "服务暂时不可用，请稍后重试"
    assert failed.json()["request_id"] == failed.headers["x-request-id"]
    assert "secret-token" not in failed.text

    downstream = client.get("/downstream", headers={"X-Request-Id": "downstream-1"})
    assert downstream.json() == {
        "code": "SERVICE_UNAVAILABLE", "message": "服务暂时不可用，请稍后重试",
        "retryable": True, "request_id": "downstream-1",
    }
    assert "secret-host" not in downstream.text
    invalid = client.get("/validated?count=private-value")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "REQUEST_INVALID"
    assert "private-value" not in invalid.text


def test_user_rate_limit_returns_429_and_does_not_share_quota_between_users() -> None:
    client = TestClient(_app(limit=1))
    assert client.post("/critical", headers={"X-Test-User": "1001"}).status_code == 200
    limited = client.post("/critical", headers={"X-Test-User": "1001"})
    assert limited.status_code == 429
    assert limited.json()["code"] == "RATE_LIMITED"
    assert limited.json()["retryable"] is True
    assert int(limited.headers["retry-after"]) >= 1
    assert client.post("/critical", headers={"X-Test-User": "2002"}).status_code == 200

    resource_client = TestClient(_app(limit=1))
    assert resource_client.post("/critical/one", headers={"X-Test-User": "3003"}).status_code == 200
    assert resource_client.post("/critical/two", headers={"X-Test-User": "3003"}).status_code == 429


def test_audit_log_contains_only_metadata_and_never_body_cookie_or_ticket(caplog) -> None:
    caplog.set_level(logging.INFO, logger="backend.main_api.audit")
    client = TestClient(_app())
    response = client.post(
        "/critical?ticket=launch-secret",
        headers={"Cookie": "trainppt_session=session-secret", "X-Test-User": "1001"},
        content=b'{"prompt":"private-body"}',
    )
    assert response.status_code == 200
    audit = next(json.loads(record.message) for record in caplog.records if record.name == "backend.main_api.audit")
    assert audit["event"] == "mutation"
    assert audit["user_id"] == 1001
    assert audit["path"] == "/critical"
    text = json.dumps(audit)
    assert "launch-secret" not in text
    assert "session-secret" not in text
    assert "private-body" not in text


def test_ready_health_maps_dependency_timeout_without_leaking_exception() -> None:
    def timeout() -> bool:
        raise TimeoutError("https://secret-host/token")

    service = HealthService((
        DependencyProbe("database", True, lambda: True),
        DependencyProbe("storage", True, timeout),
        DependencyProbe("optional_docs", False, lambda: False),
    ))
    app = FastAPI()
    app.include_router(create_health_router(service))
    client = TestClient(app)

    assert client.get("/healthz").json() == {
        "status": "ok",
        "component": "main_api",
        "release_channel": "development",
    }
    ready = client.get("/readyz")
    assert ready.status_code == 503
    assert ready.json() == {
        "status": "not_ready",
        "component": "main_api",
        "release_channel": "development",
        "dependencies": {"database": "up", "storage": "down", "optional_docs": "down"},
    }
    assert "secret-host" not in ready.text


@pytest.mark.parametrize(
    "dependency",
    ["database", "storage", "moling", "outline", "content", "personaldb"],
)
def test_each_required_dependency_failure_is_isolated_and_sanitized(dependency: str) -> None:
    def failed_probe() -> bool:
        raise RuntimeError(f"secret-{dependency}-credential")

    app = FastAPI()
    app.include_router(create_health_router(HealthService((
        DependencyProbe(dependency, True, failed_probe),
    ))))
    response = TestClient(app).get("/readyz")
    assert response.status_code == 503
    assert response.json()["dependencies"] == {dependency: "down"}
    assert "credential" not in response.text


def test_health_routes_publish_immutable_release_identity_when_configured() -> None:
    app = FastAPI()
    app.include_router(create_health_router(
        HealthService((DependencyProbe("database", True, lambda: True),)),
        release_commit="a" * 40,
        release_channel="production",
    ))
    client = TestClient(app)

    for path in ("/healthz", "/readyz"):
        payload = client.get(path).json()
        assert payload["component"] == "main_api"
        assert payload["release_channel"] == "production"
        assert payload["release_commit"] == "a" * 40
