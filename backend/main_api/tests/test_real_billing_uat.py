"""真实积分 UAT 工具的安全围栏与单笔闭环测试。"""

from __future__ import annotations

import asyncio

import pytest

from backend.main_api.integrations.moling import (
    EntitlementBalance,
    EntitlementFinalization,
    EntitlementReservation,
    MolingUnavailableError,
)
from backend.main_api.tools.real_billing_uat import UatTarget, execute_uat


TARGET = UatTarget(
    user_id=479,
    asset_id=990206,
    entitlement_id=990306,
    product_id=73,
    amount=1,
    max_points=3,
)


class FakeClient:
    def __init__(self) -> None:
        self.used = 2051
        self.reserved = 0
        self.calls: list[tuple[str, int]] = []

    async def get_entitlement_balance(self, *, entitlement_id: int, user_id: int):
        self.calls.append(("balance", entitlement_id))
        return EntitlementBalance(
            entitlement_id=entitlement_id,
            user_id=user_id,
            quota_total="10000",
            quota_used=str(self.used),
            quota_reserved=str(self.reserved),
            remaining=str(10000 - self.used - self.reserved),
            status="active",
            expires_at=None,
            usable=True,
        )

    async def reserve_entitlement(
        self, *, entitlement_id: int, user_id: int, amount: str, idempotency_key: str
    ):
        self.calls.append(("reserve", entitlement_id))
        self.reserved += int(amount)
        return EntitlementReservation(
            hold_id=51,
            reserved=amount,
            available=str(10000 - self.used - self.reserved),
            status="holding",
        )

    async def settle_entitlement(
        self, *, hold_id: int, actual_amount: str, idempotency_key: str
    ):
        self.calls.append(("settle", hold_id))
        self.reserved -= int(actual_amount)
        self.used += int(actual_amount)
        return EntitlementFinalization(
            hold_id=hold_id,
            status="settled",
            settled_amount=actual_amount,
            quota_used=str(self.used),
            quota_reserved=str(self.reserved),
            available=str(10000 - self.used),
        )


class FailingClient(FakeClient):
    def __init__(self, *, fail_action: str) -> None:
        super().__init__()
        self.fail_action = fail_action

    async def reserve_entitlement(
        self, *, entitlement_id: int, user_id: int, amount: str, idempotency_key: str
    ):
        if self.fail_action == "reserve":
            raise MolingUnavailableError(
                "预占响应未知",
                request_id="req_uat_reserve",
                retryable=True,
            )
        return await super().reserve_entitlement(
            entitlement_id=entitlement_id,
            user_id=user_id,
            amount=amount,
            idempotency_key=idempotency_key,
        )

    async def settle_entitlement(
        self, *, hold_id: int, actual_amount: str, idempotency_key: str
    ):
        if self.fail_action == "settle":
            raise MolingUnavailableError(
                "结算响应未知",
                request_id="req_uat_settle",
                retryable=True,
            )
        return await super().settle_entitlement(
            hold_id=hold_id,
            actual_amount=actual_amount,
            idempotency_key=idempotency_key,
        )


def test_read_only_mode_never_creates_hold() -> None:
    client = FakeClient()
    result = asyncio.run(execute_uat(
        client, TARGET, execute=False, confirmation=None  # type: ignore[arg-type]
    ))
    assert result.status == "ready"
    assert client.calls == [("balance", 990306)]


def test_exact_confirmation_executes_one_targeted_settlement() -> None:
    client = FakeClient()
    result = asyncio.run(execute_uat(
        client,
        TARGET,
        execute=True,
        confirmation="asset-990206-entitlement-990306-amount-1-max-3",
    ))
    assert result.status == "settled"
    assert result.quota_used_after == "2052"
    assert result.quota_reserved_after == "0"
    assert result.reserve_key is not None and result.reserve_key.endswith(":reserve")
    assert result.settle_key == result.reserve_key.removesuffix(":reserve") + ":settle"
    assert client.calls == [
        ("balance", 990306),
        ("reserve", 990306),
        ("settle", 51),
        ("balance", 990306),
    ]


@pytest.mark.parametrize("target", [
    UatTarget(479, 990206, 990306, 73, 4, 3),
    UatTarget(479, 990206, 990306, 73, 1, 4),
])
def test_authorized_cap_cannot_be_exceeded(target: UatTarget) -> None:
    with pytest.raises(ValueError):
        asyncio.run(execute_uat(FakeClient(), target, execute=False, confirmation=None))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("fail_action", "expected_status", "has_hold"),
    [
        ("reserve", "reserve_pending", False),
        ("settle", "billing_pending", True),
    ],
)
def test_uncertain_write_keeps_original_recovery_identifiers(
    fail_action: str,
    expected_status: str,
    has_hold: bool,
) -> None:
    result = asyncio.run(execute_uat(
        FailingClient(fail_action=fail_action),
        TARGET,
        execute=True,
        confirmation="asset-990206-entitlement-990306-amount-1-max-3",
    ))

    assert result.status == expected_status
    assert result.reserve_key is not None and result.reserve_key.endswith(":reserve")
    assert (result.hold_id is not None) is has_hold
    assert (result.settle_key is not None) is has_hold
