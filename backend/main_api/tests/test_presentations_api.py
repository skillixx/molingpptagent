"""T09 作品 CRUD API、幂等创建、分页和 owner 隔离契约测试。"""

from __future__ import annotations

import os
import json
import asyncio
import base64
import hashlib
import gzip
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.main_api.api.presentations import create_presentations_router
from backend.main_api.core.identity import RequestPrincipal
from backend.main_api.models.base import Base
from backend.main_api.models.domain import BillingOperation, GenerationTask, Presentation, PresentationVersion
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.repositories.resources import PresentationSchemaError
from backend.main_api.repositories.tasks import TaskLeaseRepository
from backend.main_api.schemas.presentations import CreatePresentationRequest
from backend.main_api.services.presentations import PresentationService
from backend.main_api.services.presentations import PresentationServiceError
from backend.main_api.workers.runner import PersistentTaskWorker


TRUSTED_ORIGIN = "https://trainppt.example.com"


@pytest.fixture()
def api(tmp_path: Path):
    """使用真实 SQLite 事务和可控测试身份，不连接当前 MySQL。"""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'presentations.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    def principal(x_test_user: int = Header(default=1001)) -> RequestPrincipal:
        return RequestPrincipal(
            user_id=x_test_user,
            app_id=15,
            product_id=73,
            knowledge_subject=f"moling:test:15:{x_test_user}",
        )

    app = FastAPI()
    app.include_router(
        create_presentations_router(
            service=PresentationService(
                PresentationRepository(engine),
                task_max_attempts=3,
                user_presentation_limit=None,
            ),
            principal_dependency=principal,
            trusted_origins=(TRUSTED_ORIGIN,),
            csrf_enabled=True,
        ),
        prefix="/api",
    )
    client = TestClient(app)
    yield client, engine
    client.close()
    engine.dispose()


@pytest.fixture()
def billing_api(tmp_path: Path):
    """开启本地计费意图但不配置任何平台调用，验证T16只持久化、不扣费。"""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'billing-presentations.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    def principal(x_test_user: int = Header(default=1001)) -> RequestPrincipal:
        return RequestPrincipal(
            user_id=x_test_user, app_id=15, product_id=73,
            knowledge_subject=f"moling:test:15:{x_test_user}",
            entitlement_id=990306,
        )

    app = FastAPI()
    app.include_router(create_presentations_router(
        service=PresentationService(
            PresentationRepository(engine),
            task_max_attempts=3,
            user_presentation_limit=None,
            billing_enabled=True,
            billing_product_id=73,
            billing_reserve_points=20,
            billing_settle_points=15,
        ),
        principal_dependency=principal,
        trusted_origins=(TRUSTED_ORIGIN,),
        csrf_enabled=True,
    ), prefix="/api")
    client = TestClient(app)
    yield client, engine
    client.close()
    engine.dispose()


def _create(
    client: TestClient,
    *,
    key: str,
    title: str = "季度汇报",
    content: str = "生成一份季度经营汇报",
    user_id: int = 1001,
):
    return client.post(
        "/api/presentations",
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Idempotency-Key": key,
            "X-Test-User": str(user_id),
            "X-Request-Id": f"http-{key}",
        },
        json={"title": title, "content": content, "language": "chinese"},
    )


def _save_draft(
    client: TestClient,
    *,
    key: str,
    user_id: int = 1001,
    title: str = "Linux 入门",
):
    """模拟编辑器把临时session稿保存到当前用户作品库。"""
    return client.post(
        "/api/presentations/drafts",
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Idempotency-Key": key,
            "X-Test-User": str(user_id),
            "X-Request-Id": f"draft-{key}",
        },
        json={
            "title": title,
            "template_id": "template_1",
            "slides": {
                "schema_version": 1,
                "slides": [{"id": "slide-1", "elements": [], "remark": "临时稿"}],
                "theme": {},
                "viewport_size": 1000,
                "viewport_ratio": 0.5625,
            },
        },
    )


def test_save_draft_creates_editable_work_without_generation_or_billing_task(api) -> None:
    client, engine = api

    first = _save_draft(client, key="save-session-1")
    retry = _save_draft(client, key="save-session-1")

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["reused"] is True
    assert retry.json()["presentation"]["id"] == first.json()["presentation"]["id"]
    assert first.json()["presentation"]["status"] == "draft"
    assert first.json()["presentation"]["slides"]["slides"][0]["remark"] == "临时稿"
    assert first.headers["x-request-id"] == "draft-save-session-1"

    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 1
        assert db.scalar(select(func.count()).select_from(GenerationTask)) == 0
        saved = db.scalar(select(Presentation))
        assert saved is not None and saved.owner_user_id == 1001


