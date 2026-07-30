"""T17 收费生成外层编排：reserve后运行，持久化后settle，明确失败release。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from ..integrations.moling import (
    MolingAuthenticationError,
    MolingBusinessError,
    MolingError,
    MolingProtocolError,
    MolingUnavailableError,
)
from ..repositories.billing import BillingAction, BillingStatus, BillingWorkflowRepository
from ..workers.runner import NonRetryableTaskError, TaskExecution, TaskHandler
from .billing import BillingPolicy, BillingPolicyError


class BillingWriteClient(Protocol):
    async def get_entitlement_balance(self, *, entitlement_id: int, user_id: int): ...

    async def reserve_entitlement(
        self, *, entitlement_id: int, user_id: int, amount: str, idempotency_key: str
    ): ...

    async def settle_entitlement(
        self, *, hold_id: int, actual_amount: str, idempotency_key: str
    ): ...

    async def release_entitlement(self, *, hold_id: int, idempotency_key: str): ...


class BillingGenerationOrchestrator:
    """平台写调用不在数据库事务内；每个动作先持久声明，再调用一次。"""

    def __init__(
        self,
        *,
        repository: BillingWorkflowRepository,
        client: BillingWriteClient,
        policy: BillingPolicy,
        now_factory: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self.repository = repository
        self.client = client
        self.policy = policy
        self.now_factory = now_factory

    async def prepare(self, task_id: str) -> str:
        """选择权益并预占；只有明确成功才开放任务给Agent Worker。"""
        claim = self.repository.begin_reserve(task_id, self.now_factory())
        if not claim.claimed:
            return self._prepare_state(claim.status)
        assert claim.context is not None
        context = claim.context
        try:
            selection = await self.policy.select_entitlement(
                self.client,
                user_id=context.owner_user_id,
                entitlement_id=context.entitlement_id,
            )
        except BillingPolicyError as error:
            self.repository.fail_reserve(task_id, error.code, self.now_factory())
            return "failed"
        except MolingError as error:
            # 权益查询是只读动作，失败时可确定尚未发生预占，因此不进入未知终态。
            self.repository.fail_reserve(
                task_id, self._safe_platform_code(error, "BILLING_ENTITLEMENT_LOOKUP_FAILED"),
                self.now_factory(),
            )
            return "failed"

        # 任务创建时已经固化票据指定权益；这里只防御性核对，绝不改选其他资产。
        if selection.entitlement_id != context.entitlement_id:
            self.repository.fail_reserve(
                task_id, "BILLING_ENTITLEMENT_MISMATCH", self.now_factory()
            )
            return "failed"
        try:
            reservation = await self.client.reserve_entitlement(
                entitlement_id=selection.entitlement_id,
                user_id=context.owner_user_id,
                amount=self._amount(selection.reserve_amount),
                idempotency_key=context.reserve_key,
            )
        except MolingBusinessError as error:
            mapped = self.policy.map_reserve_error(error)
            self.repository.fail_reserve(task_id, mapped.code, self.now_factory())
            return "failed"
        except (MolingUnavailableError, MolingProtocolError) as error:
            # 请求可能已在平台生效，禁止自动换权益或重复reserve。
            self.repository.mark_billing_pending(
                task_id, BillingAction.RESERVE,
                self._safe_platform_code(error, "BILLING_RESERVE_UNKNOWN"),
                self.now_factory(),
            )
            return "billing_pending"
        except MolingAuthenticationError as error:
            self.repository.fail_reserve(
                task_id, self._safe_platform_code(error, "BILLING_PLATFORM_AUTH_FAILED"),
                self.now_factory(),
            )
            return "failed"

        if not self.repository.complete_reserve(
            task_id, reservation.hold_id, self.now_factory()
        ):
            # 平台已成功但本地放行失败时冻结，并持久化hold供T18按原键核对。
            self.repository.mark_billing_pending(
                task_id,
                BillingAction.RESERVE,
                "BILLING_RESERVE_LOCAL_COMMIT_FAILED",
                self.now_factory(),
                hold_id=reservation.hold_id,
            )
            return "billing_pending"
        return "reserved"

    async def prepare_next(self) -> bool:
        """供常驻Worker发现持久计费意图；无任务返回false以进入正常轮询等待。"""
        task_id = self.repository.next_planned_task_id()
        if task_id is None:
            return False
        await self.prepare(task_id)
        return True

    def is_billing_task(self, task_id: str) -> bool:
        """隐藏仓储结构，处理器只依赖编排器公开的任务分类语义。"""
        return self.repository.has_operation(task_id)

    async def settle_after_success(self, task_id: str) -> str:
        claim = self.repository.begin_finalize(task_id, BillingAction.SETTLE, self.now_factory())
        if not claim.claimed:
            return "settled" if claim.status == BillingStatus.SETTLED else claim.status
        assert claim.context is not None and claim.context.hold_id is not None
        try:
            await self.client.settle_entitlement(
                hold_id=claim.context.hold_id,
                actual_amount=str(claim.context.actual_amount),
                idempotency_key=claim.context.settle_key,
            )
        except MolingError as error:
            self.repository.mark_billing_pending(
                task_id, BillingAction.SETTLE,
                self._safe_platform_code(error, "BILLING_SETTLE_UNKNOWN"),
                self.now_factory(),
            )
            return "billing_pending"
        if self.repository.complete_settle(task_id, self.now_factory()):
            return "settled"
        self.repository.mark_billing_pending(
            task_id,
            BillingAction.SETTLE,
            "BILLING_SETTLE_LOCAL_COMMIT_FAILED",
            self.now_factory(),
        )
        return "billing_pending"

    async def release_after_failure(self, task_id: str) -> str:
        claim = self.repository.begin_finalize(task_id, BillingAction.RELEASE, self.now_factory())
        if not claim.claimed:
            return "released" if claim.status == BillingStatus.RELEASED else claim.status
        assert claim.context is not None and claim.context.hold_id is not None
        try:
            await self.client.release_entitlement(
                hold_id=claim.context.hold_id,
                idempotency_key=claim.context.release_key,
            )
        except MolingError as error:
            self.repository.mark_billing_pending(
                task_id, BillingAction.RELEASE,
                self._safe_platform_code(error, "BILLING_RELEASE_UNKNOWN"),
                self.now_factory(),
            )
            return "billing_pending"
        if self.repository.complete_release(task_id, self.now_factory()):
            return "released"
        self.repository.mark_billing_pending(
            task_id,
            BillingAction.RELEASE,
            "BILLING_RELEASE_LOCAL_COMMIT_FAILED",
            self.now_factory(),
        )
        return "billing_pending"

    def freeze_unknown_generation_result(self, task_id: str) -> None:
        """产物探测异常时保留预占，不猜测应结算还是释放。"""
        self.repository.mark_billing_pending(
            task_id, BillingAction.INSPECT, "GENERATION_RESULT_UNKNOWN", self.now_factory()
        )

    @staticmethod
    def _prepare_state(status: str) -> str:
        if status in {
            BillingStatus.RESERVED,
            BillingStatus.SETTLING,
            BillingStatus.SETTLED,
            BillingStatus.RELEASING,
            BillingStatus.RELEASED,
        }:
            return "reserved"
        if status == BillingStatus.RESERVE_FAILED:
            return "failed"
        return status

    @staticmethod
    def _amount(value) -> str:
        return format(value, "f")

    @staticmethod
    def _safe_platform_code(error: MolingError, fallback: str) -> str:
        return f"{fallback}_{error.platform_code}" if error.platform_code is not None else fallback


class BillingTaskHandler:
    """为既有Agent处理器增加计费后置动作；非计费任务保持原行为。"""

    def __init__(self, *, inner: TaskHandler, orchestrator: BillingGenerationOrchestrator) -> None:
        self.inner = inner
        self.orchestrator = orchestrator

    async def execute(self, task: TaskExecution) -> None:
        if not self.orchestrator.is_billing_task(task.task_id):
            await self.inner.execute(task)
            return
        try:
            await self.inner.execute(task)
        except asyncio.CancelledError:
            # wait_for超时会取消处理器；必须先确认产物再决定结算/释放，并阻止同任务重跑Agent。
            outcome = await asyncio.shield(self._resolve_failed_execution(task))
            if outcome == "released":
                raise NonRetryableTaskError(
                    "GENERATION_TIMEOUT", "生成超时，预占已处理"
                ) from None
            return
        except Exception:
            outcome = await self._resolve_failed_execution(task)
            if outcome == "released":
                raise NonRetryableTaskError(
                    "GENERATION_FAILED", "生成失败，预占已处理"
                ) from None
            return

        try:
            persisted = await self.inner.has_persisted_result(task)
        except Exception:
            self.orchestrator.freeze_unknown_generation_result(task.task_id)
            return
        if not persisted:
            await self.orchestrator.release_after_failure(task.task_id)
            raise NonRetryableTaskError(
                "GENERATION_PERSISTENCE_NOT_CONFIRMED", "生成结果未完成持久化"
            ) from None
        await self.orchestrator.settle_after_success(task.task_id)

    async def _resolve_failed_execution(self, task: TaskExecution) -> str:
        """异常也先只读探测产物；探测不确定时保留hold交给T18。"""
        try:
            persisted = await self.inner.has_persisted_result(task)
        except Exception:
            self.orchestrator.freeze_unknown_generation_result(task.task_id)
            return "billing_pending"
        if persisted:
            return await self.orchestrator.settle_after_success(task.task_id)
        return await self.orchestrator.release_after_failure(task.task_id)

    async def has_persisted_result(self, task: TaskExecution) -> bool:
        if not self.orchestrator.is_billing_task(task.task_id):
            return await self.inner.has_persisted_result(task)
        try:
            persisted = await self.inner.has_persisted_result(task)
        except Exception:
            self.orchestrator.freeze_unknown_generation_result(task.task_id)
            raise RuntimeError("generation result inspection pending") from None
        if persisted:
            outcome = await self.orchestrator.settle_after_success(task.task_id)
            if outcome == "settled":
                return True
            raise RuntimeError("billing settlement pending")
        outcome = await self.orchestrator.release_after_failure(task.task_id)
        if outcome == "released":
            return False
        raise RuntimeError("billing release pending")


__all__ = ["BillingGenerationOrchestrator", "BillingTaskHandler"]
