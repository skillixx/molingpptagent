"""T18 billing_pending 对账 Worker。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Protocol

from ..integrations.moling import EntitlementFinalization, MolingError
from ..repositories.billing import BillingAction
from ..repositories.reconciliation import BillingReconciliationRepository, ReconciliationClaim
from .runner import TaskExecution, TaskHandler


logger = logging.getLogger(__name__)


class BillingReplayClient(Protocol):
    """只暴露可安全幂等重放的 settle/release，刻意不提供 reserve。"""

    async def settle_entitlement(
        self, *, hold_id: int, actual_amount: str, idempotency_key: str
    ) -> EntitlementFinalization: ...

    async def release_entitlement(
        self, *, hold_id: int, idempotency_key: str
    ) -> EntitlementFinalization: ...


class BillingReconciliationWorker:
    """每轮只处理一个到期账务动作，便于常驻 Worker 公平轮询业务任务。"""

    def __init__(
        self,
        *,
        repository: BillingReconciliationRepository,
        client: BillingReplayClient,
        result_inspector: TaskHandler,
        base_interval_seconds: int,
        inflight_stale_seconds: int,
        max_retries: int,
        now_factory=datetime.utcnow,
    ) -> None:
        if (
            base_interval_seconds <= 0
            or inflight_stale_seconds <= 0
            or max_retries <= 0
        ):
            raise ValueError("对账退避、在途租约和重试上限必须大于零")
        self.repository = repository
        self.client = client
        self.result_inspector = result_inspector
        self.base_interval_seconds = base_interval_seconds
        self.inflight_stale_seconds = inflight_stale_seconds
        self.max_retries = max_retries
        self.now_factory = now_factory
        self._last_snapshot_at: datetime | None = None

    async def run_once(self) -> bool:
        now = self.now_factory()
        await self._observe(now)
        claim = await asyncio.to_thread(
            self.repository.claim_due,
            now=now,
            base_interval_seconds=self.base_interval_seconds,
            inflight_stale_seconds=self.inflight_stale_seconds,
            max_retries=self.max_retries,
        )
        if claim is None:
            return False

        if claim.action == BillingAction.RESERVE:
            # 平台没有 hold 状态查询接口；未知 reserve 绝不能再次扣减额度。
            await asyncio.to_thread(
                self.repository.mark_manual,
                claim.task_id,
                "BILLING_RESERVE_REQUIRES_MANUAL_REVIEW",
                self.now_factory(),
            )
            return True

        action = claim.action
        if action == BillingAction.INSPECT:
            try:
                persisted = await self.result_inspector.has_persisted_result(
                    self._execution(claim)
                )
            except Exception:
                await self._failure(claim.task_id, "GENERATION_RESULT_INSPECTION_FAILED")
                return True
            action = BillingAction.SETTLE if persisted else BillingAction.RELEASE
            selected = await asyncio.to_thread(
                self.repository.choose_action, claim.task_id, action, self.now_factory()
            )
            if not selected:
                return True

        hold_id = claim.hold_id
        key = claim.settle_key if action == BillingAction.SETTLE else claim.release_key
        if not hold_id or not key or (action == BillingAction.SETTLE and claim.actual_amount is None):
            await asyncio.to_thread(
                self.repository.mark_manual,
                claim.task_id,
                "BILLING_RECONCILIATION_DATA_INCOMPLETE",
                self.now_factory(),
            )
            return True

        try:
            if action == BillingAction.SETTLE:
                await self.client.settle_entitlement(
                    hold_id=hold_id,
                    actual_amount=str(claim.actual_amount),
                    idempotency_key=key,
                )
            else:
                await self.client.release_entitlement(
                    hold_id=hold_id,
                    idempotency_key=key,
                )
        except (MolingError, ValueError):
            # 仅记录稳定分类，不保存下游异常正文、request_id 或任何请求参数。
            await self._failure(claim.task_id, f"BILLING_RECONCILE_{action.value.upper()}_FAILED")
            return True

        await asyncio.to_thread(
            self.repository.resolve, claim.task_id, action, self.now_factory()
        )
        return True

    async def _observe(self, now: datetime) -> None:
        """按基础退避周期输出聚合计数，避免高频轮询刷日志或泄露账务标识。"""
        if (
            self._last_snapshot_at is not None
            and (now - self._last_snapshot_at).total_seconds()
            < self.base_interval_seconds
        ):
            return
        snapshot = await asyncio.to_thread(
            self.repository.operational_snapshot,
            now=now,
            stale_seconds=self.inflight_stale_seconds,
        )
        self._last_snapshot_at = now
        level = (
            logging.WARNING
            if snapshot.stale_hold_count
            or snapshot.manual_required_count
            or snapshot.error_count
            else logging.INFO
        )
        logger.log(
            level,
            "billing_reconciliation_snapshot pending=%d stale_holds=%d manual=%d errors=%d",
            snapshot.pending_count,
            snapshot.stale_hold_count,
            snapshot.manual_required_count,
            snapshot.error_count,
            extra={
                "billing_pending_count": snapshot.pending_count,
                "billing_stale_hold_count": snapshot.stale_hold_count,
                "billing_manual_required_count": snapshot.manual_required_count,
                "billing_error_count": snapshot.error_count,
            },
        )

    async def _failure(self, task_id: str, code: str) -> None:
        await asyncio.to_thread(
            self.repository.record_failure,
            task_id,
            code,
            max_retries=self.max_retries,
            now=self.now_factory(),
        )

    @staticmethod
    def _execution(claim: ReconciliationClaim) -> TaskExecution:
        """探测输入沿用原任务快照；损坏输入会走安全失败和有限重试。"""
        payload = json.loads(claim.input_json)
        if not isinstance(payload, dict):
            raise ValueError("任务输入无效")
        return TaskExecution(
            task_id=claim.task_id,
            presentation_id=claim.presentation_id,
            owner_user_id=claim.owner_user_id,
            request_id=claim.request_id,
            input=payload,
            attempt=claim.attempt,
            max_attempts=claim.max_attempts,
        )


__all__ = ["BillingReconciliationWorker"]