def test_save_draft_idempotency_is_owner_scoped_and_rejects_changed_payload(api) -> None:
    client, engine = api

    owner_a = _save_draft(client, key="shared-session", user_id=1001)
    owner_b = _save_draft(client, key="shared-session", user_id=2002)
    changed = _save_draft(client, key="shared-session", user_id=1001, title="不同内容")

    assert owner_a.status_code == owner_b.status_code == 201
    assert owner_a.json()["presentation"]["id"] != owner_b.json()["presentation"]["id"]
    assert changed.status_code == 409
    assert changed.json()["code"] == "PRESENTATION_REQUEST_CONFLICT"
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 2


def test_create_atomically_persists_owner_presentation_and_task(api) -> None:
    client, engine = api
    response = _create(client, key="create-001")

    assert response.status_code == 202
    body = response.json()
    assert body["reused"] is False
    assert body["presentation"]["title"] == "季度汇报"
    assert body["presentation"]["status"] == "generating"
    assert body["task"]["status"] == "pending"
    assert body["task"]["stage"] == "queued"
    assert response.headers["x-request-id"] == "http-create-001"

    factory = sessionmaker(engine)
    with factory() as db:
        presentation = db.scalar(select(Presentation))
        task = db.scalar(select(GenerationTask))
        assert presentation is not None and task is not None
        assert presentation.owner_user_id == 1001
        assert task.owner_user_id == 1001
        assert task.presentation_id == presentation.id
        assert task.request_id == "create-001"
        assert "季度经营汇报" in task.input_json
        input_payload = json.loads(task.input_json)
        assert input_payload["generate_from_uploaded_file"] is False
        assert input_payload["generate_from_web_search"] is True


def test_create_retry_reuses_same_task_and_never_duplicates_rows(api) -> None:
    client, engine = api
    first = _create(client, key="same-business-request")
    second = _create(client, key="same-business-request")

    assert first.status_code == second.status_code == 202
    assert second.json()["reused"] is True
    assert second.json()["presentation"]["id"] == first.json()["presentation"]["id"]
    assert second.json()["task"]["id"] == first.json()["task"]["id"]
    factory = sessionmaker(engine)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 1
        assert db.scalar(select(func.count()).select_from(GenerationTask)) == 1


def test_same_client_idempotency_key_is_namespaced_by_owner(api) -> None:
    client, engine = api
    first = _create(client, key="globally-stable-key", user_id=1001)
    second_owner = _create(client, key="globally-stable-key", user_id=2002)
    assert first.status_code == second_owner.status_code == 202
    assert first.json()["task"]["id"] != second_owner.json()["task"]["id"]
    factory = sessionmaker(engine)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 2
        assert db.scalar(select(func.count()).select_from(GenerationTask)) == 2


def test_same_owner_key_with_different_business_payload_is_rejected(api) -> None:
    client, _ = api
    assert _create(client, key="incompatible-key", title="原请求", content="原内容").status_code == 202
    changed = _create(client, key="incompatible-key", title="不同请求", content="不同内容")
    assert changed.status_code == 409
    assert changed.json()["code"] == "PRESENTATION_REQUEST_CONFLICT"


def test_billing_task_is_atomically_planned_and_not_claimable_before_reserve(billing_api) -> None:
    client, engine = billing_api
    created = _create(client, key="billing-task-1")
    repeated = _create(client, key="billing-task-1")
    assert created.status_code == repeated.status_code == 202
    assert repeated.json()["reused"] is True
    assert created.json()["presentation"]["status"] == "billing_pending"
    assert created.json()["task"]["status"] == "billing_required"
    assert created.json()["task"]["stage"] == "awaiting_reserve"

    with sessionmaker(engine)() as db:
        task = db.scalar(select(GenerationTask))
        operation = db.scalar(select(BillingOperation))
        assert task is not None and operation is not None
        assert operation.task_id == task.id
        assert operation.owner_user_id == task.owner_user_id == 1001
        assert operation.product_id == 73
        assert operation.entitlement_id == 990306 and operation.hold_id is None
        assert operation.status == "planned"
        assert operation.reserved_amount == 20
        assert operation.actual_amount == 15
        assert operation.reserve_key == f"ppt:{task.id}:reserve"
        assert operation.settle_key == f"ppt:{task.id}:settle"
        assert operation.release_key == f"ppt:{task.id}:release"
        assert db.scalar(select(func.count()).select_from(BillingOperation)) == 1
    agent_calls: list[str] = []

    class CountingHandler:
        """若计费闸门失效就记录调用；正常情况下两个方法都不应执行。"""

        async def execute(self, task) -> None:
            agent_calls.append(task.request_id)

        async def has_persisted_result(self, task) -> bool:
            agent_calls.append(f"probe:{task.request_id}")
            return False

    worker = PersistentTaskWorker(
        repository=TaskLeaseRepository(engine),
        handler=CountingHandler(),
        worker_id="worker-t16",
        lease_seconds=120,
        heartbeat_seconds=30,
        retry_backoff_seconds=10,
        claim_batch_size=10,
        agent_timeout_seconds=30,
        clock=lambda: datetime(2026, 7, 23, 6, 30, 0),
    )
    assert asyncio.run(worker.run_once()) is False
    assert agent_calls == []


