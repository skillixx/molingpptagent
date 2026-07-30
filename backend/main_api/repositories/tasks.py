"""持久任务原子领取与租约围栏仓储。"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, Select, exists, func, or_, select, update
from sqlalchemy.orm import sessionmaker

from ..models.domain import BillingOperation, GenerationTask, Presentation


@dataclass(frozen=True)
class TaskLease:
    """已提交事务后的租约凭证；令牌禁止写日志。"""

    task_id: str
    worker_id: str
    lock_token: str = field(repr=False)


@dataclass(frozen=True)
class TaskRecord:
    """Worker执行所需的最小任务快照，不携带数据库Session。"""

    task_id: str
    presentation_id: str
    owner_user_id: int
    request_id: str
    input_json: str
    attempt: int
    max_attempts: int
    lock_token: str = field(repr=False)
    dispatch_started_at: datetime | None = None


def claim_candidate_statement(
    now: datetime, *, skip_locked: bool, allow_billing_tasks: bool = False
) -> Select[tuple[str]]:
    """构造短事务候选查询；MySQL 8 使用 SKIP LOCKED，其他方言走条件更新。"""
    conditions = [
        GenerationTask.status == "pending",
        GenerationTask.next_attempt_at <= now,
        GenerationTask.attempt < GenerationTask.max_attempts,
        or_(GenerationTask.locked_until.is_(None), GenerationTask.locked_until <= now),
    ]
    if not allow_billing_tasks:
        # 停止新计费或缺少结算配置时，只允许普通任务运行，遗留hold不能裸跑Agent。
        conditions.append(
            ~exists(
                select(BillingOperation.id).where(
                    BillingOperation.task_id == GenerationTask.id
                )
            )
        )
    statement = (
        select(GenerationTask.id)
        .where(*conditions)
        .order_by(GenerationTask.next_attempt_at, GenerationTask.created_at, GenerationTask.id)
        .limit(1)
    )
    return statement.with_for_update(skip_locked=True) if skip_locked else statement


class TaskLeaseRepository:
    """网络调用必须发生在本仓储返回租约并提交领取事务之后。"""

    def __init__(self, engine: Engine, *, allow_billing_tasks: bool = False) -> None:
        self.engine = engine
        self.allow_billing_tasks = allow_billing_tasks
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def claim_next(self, worker_id: str, *, now: datetime, locked_until: datetime) -> TaskLease | None:
        """原子领取一个到期 pending 任务；并发失败是正常竞争结果。"""
        lock_token = secrets.token_urlsafe(32)
        with self._session_factory.begin() as db:
            dialect = db.get_bind().dialect
            version = dialect.server_version_info or ()
            use_skip_locked = (
                dialect.name == "mysql"
                and not getattr(dialect, "is_mariadb", False)
                and version >= (8, 0)
            )
            task_id = db.scalar(
                claim_candidate_statement(
                    now,
                    skip_locked=use_skip_locked,
                    allow_billing_tasks=self.allow_billing_tasks,
                )
            )
            if task_id is None:
                return None
            claim_conditions = [
                    GenerationTask.id == task_id,
                    GenerationTask.status == "pending",
                    GenerationTask.next_attempt_at <= now,
                    GenerationTask.attempt < GenerationTask.max_attempts,
                    or_(GenerationTask.locked_until.is_(None), GenerationTask.locked_until <= now),
            ]
            if not self.allow_billing_tasks:
                claim_conditions.append(
                    ~exists(
                        select(BillingOperation.id).where(
                            BillingOperation.task_id == GenerationTask.id
                        )
                    )
                )
            result = db.execute(
                update(GenerationTask)
                .where(*claim_conditions)
                .values(
                    status="running",
                    locked_by=worker_id,
                    lock_token=lock_token,
                    locked_until=locked_until,
                    heartbeat_at=now,
                    # 首次开始时间用于审计端到端耗时，重试领取不能覆盖。
                    started_at=func.coalesce(GenerationTask.started_at, now),
                    updated_at=now,
                    attempt=GenerationTask.attempt + 1,
                )
            )
            if result.rowcount != 1:
                # 未命中只表示另一个事务先赢得竞争，不能吞掉真实数据库异常。
                return None
        return TaskLease(task_id, worker_id, lock_token)

    def fail(
        self,
        task_id: str,
        lock_token: str,
        now: datetime,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
    ) -> bool:
        """带围栏写入明确失败终态；T08 才负责按策略重新入队。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == lock_token,
                    GenerationTask.locked_until > now,
                )
                .values(
                    status="failed",
                    stage="failed",
                    last_error_code=error_code,
                    error_message=error_message,
                    retryable=retryable,
                    finished_at=now,
                    updated_at=now,
                    locked_by=None,
                    lock_token=None,
                    locked_until=None,
                )
            )
            if result.rowcount == 1:
                self._mark_presentation_failed(db, task_id, now)
            return result.rowcount == 1

    def get_for_execution(self, task_id: str, lock_token: str) -> TaskRecord | None:
        """只返回当前围栏持有者的执行快照，避免旧Worker读取后继续调用Agent。"""
        with self._session_factory() as db:
            task = db.scalar(
                select(GenerationTask).where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == lock_token,
                )
            )
            if task is None:
                return None
            return self._record(task)

    def mark_dispatch_started(self, task_id: str, lock_token: str, now: datetime) -> bool:
        """在网络调用前提交派发标记；崩溃恢复据此决定是否允许自动重试。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == lock_token,
                    GenerationTask.locked_until > now,
                    GenerationTask.dispatch_started_at.is_(None),
                )
                .values(dispatch_started_at=now, updated_at=now)
            )
            return result.rowcount == 1

    def list_expired(self, now: datetime, *, limit: int) -> list[TaskRecord]:
        """读取过期租约快照；后续探测必须在本查询事务之外执行。"""
        with self._session_factory() as db:
            tasks = db.scalars(
                select(GenerationTask)
                .where(
                    GenerationTask.status == "running",
                    GenerationTask.locked_until.is_not(None),
                    GenerationTask.locked_until <= now,
                )
                .order_by(GenerationTask.locked_until, GenerationTask.id)
                .limit(limit)
            ).all()
            return [self._record(task) for task in tasks if task.lock_token]

    def recover_before_dispatch(
        self,
        task: TaskRecord,
        *,
        now: datetime,
        next_attempt_at: datetime,
    ) -> bool:
        """派发前崩溃可安全重排；达到上限则进入死信。"""
        can_retry = task.attempt < task.max_attempts
        values: dict[str, Any]
        if can_retry:
            values = {
                "status": "pending",
                "stage": "queued",
                "next_attempt_at": next_attempt_at,
                "last_error_code": "WORKER_LOST_BEFORE_DISPATCH",
                "error_message": "Worker在Agent派发前中断",
                "locked_by": None,
                "lock_token": None,
                "locked_until": None,
                "heartbeat_at": None,
                "updated_at": now,
            }
        else:
            values = {
                "status": "failed",
                "stage": "dead_letter",
                "retryable": False,
                "last_error_code": "TASK_MAX_ATTEMPTS_EXCEEDED",
                "error_message": "任务已达到最大尝试次数",
                "finished_at": now,
                "locked_by": None,
                "lock_token": None,
                "locked_until": None,
                "updated_at": now,
            }
        return self._resolve_expired(task, now=now, values=values, dispatch_started=False)

    def recover_after_dispatch(self, task: TaskRecord, *, now: datetime, has_result: bool) -> bool:
        """派发后只探测既有产物；没有产物时显式未知失败，禁止盲目再调Agent。"""
        if has_result:
            values: dict[str, Any] = {
                "status": "succeeded",
                "stage": "completed",
                "progress": 100,
                "finished_at": now,
                "last_error_code": None,
                "error_message": None,
            }
        else:
            values = {
                "status": "failed",
                "stage": "failed",
                "retryable": False,
                "finished_at": now,
                "last_error_code": "AGENT_OUTCOME_UNKNOWN",
                "error_message": "Agent调用结果未知，已停止自动重试",
            }
        values.update(
            {
                "locked_by": None,
                "lock_token": None,
                "locked_until": None,
                "updated_at": now,
            }
        )
        return self._resolve_expired(task, now=now, values=values, dispatch_started=True)

    def record_failure(
        self,
        task: TaskRecord,
        *,
        now: datetime,
        next_attempt_at: datetime,
        error_code: str,
        error_message: str,
        retryable: bool,
    ) -> bool:
        """显式失败按尝试次数重排或死信，所有写入继续受当前租约围栏保护。"""
        if retryable and task.attempt < task.max_attempts:
            values: dict[str, Any] = {
                "status": "pending",
                "stage": "queued",
                "next_attempt_at": next_attempt_at,
                "retryable": True,
                "last_error_code": error_code,
                "error_message": error_message,
                "dispatch_started_at": None,
                "locked_by": None,
                "lock_token": None,
                "locked_until": None,
                "heartbeat_at": None,
                "updated_at": now,
            }
        else:
            values = {
                "status": "failed",
                "stage": "dead_letter" if retryable else "failed",
                "retryable": False,
                "last_error_code": error_code,
                "error_message": error_message,
                "finished_at": now,
                "locked_by": None,
                "lock_token": None,
                "locked_until": None,
                "updated_at": now,
            }
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task.task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == task.lock_token,
                    GenerationTask.locked_until > now,
                )
                .values(**values)
            )
            if result.rowcount == 1 and values.get("status") == "failed":
                self._mark_presentation_failed(db, task.task_id, now)
            return result.rowcount == 1

    def renew(self, task_id: str, lock_token: str, locked_until: datetime, now: datetime) -> bool:
        """只有仍持有有效 running 围栏的 Worker 才能续租。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == lock_token,
                    GenerationTask.locked_until > now,
                )
                .values(locked_until=locked_until, heartbeat_at=now, updated_at=now)
            )
            return result.rowcount == 1

    def complete(self, task_id: str, lock_token: str, now: datetime) -> bool:
        """带围栏提交唯一成功终态，旧 Worker 即使稍后返回也不能覆盖。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == lock_token,
                    GenerationTask.locked_until > now,
                )
                .values(
                    status="succeeded",
                    stage="completed",
                    progress=100,
                    finished_at=now,
                    updated_at=now,
                    locked_by=None,
                    lock_token=None,
                    locked_until=None,
                )
            )
            return result.rowcount == 1

    def _resolve_expired(
        self,
        task: TaskRecord,
        *,
        now: datetime,
        values: dict[str, Any],
        dispatch_started: bool,
    ) -> bool:
        """以旧lock_token作为恢复围栏，多个回收器只能有一个成功。"""
        dispatch_condition = (
            GenerationTask.dispatch_started_at.is_not(None)
            if dispatch_started
            else GenerationTask.dispatch_started_at.is_(None)
        )
        with self._session_factory.begin() as db:
            result = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task.task_id,
                    GenerationTask.status == "running",
                    GenerationTask.lock_token == task.lock_token,
                    GenerationTask.locked_until <= now,
                    dispatch_condition,
                )
                .values(**values)
            )
            if result.rowcount == 1 and values.get("status") == "failed":
                self._mark_presentation_failed(db, task.task_id, now)
            return result.rowcount == 1

    @staticmethod
    def _mark_presentation_failed(db, task_id: str, now: datetime) -> None:
        """任务进入最终失败时同步作品状态；可重试任务仍保持生成中。"""
        task = db.get(GenerationTask, task_id)
        if task is None:
            return
        db.execute(
            update(Presentation)
            .where(
                Presentation.id == task.presentation_id,
                Presentation.owner_user_id == task.owner_user_id,
                Presentation.deleted_at.is_(None),
                Presentation.status == "generating",
            )
            .values(status="failed", updated_at=now)
        )

    @staticmethod
    def _record(task: GenerationTask) -> TaskRecord:
        assert task.lock_token is not None
        return TaskRecord(
            task_id=task.id,
            presentation_id=task.presentation_id,
            owner_user_id=task.owner_user_id,
            request_id=task.request_id,
            input_json=task.input_json,
            attempt=task.attempt,
            max_attempts=task.max_attempts,
            lock_token=task.lock_token,
            dispatch_started_at=task.dispatch_started_at,
        )


__all__ = ["TaskLease", "TaskLeaseRepository", "TaskRecord", "claim_candidate_statement"]
