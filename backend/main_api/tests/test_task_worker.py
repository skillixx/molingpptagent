"""T08 持久 Worker、崩溃恢复、有限重试和Agent调用计数测试。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.main_api.models.base import Base
from backend.main_api.models.domain import GenerationTask, Presentation
from backend.main_api.repositories.tasks import TaskLeaseRepository
from backend.main_api.workers.runner import (
    NonRetryableTaskError,
    PersistentTaskWorker,
    RetryableTaskError,
    TaskExecution,
)


START = datetime(2026, 7, 23, 3, 10, 0)


class WorkerCrash(BaseException):
    """模拟进程被杀，Worker正常异常处理代码不会捕获。"""


@dataclass
class MutableClock:
    now: datetime = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


class ScriptedHandler:
    """按脚本返回成功、错误或进程崩溃，并记录真实Agent调用次数。"""

    def __init__(self, *actions: str) -> None:
        self.actions = list(actions)
        self.calls: list[str] = []
        self.persisted_results: set[str] = set()

    async def execute(self, task: TaskExecution) -> None:
        self.calls.append(task.request_id)
        action = self.actions.pop(0) if self.actions else "success"
        if action == "retryable":
            raise RetryableTaskError("AGENT_TEMPORARY", "Agent暂时不可用")
        if action == "non_retryable":
            raise NonRetryableTaskError("TASK_INPUT_INVALID", "任务输入无效")
        if action == "timeout":
            await asyncio.sleep(0.2)
            return
        if action == "persist_then_crash":
            self.persisted_results.add(task.request_id)
            raise WorkerCrash()
        if action == "crash":
            raise WorkerCrash()
        self.persisted_results.add(task.request_id)

    async def has_persisted_result(self, task: TaskExecution) -> bool:
        return task.request_id in self.persisted_results


class SlowHandler(ScriptedHandler):
    """保持任务运行到至少一次心跳，用于验证 Worker 主动续租。"""

    async def execute(self, task: TaskExecution) -> None:
        self.calls.append(task.request_id)
        await asyncio.sleep(0.05)
        self.persisted_results.add(task.request_id)


class CountingRepository:
    """只统计续租次数，其余行为原样委托给真实 SQLite 仓储。"""

    def __init__(self, repository: TaskLeaseRepository) -> None:
        self.repository = repository
        self.renew_calls = 0

    def renew(self, *args, **kwargs):
        self.renew_calls += 1
        return self.repository.renew(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self.repository, name)


def _engine(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'worker.db').as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    Base.metadata.create_all(engine)
    return engine


def _insert_task(engine, *, task_id: str = "task-1", max_attempts: int = 3) -> None:
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(
            Presentation(
                id="presentation-1",
                owner_user_id=1001,
                title="Worker测试",
                status="generating",
                slides_json="{}",
                current_version=1,
                slide_count=0,
                created_at=START,
                updated_at=START,
            )
        )
        db.add(
            GenerationTask(
                id=task_id,
                presentation_id="presentation-1",
                owner_user_id=1001,
                request_id="request-stable-1",
                status="pending",
                stage="queued",
                progress=0,
                input_json='{"operation":"test"}',
                retryable=True,
                attempt=0,
                max_attempts=max_attempts,
                next_attempt_at=START,
                created_at=START,
                updated_at=START,
            )
        )


def _task(engine) -> GenerationTask:
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        return db.scalar(select(GenerationTask).where(GenerationTask.id == "task-1"))


def _worker(engine, handler, clock, *, timeout: float = 1.0) -> PersistentTaskWorker:
    return PersistentTaskWorker(
        repository=TaskLeaseRepository(engine),
        handler=handler,
        worker_id="worker-test",
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_backoff_seconds=10,
        claim_batch_size=10,
        agent_timeout_seconds=timeout,
        clock=clock,
    )


def test_crash_before_dispatch_requeues_and_restart_calls_agent_once(tmp_path: Path) -> None:
    """领取后、Agent派发前崩溃可安全重排，新进程只调用一次Agent。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        lease = TaskLeaseRepository(engine).claim_next(
            "worker-crashed", now=clock(), locked_until=clock() + timedelta(seconds=30)
        )
        assert lease is not None
        clock.advance(31)

        handler = ScriptedHandler("success")
        restarted = _worker(engine, handler, clock)
        assert asyncio.run(restarted.run_once()) is False  # 本轮只完成回收，退避尚未到期。
        assert _task(engine).status == "pending"
        clock.advance(10)
        assert asyncio.run(restarted.run_once()) is True
        assert _task(engine).status == "succeeded"
        assert handler.calls == ["request-stable-1"]
    finally:
        engine.dispose()