def test_billing_task_without_ticket_bound_entitlement_fails_before_persistence(
    billing_api,
) -> None:
    """收费开启时禁止回退到按商品猜选，缺少票据权益必须 fail-closed。"""
    _, engine = billing_api
    service = PresentationService(
        PresentationRepository(engine),
        task_max_attempts=3,
        user_presentation_limit=None,
        billing_enabled=True,
        billing_product_id=73,
        billing_reserve_points=1,
        billing_settle_points=1,
    )
    with pytest.raises(PresentationServiceError) as exc_info:
        service.create(
            479,
            "missing-entitlement",
            CreatePresentationRequest(title="拒绝猜选", content="不应创建任务"),
        )
    assert exc_info.value.code == "BILLING_ENTITLEMENT_REQUIRED"
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(GenerationTask)) == 0
        assert db.scalar(select(func.count()).select_from(BillingOperation)) == 0


def test_concurrent_billing_request_creates_one_task_and_operation(billing_api) -> None:
    client, engine = billing_api
    barrier = threading.Barrier(2)
    second_client = TestClient(client.app)

    def create(which: int):
        barrier.wait(timeout=5)
        return (client if which == 1 else second_client).post(
            "/api/presentations",
            headers={"Origin": TRUSTED_ORIGIN, "Idempotency-Key": "billing-concurrent"},
            json={"title": "并发收费任务", "content": "相同业务输入", "language": "chinese"},
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(create, (1, 2)))
    finally:
        second_client.close()
    assert [response.status_code for response in responses] == [202, 202]
    assert len({response.json()["task"]["id"] for response in responses}) == 1
    assert sorted(response.json()["reused"] for response in responses) == [False, True]
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 1
        assert db.scalar(select(func.count()).select_from(GenerationTask)) == 1
        assert db.scalar(select(func.count()).select_from(BillingOperation)) == 1


def test_billing_request_retry_reuses_task_after_billing_state_progresses(billing_api) -> None:
    """前端刷新可能晚于reserve；幂等复用不能把合法状态推进误判成载荷冲突。"""
    client, engine = billing_api
    created = _create(client, key="billing-progress-retry")
    assert created.status_code == 202
    with sessionmaker(engine).begin() as db:
        operation = db.scalar(select(BillingOperation))
        assert operation is not None
        operation.status = "reserved"
        operation.action = "settle"

    repeated = _create(client, key="billing-progress-retry")
    assert repeated.status_code == 202
    assert repeated.json()["reused"] is True
    assert repeated.json()["task"]["id"] == created.json()["task"]["id"]


def test_client_owner_field_is_rejected_instead_of_changing_scope(api) -> None:
    client, _ = api
    response = client.post(
        "/api/presentations",
        headers={"Origin": TRUSTED_ORIGIN, "Idempotency-Key": "owner-forge"},
        json={"title": "伪造", "content": "测试", "owner_user_id": 9999},
    )
    assert response.status_code == 422


