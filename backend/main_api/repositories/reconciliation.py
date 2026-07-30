"""T18 计费对账仓储：持久化退避、并发认领与人工介入边界。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Engine, or_, select, update
from sqlalchemy.orm import sessionmaker

from ..models.domain import BillingOperation, GenerationTask, Presentation
from .billing import BillingAction, BillingStatus


@dataclass(frozen=True)
class ReconciliationClaim:
    """脱离 Session 的对账快照；不包含内部令牌等部署秘密。"""

    task_id: str
    presentation_id: str
    owner_user_id: int
    request_id: str
    input_json: str
    attempt: int
    max_attempts: int
    action: BillingAction
    hold_id: int | None
    actual_amount: int | None
    settle_key: str | None
    release_key: str | None
    retry_count: int


@dataclass(frozen=True)
class TaskStatusRecord:
    task_id: str
    presentation_id: str
    status: str
    stage: str
    progress: int
    retryable: bool
    error_code: str | None
    updated_at: datetime
    billing_status: str | None
    billing_action: str | None
    billing_retry_count: int | None
    billing_next_retry_at: datetime | None


class BillingReconciliationRepository:
    """以条件更新争抢单条记录，保证多个 Worker 不会同时重放账务写入。"""

    _DUE_STATUSES = (
        BillingStatus.BILLING_PENDING,
        BillingStatus.RESERVING,
        BillingStatus.SETTLING,
        BillingStatus.RELEASING,
        BillingStatus.RECONCILING,
    )

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def claim_due(
        self,
        *,
        now: datetime,
        base_interval_seconds: int,
        inflight_stale_seconds: int,
        max_retries: int,
    ) -> ReconciliationClaim | None:
        """认领到期动作并先提交本次次数和下次退避时间，重启后不会丢失节流状态。"""
        with self._session_factory.begin() as db:
            stale_before = now - timedelta(seconds=inflight_stale_seconds)
            # 最后一次认领后若进程崩溃，下一次到期必须自动收敛到人工，不能永久悬挂。
            db.execute(
                update(BillingOperation)
                .where(
                    BillingOperation.status == BillingStatus.RECONCILING,
                    BillingOperation.retry_count >= max_retries,
                    BillingOperation.next_retry_at.is_not(None),
                    BillingOperation.next_retry_at <= now,
                    BillingOperation.updated_at <= stale_before,
                )
                .values(
                    status=BillingStatus.MANUAL_REQUIRED,
                    next_retry_at=None,
                    last_error_code="BILLING_RECONCILIATION_INTERRUPTED",
                    updated_at=now,
                )
            )
            candidates = db.execute(
                select(
                    BillingOperation.id,
                    BillingOperation.status,
                    BillingOperation.retry_count,
                    BillingOperation.updated_at,
                )
                .where(
                    BillingOperation.status.in_(self._DUE_STATUSES),
                    BillingOperation.retry_count < max_retries,
                    or_(
                        BillingOperation.status == BillingStatus.BILLING_PENDING,
                        # 其余状态可能仍由另一进程执行，必须超过完整平台调用租约。
                        BillingOperation.updated_at <= stale_before,
                    ),
                    or_(
                        BillingOperation.next_retry_at.is_(None),
                        BillingOperation.next_retry_at <= now,
                    ),
                )
                .order_by(BillingOperation.updated_at, BillingOperation.id)
                .limit(10)
            ).all()
            for operation_id, prior_status, prior_retry_count, prior_updated_at in candidates:
                next_retry = now + timedelta(
                    seconds=min(base_interval_seconds * (2**prior_retry_count), 3600)
                )
                won = db.execute(
                    update(BillingOperation)
                    .where(
                        BillingOperation.id == operation_id,
                        BillingOperation.status == prior_status,
                        BillingOperation.retry_count == prior_retry_count,
                        BillingOperation.updated_at == prior_updated_at,
                        or_(
                            BillingOperation.next_retry_at.is_(None),
                            BillingOperation.next_retry_at <= now,
                        ),
                    )
                    .values(
                        status=BillingStatus.RECONCILING,
                        retry_count=prior_retry_count + 1,
                        next_retry_at=next_retry,
                        updated_at=now,
                    )
                )
                if won.rowcount != 1:
                    continue
                operation = db.get(BillingOperation, operation_id)
                task = db.get(GenerationTask, operation.task_id) if operation else None
                if operation is None or task is None:
                    continue
                return self._claim(operation, task)
        return None

    def choose_action(self, task_id: str, action: BillingAction, now: datetime) -> bool:
        """产物探测只决定后续使用哪个既有幂等动作，不创建新的 reserve。"""
        if action not in {BillingAction.SETTLE, BillingAction.RELEASE}:
            raise ValueError("unsupported reconciliation action")
        with self._session_factory.begin() as db:
            result = db.execute(
                update(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RECONCILING,
                )
                .values(action=action, updated_at=now)
            )
            return result.rowcount == 1

    def record_failure(
        self, task_id: str, error_code: str, *, max_retries: int, now: datetime
    ) -> bool:
        """保留 billing_pending 门闩；达到上限后停止自动请求并转人工处理。"""
        with self._session_factory.begin() as db:
            operation = db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RECONCILING,
                )
                .with_for_update()
            )
            if operation is None:
                return False
            operation.last_error_code = error_code[:64]
            operation.updated_at = now
            if operation.retry_count >= max_retries:
                operation.status = BillingStatus.MANUAL_REQUIRED
                operation.next_retry_at = None
            else:
                operation.status = BillingStatus.BILLING_PENDING
            return True

    def mark_manual(self, task_id: str, error_code: str, now: datetime) -> bool:
        """协议不能安全自动判定时立即停止，不把未知 reserve 当作可重放动作。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RECONCILING,
                )
                .values(
                    status=BillingStatus.MANUAL_REQUIRED,
                    next_retry_at=None,
                    last_error_code=error_code[:64],
                    updated_at=now,
                )
            )
            return result.rowcount == 1

    def resolve(self, task_id: str, action: BillingAction, now: datetime) -> bool:
        """账务终态、任务终态和作品门闩在同一数据库事务中提交。"""
        with self._session_factory.begin() as db:
            operation = db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RECONCILING,
                    BillingOperation.action == action,
                )
                .with_for_update()
            )
            task = db.get(GenerationTask, task_id, with_for_update=True)
            if operation is None or task is None:
                return False
            presentation = db.get(Presentation, task.presentation_id, with_for_update=True)
            if presentation is None:
                return False
            operation.status = (
                BillingStatus.SETTLED if action == BillingAction.SETTLE else BillingStatus.RELEASED
            )
            operation.last_error_code = None
            operation.next_retry_at = None
            operation.updated_at = now
            task.status = "succeeded" if action == BillingAction.SETTLE else "failed"
            task.stage = "completed" if action == BillingAction.SETTLE else "failed"
            task.progress = 100 if action == BillingAction.SETTLE else task.progress
            task.retryable = False
            task.last_error_code = (
                None if action == BillingAction.SETTLE else "BILLING_RELEASED_AFTER_RECONCILIATION"
            )
            task.error_message = None if action == BillingAction.SETTLE else "计费已释放，任务未完成"
            task.finished_at = now
            task.updated_at = now
            presentation.status = "ready" if action == BillingAction.SETTLE else "failed"
            presentation.updated_at = now
            return True

    def get_task_status(self, owner_user_id: int, task_id: str) -> TaskStatusRecord | None:
        """查询条件包含 owner，跨用户访问与资源不存在统一返回空。"""
        with self._session_factory() as db:
            row = db.execute(
                select(GenerationTask, BillingOperation)
                .join(Presentation, Presentation.id == GenerationTask.presentation_id)
                .outerjoin(BillingOperation, BillingOperation.task_id == GenerationTask.id)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            ).one_or_none()
            if row is None:
                return None
            task, operation = row
            return TaskStatusRecord(
                task_id=task.id,
                presentation_id=task.presentation_id,
                status=task.status,
                stage=task.stage,
                progress=task.progress,
                retryable=task.retryable,
                error_code=task.last_error_code,
                updated_at=task.updated_at,
                billing_status=operation.status if operation else None,
                billing_action=operation.action if operation else None,
                billing_retry_count=operation.retry_count if operation else None,
                billing_next_retry_at=operation.next_retry_at if operation else None,
            )

    @staticmethod
    def _claim(operation: BillingOperation, task: GenerationTask) -> ReconciliationClaim:
        return ReconciliationClaim(
            task_id=task.id,
            presentation_id=task.presentation_id,
            owner_user_id=task.owner_user_id,
            request_id=task.request_id,
            input_json=task.input_json,
            attempt=task.attempt,
            max_attempts=task.max_attempts,
            action=BillingAction(operation.action),
            hold_id=operation.hold_id,
            actual_amount=operation.actual_amount,
            settle_key=operation.settle_key,
            release_key=operation.release_key,
            retry_count=operation.retry_count,
        )


__all__ = [
    "BillingReconciliationRepository",
    "ReconciliationClaim",
    "TaskStatusRecord",
]
