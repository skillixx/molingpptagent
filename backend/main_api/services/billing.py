"""T15 预付计费策略：只使用票据指定权益，余额只作为体验提示。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from ..integrations.moling import EntitlementBalance, MolingBusinessError


class BillingPolicyError(RuntimeError):
    """可安全映射到业务API的计费策略错误，不携带平台原始正文。"""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class EntitlementSelection:
    entitlement_id: int
    reserve_amount: Decimal
    settle_amount: Decimal
    unlimited: bool
    expires_at: datetime | None


@dataclass(frozen=True)
class BalanceHint:
    can_attempt_reserve: bool
    remaining: Decimal | None
    final_authority: str = "platform_reserve"


class EntitlementClient(Protocol):
    async def get_entitlement_balance(
        self, *, entitlement_id: int, user_id: int
    ) -> EntitlementBalance: ...


class BillingPolicy:
    """固定积分第一版策略；最终可扣性始终由平台原子reserve决定。"""

    def __init__(
        self,
        *,
        reserve_points: int,
        settle_points: int,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        if reserve_points <= 0 or settle_points <= 0:
            raise ValueError("计费积分必须为正整数")
        if settle_points > reserve_points:
            raise ValueError("固定结算积分不能超过预占积分")
        self.reserve_amount = Decimal(reserve_points)
        self.settle_amount = Decimal(settle_points)
        self.now_factory = now_factory or (lambda: datetime.now(UTC))

    async def select_entitlement(
        self,
        client: EntitlementClient,
        *,
        user_id: int,
        entitlement_id: int | None,
    ) -> EntitlementSelection:
        """只校验墨灵票据指定的权益，禁止在同商品的其他资产间猜选。"""
        if type(entitlement_id) is not int or entitlement_id <= 0:
            raise BillingPolicyError(
                "BILLING_ENTITLEMENT_REQUIRED",
                "当前会话未绑定可计费权益",
            )
        now = self._utc(self.now_factory())
        selected = await client.get_entitlement_balance(
            entitlement_id=entitlement_id,
            user_id=user_id,
        )
        expiry = self._expiry(selected)
        if (
            selected.entitlement_id != entitlement_id
            or selected.user_id != user_id
            or selected.status != "active"
            or not selected.usable
            or (expiry is not None and expiry <= now)
        ):
            raise BillingPolicyError(
                "BILLING_ENTITLEMENT_UNAVAILABLE",
                "指定的 PPT 权益当前不可用",
            )
        remaining = self._remaining(selected)
        if remaining is not None and remaining < self.reserve_amount:
            raise BillingPolicyError(
                "BILLING_ENTITLEMENT_INSUFFICIENT",
                "指定的 PPT 权益额度不足",
            )
        return EntitlementSelection(
            entitlement_id=selected.entitlement_id,
            reserve_amount=self.reserve_amount,
            settle_amount=self.settle_amount,
            unlimited=selected.remaining is None,
            expires_at=expiry,
        )

    async def get_balance_hint(
        self,
        client: EntitlementClient,
        *,
        user_id: int,
        selection: EntitlementSelection,
    ) -> BalanceHint:
        """余额查询只改善UX；即使提示足额，T17仍必须调用平台原子reserve。"""
        balance = await client.get_entitlement_balance(
            entitlement_id=selection.entitlement_id,
            user_id=user_id,
        )
        if balance.user_id != user_id or balance.entitlement_id != selection.entitlement_id:
            raise BillingPolicyError(
                "BILLING_PLATFORM_PROTOCOL_ERROR", "计费平台响应不符合约定"
            )
        expiry = self._expiry(balance)
        usable = (
            balance.status == "active"
            and balance.usable
            and (expiry is None or expiry > self._utc(self.now_factory()))
        )
        remaining = self._remaining(balance)
        return BalanceHint(
            can_attempt_reserve=usable
            and (remaining is None or remaining >= selection.reserve_amount),
            remaining=remaining,
        )

    @staticmethod
    def map_reserve_error(error: MolingBusinessError) -> BillingPolicyError:
        """把平台并发终态映射成稳定错误；不复用下游消息。"""
        if error.platform_code == 60005:
            return BillingPolicyError(
                "BILLING_ENTITLEMENT_INSUFFICIENT", "可用权益额度不足"
            )
        if error.platform_code == 40003:
            return BillingPolicyError(
                "BILLING_PLATFORM_AUTH_FAILED", "计费平台鉴权失败"
            )
        return BillingPolicyError(
            "BILLING_PLATFORM_REJECTED",
            "计费平台拒绝了本次请求",
            retryable=error.retryable,
        )

    @staticmethod
    def _remaining(item: EntitlementBalance) -> Decimal | None:
        return None if item.remaining is None else Decimal(item.remaining)

    @staticmethod
    def _expiry(item: EntitlementBalance) -> datetime | None:
        if item.expires_at is None:
            return None
        return BillingPolicy._utc(item.expires_at)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


__all__ = [
    "BalanceHint",
    "BillingPolicy",
    "BillingPolicyError",
    "EntitlementSelection",
]