def test_list_supports_empty_pagination_search_status_and_sort(api) -> None:
    client, _ = api
    empty = client.get("/api/presentations")
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "page": 1, "page_size": 20, "total": 0, "has_more": False}

    for key, title in (("list-1", "Alpha 周报"), ("list-2", "Beta 月报"), ("list-3", "Alpha 年报")):
        assert _create(client, key=key, title=title).status_code == 202

    page = client.get(
        "/api/presentations",
        params={"page": 1, "page_size": 1, "search": "Alpha", "status": "generating", "sort": "title_asc"},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["has_more"] is True
    assert page.json()["items"][0]["title"] == "Alpha 周报"

    second_page = client.get(
        "/api/presentations",
        params={"page": 2, "page_size": 1, "search": "Alpha", "sort": "title_asc"},
    )
    assert second_page.json()["items"][0]["title"] == "Alpha 年报"


def test_list_never_returns_other_users_presentations(api) -> None:
    client, _ = api
    assert _create(client, key="owner-a", title="用户A", user_id=1001).status_code == 202
    assert _create(client, key="owner-b", title="用户B", user_id=2002).status_code == 202

    owner_a = client.get("/api/presentations", headers={"X-Test-User": "1001"}).json()
    owner_b = client.get("/api/presentations", headers={"X-Test-User": "2002"}).json()
    assert [item["title"] for item in owner_a["items"]] == ["用户A"]
    assert [item["title"] for item in owner_b["items"]] == ["用户B"]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"search": "x" * 101},
        {"status": "unknown"},
        {"sort": "raw_sql"},
    ],
)
def test_list_rejects_invalid_bounds_and_enums(api, params) -> None:
    response = api[0].get("/api/presentations", params=params)
    assert response.status_code in {400, 422}


def test_detail_hides_other_deleted_and_missing_resources_with_same_404(api) -> None:
    client, _ = api
    created = _create(client, key="detail-1").json()["presentation"]
    own = client.get(f"/api/presentations/{created['id']}")
    other = client.get(f"/api/presentations/{created['id']}", headers={"X-Test-User": "2002"})
    missing = client.get("/api/presentations/00000000-0000-0000-0000-000000000000")

    assert own.status_code == 200
    assert own.json()["slides"] == {"slides": []}
    assert other.status_code == missing.status_code == 404
    assert other.json()["code"] == missing.json()["code"] == "PRESENTATION_NOT_FOUND"

    deleted = client.delete(
        f"/api/presentations/{created['id']}", headers={"Origin": TRUSTED_ORIGIN}
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/presentations/{created['id']}").status_code == 404


def test_delete_is_idempotent_for_owner_but_other_owner_gets_404(api) -> None:
    client, _ = api
    presentation_id = _create(client, key="delete-1").json()["presentation"]["id"]
    other = client.delete(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
    )
    first = client.delete(
        f"/api/presentations/{presentation_id}", headers={"Origin": TRUSTED_ORIGIN}
    )
    repeated = client.delete(
        f"/api/presentations/{presentation_id}", headers={"Origin": TRUSTED_ORIGIN}
    )
    assert other.status_code == 404
    other_create = client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
        json={"base_version": 1, "reason": "manual"},
    )
    assert other_create.status_code == 404
    assert first.status_code == repeated.status_code == 204


def test_duplicate_copies_editable_content_only_for_owner(api) -> None:
    client, _ = api
    source = _create(client, key="duplicate-source", title="源作品").json()["presentation"]
    other = client.post(
        f"/api/presentations/{source['id']}/duplicate",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
        json={},
    )
    copied = client.post(
        f"/api/presentations/{source['id']}/duplicate",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"title": "源作品副本"},
    )

    assert other.status_code == 404
    assert copied.status_code == 201
    assert copied.json()["id"] != source["id"]
    assert copied.json()["title"] == "源作品副本"
    assert copied.json()["slides"] == {"slides": []}
    assert copied.json()["current_version"] == 1

    default_title = client.post(
        f"/api/presentations/{source['id']}/duplicate",
        headers={"Origin": TRUSTED_ORIGIN},
        json={},
    )
    assert default_title.status_code == 201
    assert default_title.json()["title"] == "源作品 副本"


def test_create_and_duplicate_both_respect_configured_user_limit(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'quota.db').as_posix()}")
    Base.metadata.create_all(engine)
    service = PresentationService(
        PresentationRepository(engine),
        task_max_attempts=3,
        user_presentation_limit=1,
    )
    try:
        created = service.create(
            1001,
            "quota-first",
            CreatePresentationRequest(title="第一份", content="测试容量"),
        )
        with pytest.raises(PresentationServiceError) as create_error:
            service.create(
                1001,
                "quota-second",
                CreatePresentationRequest(title="第二份", content="测试容量"),
            )
        with pytest.raises(PresentationServiceError) as duplicate_error:
            service.duplicate(1001, created.presentation.id, None)
        assert create_error.value.code == duplicate_error.value.code == "PRESENTATION_LIMIT_REACHED"
    finally:
        engine.dispose()


