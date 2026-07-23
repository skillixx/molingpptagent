"""T17 计费状态机仓储：数据库事务只做状态转换，平台网络调用一律在事务外。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import sessionmaker

from ..models.domain import BillingOperation, GenerationTask, Presentation


class BillingAction(StrEnum):
    RESERVE = "reserve"
    SETTLE = "settle"
    RELEASE = "release"
    INSPECT = "inspect"


class BillingStatus(StrEnum):
    PLANNED = "planned"
    RESERVING = "reserving"
    RESERVED = "reserved"
    RESERVE_FAILED = "reserve_failed"
    SETTLING = "settling"
    SETTLED = "settled"
    RELEASING = "releasing"
    RELEASED = "released"
    BILLING_PENDING = "billing_pending"
    RECONCILING = "reconciling"
    MANUAL_REQUIRED = "manual_required"


@dataclass(frozen=True)
class BillingWorkflowContext:
    """平台动作所需的脱离Session快照，不包含用户正文或任何密钥。"""

    task_id: str
    owner_user_id: int
    entitlement_id: int | None
    hold_id: str | None
    reserved_amount: int
    actual_amount: int
    reserve_key: str
    settle_key: str
    release_key: str


@dataclass(frozen=True)
class BillingWorkflowClaim:
    """claimed=false表示另一执行者或既有终态已取得该动作。"""

    claimed: bool
    status: str
    context: BillingWorkflowContext | None = None


class BillingWorkflowRepository:
    """以billing_operations为主状态机，并在同事务同步任务和作品门禁。"""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def has_operation(self, task_id: str) -> bool:
        with self._session_factory() as db:
            return db.scalar(
                select(BillingOperation.id).where(BillingOperation.task_id == task_id)
            ) is not None

    def next_planned_task_id(self) -> str | None:
        """按创建顺序发现待预占任务；真正抢占仍由begin_reserve的事务状态判断完成。"""
        with self._session_factory() as db:
            return db.scalar(
                select(BillingOperation.task_id)
                .join(GenerationTask, GenerationTask.id == BillingOperation.task_id)
                .where(
                    BillingOperation.status == BillingStatus.PLANNED,
                    GenerationTask.status == "billing_required",
                )
                .order_by(BillingOperation.created_at, BillingOperation.id)
                .limit(1)
            )

    def begin_reserve(self, task_id: str, now: datetime) -> BillingWorkflowClaim:
        """只有planned可以赢得预占权；reserving绝不由普通执行器重复调用。"""
        with self._session_factory.begin() as db:
            # 条件更新在SQLite和MySQL都能原子判定赢家，不能只依赖SQLite忽略的FOR UPDATE。
            won = db.execute(
                update(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.PLANNED,
                )
                .values(
                    action=BillingAction.RESERVE,
                    status=BillingStatus.RESERVING,
                    updated_at=now,
                )
            )
            if won.rowcount != 1:
                operation, task = self._load(db, task_id)
                if operation is None or task is None:
                    return BillingWorkflowClaim(False, "not_found")
                return BillingWorkflowClaim(False, operation.status, self._context(operation))
            operation, task = self._load(db, task_id)
            if operation is None or task is None or task.status != "billing_required":
                raise RuntimeError("billing task state changed")
            task_won = db.execute(
                update(GenerationTask)
                .where(
                    GenerationTask.id == task_id,
                    GenerationTask.status == "billing_required",
                )
                .values(stage="reserving", updated_at=now)
            )
            if task_won.rowcount != 1:
                # 抛出使整个事务回滚，避免只推进账务状态却没有同步任务闸门。
                raise RuntimeError("billing task state changed")
            return BillingWorkflowClaim(True, BillingStatus.RESERVING, self._context(operation))

    def set_entitlement(self, task_id: str, entitlement_id: int, now: datetime) -> bool:
        """选择结果必须在发出reserve前提交，供崩溃和后续对账定位。"""
        with self._session_factory.begin() as db:
            operation = db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RESERVING,
                    BillingOperation.action == BillingAction.RESERVE,
                )
                .with_for_update()
            )
            if operation is None:
                return False
            operation.entitlement_id = str(entitlement_id)
            operation.updated_at = now
            return True

    def complete_reserve(self, task_id: str, hold_id: str, now: datetime) -> bool:
        """平台预占成功后才把任务开放给通用Worker领取。"""
        with self._session_factory.begin() as db:
            operation, task = self._load(db, task_id)
            if (
                operation is None
                or task is None
                or operation.status != BillingStatus.RESERVING
                or operation.entitlement_id is None
            ):
                return False
            presentation = db.get(Presentation, task.presentation_id)
            if presentation is None:
                return False
            operation.hold_id = hold_id
            operation.status = BillingStatus.RESERVED
            operation.last_error_code = None
            operation.updated_at = now
            task.status = "pending"
            task.stage = "queued"
            task.next_attempt_at = now
            task.updated_at = now
            presentation.status = "generating"
            presentation.updated_at = now
            return True

    def fail_reserve(self, task_id: str, error_code: str, now: datetime) -> bool:
        """仅用于确定未预占的失败；终态未知必须走billing_pending。"""
        with self._session_factory.begin() as db:
            operation, task = self._load(db, task_id)
            if operation is None or task is None or operation.status != BillingStatus.RESERVING:
                return False
            presentation = db.get(Presentation, task.presentation_id)
            operation.status = BillingStatus.RESERVE_FAILED
            operation.last_error_code = error_code[:64]
            operation.updated_at = now
            self._fail_task(task, error_code, now)
            if presentation is not None:
                presentation.status = "failed"
                presentation.updated_at = now
            return True

    def begin_finalize(
        self, task_id: str, action: BillingAction, now: datetime
    ) -> BillingWorkflowClaim:
        """只有本地明确reserved的记录能开始settle或release。"""
        if action not in {BillingAction.SETTLE, BillingAction.RELEASE}:
            raise ValueError("unsupported billing action")
        with self._session_factory.begin() as db:
            next_status = (
                BillingStatus.SETTLING
                if action == BillingAction.SETTLE
                else BillingStatus.RELEASING
            )
            won = db.execute(
                update(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.RESERVED,
                    BillingOperation.hold_id.is_not(None),
                )
                .values(action=action, status=next_status, updated_at=now)
            )
            if won.rowcount != 1:
                operation, task = self._load(db, task_id)
                if operation is None or task is None:
                    return BillingWorkflowClaim(False, "not_found")
                return BillingWorkflowClaim(False, operation.status, self._context(operation))
            operation, task = self._load(db, task_id)
            if operation is None or task is None or operation.hold_id is None:
                raise RuntimeError("billing task state changed")
            task.stage = next_status
            task.updated_at = now
            return BillingWorkflowClaim(True, next_status, self._context(operation))

    def complete_settle(self, task_id: str, now: datetime) -> bool:
        """只提交账务settled；任务成功仍由持有效租约的Worker围栏提交。"""
        with self._session_factory.begin() as db:
            operation = db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.task_id == task_id,
                    BillingOperation.status == BillingStatus.SETTLING,
                    BillingOperation.action == BillingAction.SETTLE,
                )
                .with_for_update()
            )
            if operation is None:
                return False
            operation.status = BillingStatus.SETTLED
            operation.last_error_code = None
            operation.updated_at = now
            return True

    def complete_release(self, task_id: str, now: datetime) -> bool:
        """只提交账务released和作品失败；任务终态由Worker锁令牌防止旧执行者覆盖。"""
        with self._session_factory.begin() as db:
            operation, task = self._load(db, task_id)
            if (
                operation is None
                or task is None
                or operation.status != BillingStatus.RELEASING
                or operation.action != BillingAction.RELEASE
            ):
                return False
            operation.status = BillingStatus.RELEASED
            operation.last_error_code = None
            operation.updated_at = now
            presentation = db.get(Presentation, task.presentation_id)
            if presentation is not None:
                presentation.status = "failed"
                presentation.updated_at = now
            return True

    def mark_billing_pending(
        self,
        task_id: str,
        action: BillingAction,
        error_code: str,
        now: datetime,
        *,
        hold_id: str | None = None,
    ) -> bool:
        """写动作终态未知时冻结任务；T18只能按既有动作键对账，禁止新reserve。"""
        with self._session_factory.begin() as db:
            operation, task = self._load(db, task_id)
            if operation is None or task is None or operation.status in {
                BillingStatus.SETTLED,
                BillingStatus.RELEASED,
                BillingStatus.RESERVE_FAILED,
            }:
                return False
            operation.action = action
            operation.status = BillingStatus.BILLING_PENDING
            if hold_id is not None:
                # reserve平台成功而本地放行失败时也必须保住hold，供T18按原键核对。
                operation.hold_id = hold_id
            operation.last_error_code = error_code[:64]
            operation.updated_at = now
            task.status = "billing_pending"
            task.stage = "billing_pending"
            task.retryable = False
            task.last_error_code = error_code[:64]
            task.error_message = "计费结果待确认"
            task.locked_by = None
            task.lock_token = None
            task.locked_until = None
            task.heartbeat_at = None
            task.updated_at = now
            presentation = db.get(Presentation, task.presentation_id)
            if presentation is not None:
                presentation.status = "billing_pending"
                presentation.updated_at = now
            return True

    @staticmethod
    def _fail_task(task: GenerationTask, error_code: str, now: datetime) -> None:
        task.status = "failed"
        task.stage = "failed"
        task.retryable = False
        task.last_error_code = error_code[:64]
        task.error_message = "计费前置检查失败"
        task.finished_at = now
        task.updated_at = now

    @staticmethod
    def _load(db, task_id: str):
        operation = db.scalar(
            select(BillingOperation)
            .where(BillingOperation.task_id == task_id)
            .with_for_update()
        )
        task = db.get(GenerationTask, task_id, with_for_update=True)
        return operation, task

    @staticmethod
    def _context(operation: BillingOperation) -> BillingWorkflowContext:
        if (
            operation.reserved_amount is None
            or operation.actual_amount is None
            or operation.reserve_key is None
            or operation.settle_key is None
            or operation.release_key is None
        ):
            raise ValueError("billing operation is incomplete")
        return BillingWorkflowContext(
            task_id=operation.task_id,
            owner_user_id=operation.owner_user_id,
            entitlement_id=int(operation.entitlement_id) if operation.entitlement_id else None,
            hold_id=operation.hold_id,
            reserved_amount=operation.reserved_amount,
            actual_amount=operation.actual_amount,
            reserve_key=operation.reserve_key,
            settle_key=operation.settle_key,
            release_key=operation.release_key,
        )


__all__ = [
    "BillingAction",
    "BillingStatus",
    "BillingWorkflowClaim",
    "BillingWorkflowContext",
    "BillingWorkflowRepository",
]
