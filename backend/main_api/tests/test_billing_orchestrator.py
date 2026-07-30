"""T17 reserve/settle/release 外层编排与持久状态机测试。"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import threading

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from backend.main_api.integrations.moling import (
    EntitlementBalance,
    EntitlementFinalization,
    EntitlementReservation,
    MolingBusinessError,
    MolingUnavailableError,
)
from backend.main_api.models.base import Base
from backend.main_api.models.domain import BillingOperation, GenerationTask, Presentation
from backend.main_api.repositories.billing import BillingWorkflowRepository
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.repositories.tasks import TaskLeaseRepository
from backend.main_api.schemas.presentations import CreatePresentationRequest
from backend.main_api.services.billing import BillingPolicy
from backend.main_api.services.generation_orchestrator import (
    BillingGenerationOrchestrator,
    BillingTaskHandler,
)
from backend.main_api.services.presentations import PresentationService
from backend.main_api.workers.runner import PersistentTaskWorker


NOW = datetime(2026, 7, 23, 6, 30, 0)


class FakeBillingClient:
    """记录平台写动作；每个动作可注入明确失败或终态未知。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reserve_error: Exception | None = None
        self.settle_error: Exception | None = None
        self.release_error: Exception | None = None
        self.insufficient = False

    async def get_entitlement_balance(self, *, entitlement_id: int, user_id: int):
        assert entitlement_id == 990306
        return EntitlementBalance(
            entitlement_id=entitlement_id,
            user_id=user_id,
            quota_total="100",
            quota_used="0",
            quota_reserved="0",
            remaining="5" if self.insufficient else "100",
            status="active",
            expires_at=None,
            usable=True,
        )

    async def reserve_entitlement(self, *, entitlement_id: int, user_id: int, amount: str, idempotency_key: str):
        self.calls.append(("reserve", idempotency_key))
        if self.reserve_error:
            raise self.reserve_error
        return EntitlementReservation(hold_id=51, reserved=amount, available="90", status="holding")

    async def settle_entitlement(self, *, hold_id: int, actual_amount: str, idempotency_key: str):
        self.calls.append(("settle", idempotency_key))
        if self.settle_error:
            raise self.settle_error
        return EntitlementFinalization(
            hold_id=hold_id, status="settled", settled_amount=actual_amount,
            quota_used=actual_amount, quota_reserved="0", available="92",
        )

    async def release_entitlement(self, *, hold_id: int, idempotency_key: str):
        self.calls.append(("release", idempotency_key))
        if self.release_error:
            raise self.release_error
        return EntitlementFinalization(
            hold_id=hold_id, status="released", settled_amount="0",
            quota_used="0", quota_reserved="0", available="100",
        )


class ScriptedGenerationHandler:
    """模拟Agent与作品持久化；调用次数是计费前置闸门的真实证据。"""

    def __init__(
        self,
        engine,
        *,
        fail: bool = False,
        persist: bool = True,
        probe_error: bool = False,
        fail_after_persist: bool = False,
        delay_seconds: float = 0,
    ) -> None:
        self.engine = engine
        self.fail = fail
        self.persist = persist
        self.probe_error = probe_error
        self.fail_after_persist = fail_after_persist
        self.delay_seconds = delay_seconds
        self.calls: list[str] = []
        self.persisted: set[str] = set()

    async def execute(self, task) -> None:
        self.calls.append(task.task_id)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.fail:
            raise RuntimeError("测试Agent明确失败")
        if self.persist:
            self.persisted.add(task.task_id)
            with sessionmaker(self.engine).begin() as db:
                db.execute(update(Presentation).where(Presentation.id == task.presentation_id).values(
                    status="ready", slides_json='{"slides":[{"id":"s1"}]}', slide_count=1,
                    updated_at=NOW,
                ))
        if self.fail_after_persist:
            raise RuntimeError("测试Agent在持久化后返回异常")

    async def has_persisted_result(self, task) -> bool:
        if self.probe_error:
            raise RuntimeError("测试持久化探测暂不可用")
        return task.task_id in self.persisted