@pytest.mark.parametrize("method,path", [("post", "/api/presentations"), ("delete", "/api/presentations/missing")])
def test_cross_site_mutations_are_rejected(api, method: str, path: str) -> None:
    client, _ = api
    kwargs = {"headers": {"Origin": "https://evil.example", "Idempotency-Key": "csrf"}}
    if method == "post":
        kwargs["json"] = {"title": "跨站", "content": "不应创建"}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_ORIGIN_REJECTED"


def test_invalid_title_and_idempotency_key_fail_before_database_write(api) -> None:
    client, engine = api
    long_title = _create(client, key="long-title", title="标" * 256)
    bad_key = _create(client, key="contains space")
    assert long_title.status_code == 422
    assert bad_key.status_code == 400
    assert bad_key.json()["code"] == "PRESENTATION_IDEMPOTENCY_KEY_INVALID"
    factory = sessionmaker(engine)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Presentation)) == 0


def test_openapi_freezes_crud_paths_and_response_models(api) -> None:
    schema = api[0].get("/openapi.json").json()
    paths = schema["paths"]
    assert {"get", "post"}.issubset(paths["/api/presentations"])
    assert {"get", "delete"}.issubset(paths["/api/presentations/{presentation_id}"])
    assert "post" in paths["/api/presentations/{presentation_id}/duplicate"]
    assert {"get", "post"}.issubset(paths["/api/presentations/{presentation_id}/versions"])
    assert "post" in paths["/api/presentations/{presentation_id}/versions/{version}/restore"]
    assert "202" in paths["/api/presentations"]["post"]["responses"]
    assert "400" in paths["/api/presentations"]["post"]["responses"]
    assert "201" in paths["/api/presentations/{presentation_id}/duplicate"]["post"]["responses"]
    assert "500" in paths["/api/presentations/{presentation_id}"]["get"]["responses"]
    assert "503" in paths["/api/presentations/{presentation_id}/versions"]["post"]["responses"]


def test_corrupted_stored_slides_returns_stable_error_without_raw_data(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="corrupted-json").json()["presentation"]["id"]
    factory = sessionmaker(engine)
    with factory.begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.slides_json = "{secret-invalid-json"

    response = client.get(f"/api/presentations/{presentation_id}")
    assert response.status_code == 500
    assert response.json()["code"] == "PRESENTATION_DATA_INVALID"
    assert "secret-invalid-json" not in response.text


def test_detail_loads_exact_10_mib_utf8_draft(api) -> None:
    """10MiB上限内的当前稿必须可恢复，不用小样本代替容量边界。"""
    client, engine = api
    presentation_id = _create(client, key="ten-mib-detail").json()["presentation"]["id"]
    prefix = '{"schema_version":1,"slides":[{"id":"boundary","elements":[],"remark":"'
    suffix = '"}]}'
    padding = 10 * 1024 * 1024 - len(prefix.encode("utf-8")) - len(suffix.encode("utf-8"))
    slides_json = f"{prefix}{'x' * padding}{suffix}"
    assert len(slides_json.encode("utf-8")) == 10 * 1024 * 1024

    factory = sessionmaker(engine)
    with factory.begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.slides_json = slides_json
        presentation.status = "ready"
        presentation.slide_count = 1

    response = client.get(f"/api/presentations/{presentation_id}")
    assert response.status_code == 200
    assert response.json()["slides"]["slides"][0]["id"] == "boundary"
    assert len(response.json()["slides"]["slides"][0]["remark"]) == padding


def test_patch_saves_current_draft_and_increments_version(api) -> None:
    """保存当前稿时必须携带已加载的服务端版本。"""
    client, engine = api
    presentation_id = _create(client, key="save-current-draft").json()["presentation"]["id"]
    factory = sessionmaker(engine)
    with factory.begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"

    response = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN, "X-Request-Id": "save-request-1"},
        json={
            "base_version": 1,
            "title": "已保存标题",
            "slides": {
                "schema_version": 1,
                "slides": [{"id": "slide-1", "elements": [], "remark": "已保存"}],
                "viewport_size": 1000,
                "viewport_ratio": 0.5625,
            },
        },
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "save-request-1"
    assert response.json()["current_version"] == 2
    assert response.json()["slide_count"] == 1
    with factory() as db:
        saved = db.get(Presentation, presentation_id)
        assert saved is not None
        assert saved.owner_user_id == 1001
        assert saved.title == "已保存标题"
        assert saved.current_version == 2
        assert json.loads(saved.slides_json)["slides"][0]["remark"] == "已保存"


