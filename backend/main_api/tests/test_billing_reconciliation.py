"""T18 billing_pending自动对账、退避、重启和人工查询测试。"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.main_api.api.tasks import create_tasks_router
from backend.main_api.core.identity import RequestPrincipal
from backend.main_api.integrations.moling import (
    EntitlementFinalization,
    MolingUnavailableError,
)
from backend.main_api.models.base import Base
from backend.main_api.models.domain import BillingOperation, GenerationTask, Presentation
from backend.main_api.repositories.reconciliation import BillingReconciliationRepository
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.schemas.presentations import CreatePresentationRequest
from backend.main_api.services.presentations import PresentationService
from backend.main_api.services.tasks import TaskQueryService
from backend.main_api.workers.reconciliation import BillingReconciliationWorker


START = datetime(2026, 7, 23, 7, 0, 0)


class MutableClock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


class LedgerClient:
    """模拟平台幂等账本；可在响应丢失前先提交终态。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.terminals: dict[str, str] = {}
        self.always_timeout = False

    async def settle_entitlement(self, *, hold_id: str, actual_amount: str, idempotency_key: str):
        self.calls.append(("settle", idempotency_key))
        if self.always_timeout:
            raise MolingUnavailableError("平台暂不可用", request_id="safe", retryable=True)
        self.terminals[idempotency_key] = "settled"
        return EntitlementFinalization(
            hold_id=hold_id, status="settled", settled_amount=actual_amount,
            quota_used=actual_amount, quota_reserved="0", available="92",
        )

    async def release_entitlement(self, *, hold_id: str, idempotency_key: str):
        self.calls.append(("release", idempotency_key))
        if self.always_timeout:
            raise MolingUnavailableError("平台暂不可用", request_id="safe", retryable=True)
        self.terminals[idempotency_key] = "released"
        return EntitlementFinalization(
            hold_id=hold_id, status="released", settled_amount="0",
            quota_used="0", quota_reserved="0", available="100",
        )