class LocalCommitFailingRepository(BillingWorkflowRepository):
    """模拟平台成功后，本地对应终态条件提交未完成。"""

    def __init__(self, engine, action: str) -> None:
        super().__init__(engine)
        self.action = action

    def complete_reserve(self, task_id: str, hold_id: int, now: datetime) -> bool:
        return False if self.action == "reserve" else super().complete_reserve(task_id, hold_id, now)

    def complete_settle(self, task_id: str, now: datetime) -> bool:
        return False if self.action == "settle" else super().complete_settle(task_id, now)

    def complete_release(self, task_id: str, now: datetime) -> bool:
        return False if self.action == "release" else super().complete_release(task_id, now)


def _fixture(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'billing-workflow.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    ids = iter(("presentation-1", "task-1", "billing-1"))
    created = PresentationService(
        PresentationRepository(engine),
        task_max_attempts=3,
        user_presentation_limit=None,
        billing_enabled=True,
        billing_product_id=73,
        billing_reserve_points=10,
        billing_settle_points=8,
        id_factory=lambda: next(ids),
        now_factory=lambda: NOW,
    ).create(
        1001,
        "billing-workflow-request",
        CreatePresentationRequest(title="计费编排", content="生成完整PPT"),
        billing_entitlement_id=990306,
    )
    client = FakeBillingClient()
    orchestrator = BillingGenerationOrchestrator(
        repository=BillingWorkflowRepository(engine),
        client=client,
        policy=BillingPolicy(reserve_points=10, settle_points=8),
        now_factory=lambda: NOW,
    )
    return engine, created.task.id, client, orchestrator


def _run_worker(
    engine,
    handler: BillingTaskHandler,
    *,
    allow_billing_tasks: bool = True,
    timeout_seconds: float = 30,
) -> bool:
    worker = PersistentTaskWorker(
        repository=TaskLeaseRepository(engine, allow_billing_tasks=allow_billing_tasks),
        handler=handler, worker_id="billing-worker",
        lease_seconds=120, heartbeat_seconds=30, retry_backoff_seconds=10,
        claim_batch_size=10, agent_timeout_seconds=timeout_seconds, clock=lambda: NOW,
    )
    return asyncio.run(worker.run_once())


def _states(engine):
    with sessionmaker(engine)() as db:
        return (
            db.scalar(select(Presentation)),
            db.scalar(select(GenerationTask)),
            db.scalar(select(BillingOperation)),
        )


def test_success_reserves_before_agent_persists_then_settles_once(tmp_path: Path) -> None:
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    inner = ScriptedGenerationHandler(engine)
    try:
        assert asyncio.run(orchestrator.prepare_next()) is True
        assert asyncio.run(orchestrator.prepare_next()) is False
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert inner.calls == []
        # 关闭新计费或缺少收尾配置时，普通Worker不得裸跑已有收费任务。
        assert _run_worker(
            engine,
            BillingTaskHandler(inner=inner, orchestrator=orchestrator),
            allow_billing_tasks=False,
        ) is False
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is False
        presentation, task, operation = _states(engine)
        assert inner.calls == [task_id]
        assert client.calls == [
            ("reserve", f"ppt:{task_id}:reserve"),
            ("settle", f"ppt:{task_id}:settle"),
        ]
        assert operation.status == "settled" and operation.hold_id == 51
        assert task.status == "succeeded" and presentation.status == "ready"
        assert asyncio.run(orchestrator.settle_after_success(task_id)) == "settled"
        assert len(client.calls) == 2
    finally:
        engine.dispose()


def test_insufficient_reserve_fails_without_agent_call(tmp_path: Path) -> None:
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    client.insufficient = True
    inner = ScriptedGenerationHandler(engine)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "failed"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is False
        presentation, task, operation = _states(engine)
        assert inner.calls == [] and client.calls == []
        assert operation.status == "reserve_failed"
        assert task.status == "failed" and presentation.status == "failed"
    finally:
        engine.dispose()


def test_platform_atomic_60005_does_not_switch_entitlement_or_call_agent(tmp_path: Path) -> None:
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    client.reserve_error = MolingBusinessError(
        "平台拒绝", request_id="safe", retryable=False, platform_code=60005
    )
    inner = ScriptedGenerationHandler(engine)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "failed"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is False
        assert inner.calls == []
        assert client.calls == [("reserve", f"ppt:{task_id}:reserve")]
        assert _states(engine)[2].last_error_code == "BILLING_ENTITLEMENT_INSUFFICIENT"
    finally:
        engine.dispose()


def test_agent_or_persistence_failure_releases_once(tmp_path: Path) -> None:
    for fail, persist, expected_code in (
        (True, True, "GENERATION_FAILED"),
        (False, False, "GENERATION_PERSISTENCE_NOT_CONFIRMED"),
    ):
        case_dir = tmp_path / f"{fail}-{persist}"
        case_dir.mkdir()
        engine, task_id, client, orchestrator = _fixture(case_dir)
        inner = ScriptedGenerationHandler(engine, fail=fail, persist=persist)
        try:
            assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
            assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
            presentation, task, operation = _states(engine)
            assert client.calls == [
                ("reserve", f"ppt:{task_id}:reserve"),
                ("release", f"ppt:{task_id}:release"),
            ]
            assert operation.status == "released"
            assert task.status == "failed" and task.last_error_code == expected_code
            assert presentation.status == "failed"
            assert asyncio.run(orchestrator.release_after_failure(task_id)) == "released"
            assert len(client.calls) == 2
        finally:
            engine.dispose()


def test_write_timeout_enters_billing_pending_without_guessing_or_compensation(tmp_path: Path) -> None:
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    client.reserve_error = MolingUnavailableError(
        "平台暂不可用", request_id="safe", retryable=True
    )
    inner = ScriptedGenerationHandler(engine)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "billing_pending"
        presentation, task, operation = _states(engine)
        assert inner.calls == []
        assert operation.status == task.status == presentation.status == "billing_pending"
        assert operation.action == "reserve"
        assert client.calls == [("reserve", f"ppt:{task_id}:reserve")]
    finally:
        engine.dispose()


def test_settle_timeout_never_releases_or_reports_success(tmp_path: Path) -> None:
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    client.settle_error = MolingUnavailableError(
        "平台暂不可用", request_id="safe", retryable=True
    )
    inner = ScriptedGenerationHandler(engine)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [
            ("reserve", f"ppt:{task_id}:reserve"),
            ("settle", f"ppt:{task_id}:settle"),
        ]
        assert operation.status == task.status == presentation.status == "billing_pending"
        assert operation.action == "settle"
    finally:
        engine.dispose()


def test_persistence_probe_error_freezes_reserved_task_for_reconciliation(tmp_path: Path) -> None:
    """探测异常不等于无产物，不能贸然release或settle。"""
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    inner = ScriptedGenerationHandler(engine, persist=True, probe_error=True)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [("reserve", f"ppt:{task_id}:reserve")]
        assert operation.status == task.status == presentation.status == "billing_pending"
        assert operation.action == "inspect"
        assert task.last_error_code == "GENERATION_RESULT_UNKNOWN"
    finally:
        engine.dispose()


def test_concurrent_prepare_only_calls_platform_reserve_once(tmp_path: Path) -> None:
    """两个常驻进程同时发现planned时，只允许数据库条件更新赢家调用平台。"""
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    try:
        barrier = threading.Barrier(2)

        def prepare(_: int) -> str:
            barrier.wait(timeout=5)
            return asyncio.run(orchestrator.prepare(task_id))

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(prepare, (1, 2)))
        assert "reserved" in outcomes
        assert client.calls == [("reserve", f"ppt:{task_id}:reserve")]
        assert _states(engine)[2].status == "reserved"
    finally:
        engine.dispose()