def test_patch_rejects_other_deleted_missing_and_non_editable_presentations(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="save-owner-scope").json()["presentation"]["id"]
    payload = {"base_version": 1, "title": "不能覆盖", "slides": {"schema_version": 1, "slides": []}}

    other = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
        json=payload,
    )
    missing = client.patch(
        "/api/presentations/00000000-0000-0000-0000-000000000000",
        headers={"Origin": TRUSTED_ORIGIN},
        json=payload,
    )
    # 生成中作品不能通过直接URL绕过状态门禁进入编辑保存。
    generating = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json=payload,
    )
    assert other.status_code == missing.status_code == 404
    assert other.json()["code"] == missing.json()["code"] == "PRESENTATION_NOT_FOUND"
    assert generating.status_code == 409
    assert generating.json()["code"] == "PRESENTATION_NOT_EDITABLE"

    with sessionmaker(engine)() as db:
        unchanged = db.get(Presentation, presentation_id)
        assert unchanged is not None
        assert unchanged.title != "不能覆盖"
        assert unchanged.current_version == 1


def test_patch_enforces_utf8_10_mib_limit_and_document_shape(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="save-size-limit").json()["presentation"]["id"]
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"

    prefix = '{"schema_version":1,"slides":[{"id":"boundary","elements":[],"remark":"'
    suffix = '"}]}'
    exact_padding = 10 * 1024 * 1024 - len(prefix.encode("utf-8")) - len(suffix.encode("utf-8"))
    exact_document = json.loads(f"{prefix}{'x' * exact_padding}{suffix}")
    exact = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "title": "边界稿", "slides": exact_document},
    )
    assert exact.status_code == 200

    exact_document["slides"][0]["remark"] += "x"
    oversized = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 2, "title": "超限稿", "slides": exact_document},
    )
    malformed = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 2, "title": "损坏稿", "slides": {"schema_version": 1, "slides": [{"id": "x"}]}},
    )
    malformed_element = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json={
            "base_version": 2,
            "title": "损坏元素",
            "slides": {
                "schema_version": 1,
                "slides": [{"id": "x", "elements": [{"id": "secret", "type": 7}]}],
            },
        },
    )
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "PRESENTATION_DOCUMENT_TOO_LARGE"
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "PRESENTATION_DOCUMENT_INVALID"
    assert malformed_element.status_code == 422
    assert malformed_element.json()["code"] == "PRESENTATION_DOCUMENT_INVALID"
    assert "remark" not in oversized.text


def test_patch_requires_trusted_origin_and_openapi_contract(api) -> None:
    client, _ = api
    presentation_id = _create(client, key="save-origin").json()["presentation"]["id"]
    response = client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": "https://evil.example"},
        json={"base_version": 1, "title": "跨站", "slides": {"schema_version": 1, "slides": []}},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_ORIGIN_REJECTED"
    operation = client.get("/openapi.json").json()["paths"][
        "/api/presentations/{presentation_id}"
    ]["patch"]
    assert {"200", "403", "404", "409", "413", "422"}.issubset(operation["responses"])


def test_patch_optimistic_lock_allows_only_one_writer_for_same_base_version(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="optimistic-lock").json()["presentation"]["id"]
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"

    barrier = threading.Barrier(2)
    second_client = TestClient(client.app)

    def save(label: str):
        barrier.wait(timeout=5)
        return (client if label == "a" else second_client).patch(
            f"/api/presentations/{presentation_id}",
            headers={"Origin": TRUSTED_ORIGIN},
            json={
                "base_version": 1,
                "title": f"标签{label.upper()}保存",
                "slides": {"schema_version": 1, "slides": [{"id": label, "elements": []}]},
            },
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(save, ("a", "b")))
    finally:
        second_client.close()

    succeeded = next(response for response in responses if response.status_code == 200)
    conflicted = next(response for response in responses if response.status_code == 409)
    winning_id = succeeded.json()["slides"]["slides"][0]["id"]
    assert succeeded.json()["current_version"] == 2
    assert conflicted.json()["code"] == "PRESENTATION_VERSION_CONFLICT"
    assert conflicted.json()["latest"] == {
        "title": f"标签{winning_id.upper()}保存",
        "current_version": 2,
        "updated_at": succeeded.json()["updated_at"],
    }
    assert "slides" not in conflicted.json()["latest"]
    detail = client.get(f"/api/presentations/{presentation_id}").json()
    assert detail["title"] == f"标签{winning_id.upper()}保存"
    assert detail["slides"]["slides"][0]["id"] == winning_id