class ResultInspector:
    def __init__(self, result: bool | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    async def has_persisted_result(self, task) -> bool:
        self.calls.append(task.task_id)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class SlowLedgerClient(LedgerClient):
    """让首个结算停在平台调用内，用于证明另一 Worker 不会并行重放。"""

    def __init__(self) -> None:
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.active_calls = 0
        self.max_active_calls = 0

    async def settle_entitlement(self, *, hold_id: str, actual_amount: str, idempotency_key: str):
        self.active_calls += 1
        self.max_active_calls = max(self.max_active_calls, self.active_calls)
        self.entered.set()
        await self.release.wait()
        try:
            return await super().settle_entitlement(
                hold_id=hold_id,
                actual_amount=actual_amount,
                idempotency_key=idempotency_key,
            )
        finally:
            self.active_calls -= 1


def _database(tmp_path: Path, *, action: str = "settle"):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'reconciliation.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    ids = iter(("presentation-r", "task-r", "billing-r"))
    result = PresentationService(
        PresentationRepository(engine),
        task_max_attempts=3,
        user_presentation_limit=None,
        billing_enabled=True,
        billing_product_id=73,
        billing_reserve_points=10,
        billing_settle_points=8,
        id_factory=lambda: next(ids),
        now_factory=lambda: START,
    ).create(
        1001, "reconcile-request",
        CreatePresentationRequest(title="待对账作品", content="生成PPT"),
    )
    with sessionmaker(engine).begin() as db:
        operation = db.scalar(select(BillingOperation))
        task = db.scalar(select(GenerationTask))
        presentation = db.scalar(select(Presentation))
        operation.entitlement_id = "81"
        operation.hold_id = "hold-r"
        operation.action = action
        operation.status = "billing_pending"
        operation.last_error_code = f"BILLING_{action.upper()}_UNKNOWN"
        operation.retry_count = 0
        operation.next_retry_at = None
        task.status = "billing_pending"
        task.stage = "billing_pending"
        task.retryable = False
        presentation.status = "billing_pending"
    return engine, result.task.id


def _worker(engine, client, inspector, clock, *, max_retries: int = 3):
    return BillingReconciliationWorker(
        repository=BillingReconciliationRepository(engine),
        client=client,
        result_inspector=inspector,
        base_interval_seconds=10,
        inflight_stale_seconds=20,
        max_retries=max_retries,
        now_factory=clock,
    )


def _states(engine):
    with sessionmaker(engine)() as db:
        return (
            db.scalar(select(Presentation)),
            db.scalar(select(GenerationTask)),
            db.scalar(select(BillingOperation)),
        )


def test_settle_timeout_already_applied_replays_same_key_and_recovers(tmp_path: Path) -> None:
    engine, task_id = _database(tmp_path, action="settle")
    client = LedgerClient()
    client.terminals[f"ppt:{task_id}:settle"] = "settled"
    worker = _worker(engine, client, ResultInspector(True), MutableClock())
    try:
        assert asyncio.run(worker.run_once()) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [("settle", f"ppt:{task_id}:settle")]
        assert operation.status == "settled" and operation.retry_count == 1
        assert task.status == "succeeded" and presentation.status == "ready"
    finally:
        engine.dispose()


def test_release_timeout_replays_same_key_and_never_claims_refund_early(tmp_path: Path) -> None:
    engine, task_id = _database(tmp_path, action="release")
    client = LedgerClient()
    worker = _worker(engine, client, ResultInspector(False), MutableClock())
    try:
        before = _states(engine)
        assert before[0].status == before[1].status == before[2].status == "billing_pending"
        assert asyncio.run(worker.run_once()) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [("release", f"ppt:{task_id}:release")]
        assert operation.status == "released"
        assert task.status == "failed" and presentation.status == "failed"
    finally:
        engine.dispose()


def test_restart_preserves_exponential_backoff_and_stops_at_max_retries(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path, action="settle")
    client = LedgerClient()
    client.always_timeout = True
    clock = MutableClock()
    try:
        first_process = _worker(engine, client, ResultInspector(True), clock, max_retries=3)
        assert asyncio.run(first_process.run_once()) is True
        assert _states(engine)[2].next_retry_at == START + timedelta(seconds=10)

        # 模拟服务重启：新实例必须读取数据库退避时间，而不是从零开始热重试。
        second_process = _worker(engine, client, ResultInspector(True), clock, max_retries=3)
        clock.advance(9)
        assert asyncio.run(second_process.run_once()) is False
        clock.advance(1)
        assert asyncio.run(second_process.run_once()) is True
        assert _states(engine)[2].next_retry_at == START + timedelta(seconds=30)
        clock.advance(20)
        assert asyncio.run(second_process.run_once()) is True

        presentation, task, operation = _states(engine)
        assert len(client.calls) == 3
        assert operation.status == "manual_required"
        assert operation.retry_count == 3 and operation.next_retry_at is None
        assert task.status == presentation.status == "billing_pending"
        clock.advance(3600)
        assert asyncio.run(second_process.run_once()) is False
        assert len(client.calls) == 3
    finally:
        engine.dispose()


def test_inflight_platform_write_must_be_stale_before_reconciliation(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path, action="settle")
    clock = MutableClock()
    client = LedgerClient()
    with sessionmaker(engine).begin() as db:
        operation = db.scalar(select(BillingOperation))
        operation.status = "settling"
        operation.updated_at = START
    worker = _worker(engine, client, ResultInspector(True), clock)
    try:
        # 多 Worker 场景下，刚发出的平台写调用不能被对账进程并行重放。
        assert asyncio.run(worker.run_once()) is False
        assert client.calls == []
        clock.advance(10)
        assert asyncio.run(worker.run_once()) is False
        assert client.calls == []
        clock.advance(10)
        assert asyncio.run(worker.run_once()) is True
        assert client.calls == [("settle", "ppt:task-r:settle")]
    finally:
        engine.dispose()


def test_concurrent_reconciliation_claim_has_only_one_winner(tmp_path: Path) -> None:
    engine, task_id = _database(tmp_path, action="release")
    repository = BillingReconciliationRepository(engine)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(
                lambda _: repository.claim_due(
                    now=START,
                    base_interval_seconds=10,
                    inflight_stale_seconds=20,
                    max_retries=3,
                ),
                range(2),
            ))
        assert [claim.task_id for claim in claims if claim is not None] == [task_id]
        assert _states(engine)[2].retry_count == 1
    finally:
        engine.dispose()


def test_slow_platform_call_is_not_replayed_before_inflight_lease(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path, action="settle")
    clock = MutableClock()

    async def scenario() -> SlowLedgerClient:
        client = SlowLedgerClient()
        first = _worker(engine, client, ResultInspector(True), clock)
        second = _worker(engine, client, ResultInspector(True), clock)
        first_run = asyncio.create_task(first.run_once())
        await client.entered.wait()
        clock.advance(10)
        assert await second.run_once() is False
        client.release.set()
        assert await first_run is True
        return client

    try:
        client = asyncio.run(scenario())
        assert client.max_active_calls == 1
        assert client.calls == [("settle", "ppt:task-r:settle")]
    finally:
        engine.dispose()