def test_release_timeout_freezes_task_without_retrying_release(tmp_path: Path) -> None:
    """release响应丢失时不能宣称已退款，也不能在T17自动重放。"""
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    client.release_error = MolingUnavailableError(
        "平台暂不可用", request_id="safe", retryable=True
    )
    inner = ScriptedGenerationHandler(engine, fail=True)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [
            ("reserve", f"ppt:{task_id}:reserve"),
            ("release", f"ppt:{task_id}:release"),
        ]
        assert operation.status == task.status == presentation.status == "billing_pending"
        assert operation.action == "release"
    finally:
        engine.dispose()


def test_platform_success_but_local_terminal_commit_failure_is_frozen(tmp_path: Path) -> None:
    """平台成功、本地条件提交失败时保留动作证据，不能继续或报告成功。"""
    for action in ("reserve", "settle", "release"):
        case_dir = tmp_path / action
        case_dir.mkdir()
        engine, task_id, client, orchestrator = _fixture(case_dir)
        orchestrator.repository = LocalCommitFailingRepository(engine, action)
        try:
            prepared = asyncio.run(orchestrator.prepare(task_id))
            if action == "reserve":
                assert prepared == "billing_pending"
            else:
                assert prepared == "reserved"
                inner = ScriptedGenerationHandler(engine, fail=action == "release")
                assert _run_worker(
                    engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)
                ) is True
            presentation, task, operation = _states(engine)
            assert operation.status == task.status == presentation.status == "billing_pending"
            assert operation.action == action
            assert operation.hold_id == 51
            assert operation.last_error_code == f"BILLING_{action.upper()}_LOCAL_COMMIT_FAILED"
        finally:
            engine.dispose()