def test_duplicate_can_atomically_preserve_conflicting_local_draft_at_version_one(api) -> None:
    client, engine = api
    source_id = _create(client, key="conflict-copy", title="源作品").json()["presentation"]["id"]
    with sessionmaker(engine).begin() as db:
        source = db.get(Presentation, source_id)
        assert source is not None
        source.status = "ready"

    other = client.post(
        f"/api/presentations/{source_id}/duplicate",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
        json={
            "title": "越权副本",
            "slides": {"schema_version": 1, "slides": [{"id": "local", "elements": []}]},
        },
    )
    copied = client.post(
        f"/api/presentations/{source_id}/duplicate",
        headers={"Origin": TRUSTED_ORIGIN},
        json={
            "title": "冲突稿副本",
            "slides": {
                "schema_version": 1,
                "slides": [{"id": "local", "elements": [], "remark": "本地冲突内容"}],
            },
        },
    )

    assert other.status_code == 404
    assert copied.status_code == 201
    assert copied.json()["id"] != source_id
    assert copied.json()["current_version"] == 1
    assert copied.json()["title"] == "冲突稿副本"
    assert copied.json()["slides"]["slides"][0]["remark"] == "本地冲突内容"
    factory = sessionmaker(engine)
    with factory() as db:
        copy_row = db.get(Presentation, copied.json()["id"])
        source_row = db.get(Presentation, source_id)
        assert copy_row is not None and copy_row.owner_user_id == 1001
        assert copy_row.current_version == 1
        assert source_row is not None and source_row.title == "源作品"


def test_checkpoint_create_list_is_idempotent_unique_and_owner_scoped(api) -> None:
    """同一作品版本只能有一个检查点，且列表不泄露正文或跨owner数据。"""
    client, engine = api
    presentation_id = _create(client, key="checkpoint-list").json()["presentation"]["id"]
    document = {"schema_version": 1, "slides": [{"id": "v1", "elements": [], "remark": "版本一"}]}
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"
        presentation.slides_json = json.dumps(document, ensure_ascii=False)
        presentation.slide_count = 1

    first = client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "reason": "manual"},
    )
    repeated = client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "reason": "manual"},
    )
    listed = client.get(f"/api/presentations/{presentation_id}/versions")
    other = client.get(
        f"/api/presentations/{presentation_id}/versions",
        headers={"X-Test-User": "2002"},
    )

    assert first.status_code == 201
    assert repeated.status_code == 200
    assert first.json() == repeated.json()
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["version"] == 1
    assert listed.json()["items"][0]["reason"] == "manual"
    assert listed.json()["items"][0]["content_sha256"] == hashlib.sha256(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert "slides" not in listed.text
    assert other.status_code == 404


def test_restore_creates_new_version_without_overwriting_history(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="checkpoint-restore").json()["presentation"]["id"]
    v1 = {"schema_version": 1, "slides": [{"id": "v1", "elements": [], "remark": "历史版本"}]}
    v2 = {"schema_version": 1, "slides": [{"id": "v2", "elements": [], "remark": "当前版本"}]}
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"
        presentation.slides_json = json.dumps(v1, ensure_ascii=False)
        presentation.slide_count = 1

    assert client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "reason": "manual"},
    ).status_code == 201
    assert client.patch(
        f"/api/presentations/{presentation_id}",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "title": "版本二", "slides": v2},
    ).status_code == 200
    assert client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 2, "reason": "ai"},
    ).status_code == 201

    restored = client.post(
        f"/api/presentations/{presentation_id}/versions/1/restore",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 2},
    )
    stale = client.post(
        f"/api/presentations/{presentation_id}/versions/2/restore",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 2},
    )

    assert restored.status_code == 200
    assert restored.json()["current_version"] == 3
    assert restored.json()["slides"] == v1
    assert stale.status_code == 409
    assert stale.json()["code"] == "PRESENTATION_VERSION_CONFLICT"
    listed = client.get(f"/api/presentations/{presentation_id}/versions").json()["items"]
    assert [item["version"] for item in listed] == [3, 2, 1]
    assert [item["reason"] for item in listed] == ["restore", "ai", "manual"]
    assert listed[0]["content_sha256"] == listed[2]["content_sha256"]
    assert listed[1]["content_sha256"] != listed[2]["content_sha256"]
    other_restore = client.post(
        f"/api/presentations/{presentation_id}/versions/1/restore",
        headers={"Origin": TRUSTED_ORIGIN, "X-Test-User": "2002"},
        json={"base_version": 3},
    )
    assert other_restore.status_code == 404
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(PresentationVersion)) == 3


