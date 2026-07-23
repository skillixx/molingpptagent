"""T15 预付权益选择、固定积分策略和平台并发拒绝映射测试。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from backend.main_api.integrations.moling import EntitlementBalance, MolingBusinessError
from backend.main_api.services.billing import BillingPolicy, BillingPolicyError


NOW = datetime(2026, 7, 23, 6, 0, tzinfo=UTC)


def entitlement(
    entitlement_id: int,
    *,
    remaining: str | None,
    expires_at: str | None,
    usable: bool = True,
    status: str = "active",
    user_id: int = 9,
) -> EntitlementBalance:
    return EntitlementBalance.model_validate({
        "entitlement_id": entitlement_id,
        "user_id": user_id,
        "quota_total": None if remaining is None else "100",
        "quota_used": "0",
        "quota_reserved": "0",
        "remaining": remaining,
        "status": status,
        "expires_at": expires_at,
        "usable": usable,
    })


class FakeMolingClient:
    def __init__(self, items: tuple[EntitlementBalance, ...]) -> None:
        self.items = items
        self.balance = items[0] if items else None

    async def list_user_entitlements(self, *, user_id: int):
        return self.items

    async def get_entitlement_balance(self, *, entitlement_id: int, user_id: int):
        assert self.balance is not None
        return self.balance


def run(coroutine):
    return asyncio.run(coroutine)


def test_selects_earliest_expiring_single_entitlement_and_never_splits() -> None:
    policy = BillingPolicy(reserve_points=10, settle_points=8, now_factory=lambda: NOW)
    client = FakeMolingClient((
        entitlement(1, remaining="50", expires_at="2026-07-22T00:00:00Z"),  # 已过期
        entitlement(2, remaining="9", expires_at="2026-07-24T00:00:00Z"),
        entitlement(3, remaining="20", expires_at="2026-07-26T00:00:00Z"),
        entitlement(4, remaining="20", expires_at="2026-07-25T00:00:00Z"),
        entitlement(5, remaining=None, expires_at=None),
    ))

    selected = run(policy.select_entitlement(client, user_id=9))

    assert selected.entitlement_id == 4
    assert selected.reserve_amount == Decimal("10")
    assert selected.settle_amount == Decimal("8")
    assert selected.unlimited is False


def test_unlimited_entitlement_is_usable_and_null_expiry_sorts_last() -> None:
    policy = BillingPolicy(reserve_points=10, settle_points=10, now_factory=lambda: NOW)
    selected = run(policy.select_entitlement(
        FakeMolingClient((entitlement(8, remaining=None, expires_at=None),)),
        user_id=9,
    ))
    assert selected.entitlement_id == 8
    assert selected.unlimited is True


def test_two_small_entitlements_are_not_combined_and_report_insufficient() -> None:
    policy = BillingPolicy(reserve_points=10, settle_points=8, now_factory=lambda: NOW)
    client = FakeMolingClient((
        entitlement(1, remaining="6", expires_at="2026-07-24T00:00:00Z"),
        entitlement(2, remaining="6", expires_at="2026-07-25T00:00:00Z"),
    ))
    with pytest.raises(BillingPolicyError) as exc_info:
        run(policy.select_entitlement(client, user_id=9))
    assert exc_info.value.code == "BILLING_ENTITLEMENT_INSUFFICIENT"
    assert exc_info.value.retryable is False


def test_no_active_usable_entitlement_has_stable_error() -> None:
    policy = BillingPolicy(reserve_points=10, settle_points=8, now_factory=lambda: NOW)
    client = FakeMolingClient((
        entitlement(1, remaining="50", expires_at="2026-07-24T00:00:00Z", usable=False, status="suspended"),
    ))
    with pytest.raises(BillingPolicyError) as exc_info:
        run(policy.select_entitlement(client, user_id=9))
    assert exc_info.value.code == "BILLING_ENTITLEMENT_UNAVAILABLE"


def test_balance_is_only_ux_hint_and_platform_60005_remains_final_authority() -> None:
    policy = BillingPolicy(reserve_points=10, settle_points=8, now_factory=lambda: NOW)
    selected = run(policy.select_entitlement(
        FakeMolingClient((entitlement(8, remaining="20", expires_at=None),)),
        user_id=9,
    ))
    changed = entitlement(8, remaining="0", expires_at=None, usable=False)
    client = FakeMolingClient((changed,))
    hint = run(policy.get_balance_hint(client, user_id=9, selection=selected))
    assert hint.can_attempt_reserve is False
    assert hint.final_authority == "platform_reserve"

    platform_error = MolingBusinessError(
        "平台拒绝", request_id="safe-request", retryable=False, platform_code=60005
    )
    mapped = policy.map_reserve_error(platform_error)
    assert mapped.code == "BILLING_ENTITLEMENT_INSUFFICIENT"
    assert mapped.retryable is False
    assert "平台拒绝" not in str(mapped)


def test_fixed_settlement_cannot_exceed_reserved_points() -> None:
    with pytest.raises(ValueError):
        BillingPolicy(reserve_points=8, settle_points=9)