def test_crash_after_agent_dispatch_without_result_never_calls_agent_again(tmp_path: Path) -> None:
    """Agent结果未知时显式失败，禁止重启后盲目重复外部调用。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        handler = ScriptedHandler("crash", "success")
        worker = _worker(engine, handler, clock)
        try:
            asyncio.run(worker.run_once())
        except WorkerCrash:
            pass
        clock.advance(31)

        restarted = _worker(engine, handler, clock)
        assert asyncio.run(restarted.run_once()) is False
        task = _task(engine)
        assert task.status == "failed"
        assert task.last_error_code == "AGENT_OUTCOME_UNKNOWN"
        assert handler.calls == ["request-stable-1"]
    finally:
        engine.dispose()


def test_crash_after_persisted_result_recovers_success_without_second_agent_call(tmp_path: Path) -> None:
    """Agent产物已持久化时，重启探测产物后直接提交成功。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        handler = ScriptedHandler("persist_then_crash", "success")
        worker = _worker(engine, handler, clock)
        try:
            asyncio.run(worker.run_once())
        except WorkerCrash:
            pass
        clock.advance(31)

        assert asyncio.run(_worker(engine, handler, clock).run_once()) is False
        assert _task(engine).status == "succeeded"
        assert handler.calls == ["request-stable-1"]
    finally:
        engine.dispose()


def test_timeout_retries_with_backoff_then_succeeds(tmp_path: Path) -> None:
    """明确超时可重试，退避到期前不得再次调用Agent。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        handler = ScriptedHandler("timeout", "success")
        worker = _worker(engine, handler, clock, timeout=0.01)
        assert asyncio.run(worker.run_once()) is True
        task = _task(engine)
        assert task.status == "pending"
        assert task.last_error_code == "AGENT_TIMEOUT"
        assert asyncio.run(worker.run_once()) is False
        clock.advance(10)
        assert asyncio.run(worker.run_once()) is True
        assert _task(engine).status == "succeeded"
        assert handler.calls == ["request-stable-1", "request-stable-1"]
    finally:
        engine.dispose()


def test_retryable_failure_stops_at_max_attempts_and_becomes_dead_letter(tmp_path: Path) -> None:
    """最大尝试次数包含首次执行，达到上限后必须明确失败且不再领取。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine, max_attempts=3)
        clock = MutableClock()
        handler = ScriptedHandler("retryable", "retryable", "retryable", "success")
        worker = _worker(engine, handler, clock)
        for backoff in (10, 20):
            assert asyncio.run(worker.run_once()) is True
            clock.advance(backoff)
        assert asyncio.run(worker.run_once()) is True
        task = _task(engine)
        assert task.status == "failed"
        assert task.stage == "dead_letter"
        assert task.attempt == 3
        clock.advance(1000)
        assert asyncio.run(worker.run_once()) is False
        assert len(handler.calls) == 3
    finally:
        engine.dispose()


def test_non_retryable_failure_is_terminal_after_first_call(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        handler = ScriptedHandler("non_retryable", "success")
        worker = _worker(engine, handler, clock)
        assert asyncio.run(worker.run_once()) is True
        assert _task(engine).status == "failed"
        clock.advance(1000)
        assert asyncio.run(worker.run_once()) is False
        assert len(handler.calls) == 1
    finally:
        engine.dispose()


def test_completed_task_is_not_delivered_again(tmp_path: Path) -> None:
    """重复轮询或重复投递不能让已成功任务再次调用 Agent。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        clock = MutableClock()
        handler = ScriptedHandler("success", "success")
        worker = _worker(engine, handler, clock)

        assert asyncio.run(worker.run_once()) is True
        assert asyncio.run(worker.run_once()) is False
        assert handler.calls == ["request-stable-1"]
    finally:
        engine.dispose()


def test_running_task_renews_lease_before_completion(tmp_path: Path) -> None:
    """长任务执行期间由独立心跳协程续租，Agent 调用本身不占用数据库事务。"""
    engine = _engine(tmp_path)
    try:
        _insert_task(engine)
        repository = CountingRepository(TaskLeaseRepository(engine))
        handler = SlowHandler()
        worker = PersistentTaskWorker(
            repository=repository,
            handler=handler,
            worker_id="worker-heartbeat",
            lease_seconds=1,
            heartbeat_seconds=0.01,
            retry_backoff_seconds=10,
            claim_batch_size=10,
            agent_timeout_seconds=1,
            clock=MutableClock(),
        )

        assert asyncio.run(worker.run_once()) is True
        assert repository.renew_calls >= 1
        assert _task(engine).status == "succeeded"
    finally:
        engine.dispose()