def test_checkpoint_retention_keeps_latest_twenty_after_new_version_commits(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="checkpoint-retention").json()["presentation"]["id"]
    factory = sessionmaker(engine)
    for version in range(1, 23):
        with factory.begin() as db:
            presentation = db.get(Presentation, presentation_id)
            assert presentation is not None
            presentation.status = "ready"
            presentation.current_version = version
            presentation.slides_json = json.dumps(
                {"schema_version": 1, "slides": [{"id": f"v{version}", "elements": []}]}
            )
            presentation.slide_count = 1
        response = client.post(
            f"/api/presentations/{presentation_id}/versions",
            headers={"Origin": TRUSTED_ORIGIN},
            json={"base_version": version, "reason": "periodic"},
        )
        assert response.status_code == 201

    versions = client.get(f"/api/presentations/{presentation_id}/versions").json()["items"]
    assert len(versions) == 20
    assert [item["version"] for item in versions] == list(range(22, 2, -1))


def test_checkpoint_rejects_large_compressed_body_without_storage(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="checkpoint-large").json()["presentation"]["id"]
    # 随机字节先转成合法JSON字符串，确保gzip后仍真实超过1MiB内联阈值。
    noisy = base64.b64encode(os.urandom(1100 * 1024)).decode("ascii")
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"
        presentation.slides_json = json.dumps(
            {"schema_version": 1, "slides": [{"id": "large", "elements": [], "remark": noisy}]}
        )
        presentation.slide_count = 1

    response = client.post(
        f"/api/presentations/{presentation_id}/versions",
        headers={"Origin": TRUSTED_ORIGIN},
        json={"base_version": 1, "reason": "export"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "CHECKPOINT_STORAGE_UNAVAILABLE"
    assert noisy[:32] not in response.text
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(PresentationVersion)) == 0


def test_checkpoint_zip_bomb_is_bounded_and_returns_stable_error(api) -> None:
    client, engine = api
    presentation_id = _create(client, key="checkpoint-zip-bomb").json()["presentation"]["id"]
    compressed = gzip.compress(b'x' * (10 * 1024 * 1024 + 1), mtime=0)
    envelope = json.dumps({
        "format": "gzip+base64-v1",
        "data": base64.b64encode(compressed).decode("ascii"),
    })
    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, presentation_id)
        assert presentation is not None
        presentation.status = "ready"
        db.add(PresentationVersion(
            id="zip-bomb-version",
            presentation_id=presentation_id,
            version=1,
            slides_json=envelope,
            reason="manual",
            created_by=1001,
            created_at=presentation.created_at,
        ))

    response = client.get(f"/api/presentations/{presentation_id}/versions")
    assert response.status_code == 500
    assert response.json()["code"] == "PRESENTATION_VERSION_DATA_INVALID"
    assert "gzip" not in response.text


def test_missing_migration_fails_schema_check_with_stable_error(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        with pytest.raises(PresentationSchemaError) as exc_info:
            PresentationRepository(engine).ensure_schema()
        assert str(exc_info.value) == "作品数据表迁移未完成"
    finally:
        engine.dispose()


def test_main_app_registers_internal_proxy_route_only_when_persistence_is_enabled(tmp_path: Path) -> None:
    """使用实际main装配验证代理内路径和旧生成路由同时存在，不用Mock监听冒充验收。"""
    database_path = tmp_path / "main-app.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    repository_root = Path(__file__).resolve().parents[3]
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": database_url,
            "PERSISTENCE_ENABLED": "true",
            "SSO_ENABLED": "false",
            "STORAGE_ENABLED": "true",
            "STORAGE_ENDPOINT": "https://storage.example.test",
            "STORAGE_BUCKET": "trainppt-test",
            "STORAGE_ACCESS_KEY_ID": "fake-access-key",
                "STORAGE_SECRET_ACCESS_KEY": "fake-secret-key",
                "DOWNLOAD_SIGNING_SECRET": "test-download-signing-secret-32-bytes",
            "USER_PRESENTATION_LIMIT": "100",
            "USER_STORAGE_QUOTA_BYTES": "1073741824",
            "BILLING_ENABLED": "false",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main; "
                "from fastapi.testclient import TestClient; "
                "client=TestClient(main.app); "
                "created=client.post('/presentations', headers={'Idempotency-Key':'main-real'}, "
                "json={'title':'Main装配','content':'验证实际路由'}); "
                "listed=client.get('/presentations'); "
                "paths={r.path for r in main.app.routes if hasattr(r, 'path')}; "
                "print(created.status_code, listed.json()['total'], "
                "'/tools/aippt_outline' in paths)"
            ),
        ],
        cwd=repository_root / "backend/main_api",
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "202 1 True"