def test_agent_error_after_persistence_settles_instead_of_releasing(tmp_path: Path) -> None:
    """异常不代表无产物；已确认作品落库时仍应按成功路径结算。"""
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    inner = ScriptedGenerationHandler(engine, fail_after_persist=True)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert _run_worker(engine, BillingTaskHandler(inner=inner, orchestrator=orchestrator)) is True
        presentation, task, operation = _states(engine)
        assert client.calls == [
            ("reserve", f"ppt:{task_id}:reserve"),
            ("settle", f"ppt:{task_id}:settle"),
        ]
        assert operation.status == "settled"
        assert task.status == "succeeded" and presentation.status == "ready"
    finally:
        engine.dispose()


def test_agent_timeout_probes_then_releases_without_retrying_agent(tmp_path: Path) -> None:
    """Worker取消处理器时也必须完成计费补偿，并把当前任务置为不可重试。"""
    engine, task_id, client, orchestrator = _fixture(tmp_path)
    inner = ScriptedGenerationHandler(engine, persist=False, delay_seconds=0.2)
    try:
        assert asyncio.run(orchestrator.prepare(task_id)) == "reserved"
        assert _run_worker(
            engine,
            BillingTaskHandler(inner=inner, orchestrator=orchestrator),
            timeout_seconds=0.01,
        ) is True
        assert _run_worker(
            engine,
            BillingTaskHandler(inner=inner, orchestrator=orchestrator),
            timeout_seconds=0.01,
        ) is False
        presentation, task, operation = _states(engine)
        assert inner.calls == [task_id]
        assert client.calls == [
            ("reserve", f"ppt:{task_id}:reserve"),
            ("release", f"ppt:{task_id}:release"),
        ]
        assert operation.status == "released"
        assert task.status == "failed" and task.last_error_code == "GENERATION_TIMEOUT"
        assert presentation.status == "failed"
    finally:
        engine.dispose()