def test_default_backoff_and_platform_timeout_lease_are_independent(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path, action="settle")
    try:
        # 默认退避60秒、平台四段超时预算41秒；两者独立生效，不应阻止Worker启动。
        worker = BillingReconciliationWorker(
            repository=BillingReconciliationRepository(engine),
            client=LedgerClient(),
            result_inspector=ResultInspector(True),
            base_interval_seconds=60,
            inflight_stale_seconds=41,
            max_retries=8,
            now_factory=MutableClock(),
        )
        assert worker.base_interval_seconds == 60
        assert worker.inflight_stale_seconds == 41
    finally:
        engine.dispose()


def test_crash_after_final_claim_eventually_converges_to_manual_review(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path, action="settle")
    repository = BillingReconciliationRepository(engine)
    try:
        with sessionmaker(engine).begin() as db:
            operation = db.scalar(select(BillingOperation))
            operation.status = "reconciling"
            operation.retry_count = 3
            operation.next_retry_at = START + timedelta(seconds=10)
        assert repository.claim_due(
            now=START + timedelta(seconds=19),
            base_interval_seconds=10,
            inflight_stale_seconds=20,
            max_retries=3,
        ) is None
        assert _states(engine)[2].status == "reconciling"

        # 模拟最后一次外部写前崩溃：退避到期后只转人工，不再发任何平台请求。
        assert repository.claim_due(
            now=START + timedelta(seconds=20),
            base_interval_seconds=10,
            inflight_stale_seconds=20,
            max_retries=3,
        ) is None
        operation = _states(engine)[2]
        assert operation.status == "manual_required"
        assert operation.next_retry_at is None
        assert operation.last_error_code == "BILLING_RECONCILIATION_INTERRUPTED"
    finally:
        engine.dispose()


def test_inspect_action_chooses_settle_or_release_without_new_reserve(tmp_path: Path) -> None:
    for persisted, expected in ((True, "settle"), (False, "release")):
        case_dir = tmp_path / str(persisted)
        case_dir.mkdir()
        engine, task_id = _database(case_dir, action="inspect")
        client = LedgerClient()
        inspector = ResultInspector(persisted)
        try:
            assert asyncio.run(_worker(engine, client, inspector, MutableClock()).run_once()) is True
            assert inspector.calls == [task_id]
            assert client.calls == [(expected, f"ppt:{task_id}:{expected}")]
        finally:
            engine.dispose()


def test_unknown_reserve_never_replays_and_requires_manual_review(tmp_path: Path) -> None:
    engine, task_id = _database(tmp_path, action="reserve")
    client = LedgerClient()
    try:
        assert asyncio.run(
            _worker(engine, client, ResultInspector(False), MutableClock()).run_once()
        ) is True
        presentation, task, operation = _states(engine)
        assert client.calls == []
        assert operation.status == "manual_required"
        assert operation.last_error_code == "BILLING_RESERVE_REQUIRES_MANUAL_REVIEW"
        assert task.status == presentation.status == "billing_pending"
        assert operation.reserve_key == f"ppt:{task_id}:reserve"
    finally:
        engine.dispose()


def test_task_query_is_owner_scoped_and_never_exposes_billing_secrets(tmp_path: Path) -> None:
    engine, task_id = _database(tmp_path, action="release")

    def principal(x_test_user: int = Header(default=1001)) -> RequestPrincipal:
        return RequestPrincipal(
            user_id=x_test_user, app_id=15, product_id=73,
            knowledge_subject=f"moling:test:15:{x_test_user}",
        )

    app = FastAPI()
    app.include_router(create_tasks_router(
        service=TaskQueryService(BillingReconciliationRepository(engine)),
        principal_dependency=principal,
    ), prefix="/api")
    client = TestClient(app)
    try:
        own = client.get(f"/api/tasks/{task_id}")
        other = client.get(f"/api/tasks/{task_id}", headers={"X-Test-User": "2002"})
        assert own.status_code == 200
        assert other.status_code == 404
        assert own.json()["billing"] == {
            "status": "billing_pending", "action": "release", "retry_count": 0,
            "next_retry_at": None, "manual_required": False,
        }
        rendered = own.text.lower()
        for forbidden in ("hold-r", "ppt:task-r", "entitlement", "reserved_amount", "actual_amount"):
            assert forbidden not in rendered
        assert other.json()["code"] == "TASK_NOT_FOUND"
    finally:
        client.close()
        engine.dispose()
