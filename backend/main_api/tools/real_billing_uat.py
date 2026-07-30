"""受控执行一笔墨灵真实预占与结算；默认只读，必须显式确认才写入。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main_api.integrations.moling import MolingClient, MolingError


@dataclass(frozen=True)
class UatTarget:
    user_id: int
    asset_id: int
    entitlement_id: int
    product_id: int
    amount: int
    max_points: int


@dataclass(frozen=True)
class UatResult:
    mode: str
    asset_id: int
    entitlement_id: int
    amount: int
    hold_id: int | None
    reserve_key: str | None
    settle_key: str | None
    status: str
    quota_used_before: str
    quota_used_after: str | None
    quota_reserved_before: str
    quota_reserved_after: str | None


def _validate_target(target: UatTarget) -> None:
    """本工具只允许正整数小额测试，累计授权上限不得超过 3 积分。"""
    values = (
        target.user_id,
        target.asset_id,
        target.entitlement_id,
        target.product_id,
        target.amount,
        target.max_points,
    )
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError("UAT目标参数无效")
    if target.max_points > 3 or target.amount > target.max_points:
        raise ValueError("UAT积分超过授权上限")


def _confirmation(target: UatTarget) -> str:
    return (
        f"asset-{target.asset_id}-entitlement-{target.entitlement_id}"
        f"-amount-{target.amount}-max-{target.max_points}"
    )


async def execute_uat(
    client: MolingClient,
    target: UatTarget,
    *,
    execute: bool,
    confirmation: str | None,
) -> UatResult:
    """先读取并严格核对指定权益；显式确认后只创建一个稳定预占并结算。"""
    _validate_target(target)
    before = await client.get_entitlement_balance(
        entitlement_id=target.entitlement_id,
        user_id=target.user_id,
    )
    if (
        before.entitlement_id != target.entitlement_id
        or before.user_id != target.user_id
        or before.status != "active"
        or not before.usable
    ):
        raise RuntimeError("指定权益当前不可用于 UAT")
    if before.remaining is not None and Decimal(before.remaining) < target.amount:
        raise RuntimeError("指定权益额度不足")

    if not execute:
        return UatResult(
            mode="read_only",
            asset_id=target.asset_id,
            entitlement_id=target.entitlement_id,
            amount=target.amount,
            hold_id=None,
            reserve_key=None,
            settle_key=None,
            status="ready",
            quota_used_before=before.quota_used,
            quota_used_after=None,
            quota_reserved_before=before.quota_reserved,
            quota_reserved_after=None,
        )
    if confirmation != _confirmation(target):
        raise ValueError("UAT确认文本不匹配")

    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    reserve_key = f"uat:ppt:{target.asset_id}:{timestamp}:{uuid4().hex[:12]}:reserve"
    settle_key = reserve_key.removesuffix(":reserve") + ":settle"
    amount = str(target.amount)
    try:
        reservation = await client.reserve_entitlement(
            entitlement_id=target.entitlement_id,
            user_id=target.user_id,
            amount=amount,
            idempotency_key=reserve_key,
        )
    except MolingError:
        # 预占响应不确定时保留原幂等键，禁止换键重试或继续生成。
        return UatResult(
            mode="real_write",
            asset_id=target.asset_id,
            entitlement_id=target.entitlement_id,
            amount=target.amount,
            hold_id=None,
            reserve_key=reserve_key,
            settle_key=None,
            status="reserve_pending",
            quota_used_before=before.quota_used,
            quota_used_after=None,
            quota_reserved_before=before.quota_reserved,
            quota_reserved_after=None,
        )
    try:
        finalization = await client.settle_entitlement(
            hold_id=reservation.hold_id,
            actual_amount=amount,
            idempotency_key=settle_key,
        )
    except MolingError:
        # 不确定时既不换权益也不释放，保留原 hold 供同键对账恢复。
        return UatResult(
            mode="real_write",
            asset_id=target.asset_id,
            entitlement_id=target.entitlement_id,
            amount=target.amount,
            hold_id=reservation.hold_id,
            reserve_key=reserve_key,
            settle_key=settle_key,
            status="billing_pending",
            quota_used_before=before.quota_used,
            quota_used_after=None,
            quota_reserved_before=before.quota_reserved,
            quota_reserved_after=None,
        )

    try:
        after = await client.get_entitlement_balance(
            entitlement_id=target.entitlement_id,
            user_id=target.user_id,
        )
    except MolingError:
        # 平台已返回结算终态，但余额复核失败时仍保留完整恢复标识并退出非零。
        return UatResult(
            mode="real_write",
            asset_id=target.asset_id,
            entitlement_id=target.entitlement_id,
            amount=target.amount,
            hold_id=finalization.hold_id,
            reserve_key=reserve_key,
            settle_key=settle_key,
            status="settlement_verification_pending",
            quota_used_before=before.quota_used,
            quota_used_after=None,
            quota_reserved_before=before.quota_reserved,
            quota_reserved_after=None,
        )
    if Decimal(after.quota_used) - Decimal(before.quota_used) != target.amount:
        raise RuntimeError("UAT结算后的已用额度变化不符合预期")
    if Decimal(after.quota_reserved) != Decimal(before.quota_reserved):
        raise RuntimeError("UAT结算后仍残留本轮新增预占")
    return UatResult(
        mode="real_write",
        asset_id=target.asset_id,
        entitlement_id=target.entitlement_id,
        amount=target.amount,
        hold_id=finalization.hold_id,
        reserve_key=reserve_key,
        settle_key=settle_key,
        status=finalization.status,
        quota_used_before=before.quota_used,
        quota_used_after=after.quota_used,
        quota_reserved_before=before.quota_reserved,
        quota_reserved_after=after.quota_reserved,
    )


def _client_from_environment(product_id: int) -> MolingClient:
    load_dotenv(ROOT / ".env")
    base_url = os.getenv("MOLING_API_BASE_URL", "").strip()
    token = os.getenv("INTERNAL_API_TOKEN", "").strip()
    app_id = int(os.getenv("MOLING_APP_ID", "0"))
    configured_product_id = int(os.getenv("MOLING_PRODUCT_ID", "0"))
    if not base_url or not token or app_id <= 0 or configured_product_id <= 0:
        raise RuntimeError("墨灵 UAT 配置不完整")
    if configured_product_id != product_id:
        raise RuntimeError("墨灵 UAT 商品与应用配置不一致")
    return MolingClient(
        base_url=base_url,
        internal_api_token=token,
        app_id=app_id,
        product_id=configured_product_id,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="受控墨灵真实积分 UAT")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--asset-id", type=int, required=True)
    parser.add_argument("--entitlement-id", type=int, required=True)
    parser.add_argument("--product-id", type=int, required=True)
    parser.add_argument("--amount", type=int, required=True)
    parser.add_argument("--max-points", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm")
    return parser


def main() -> int:
    args = _parser().parse_args()
    target = UatTarget(
        user_id=args.user_id,
        asset_id=args.asset_id,
        entitlement_id=args.entitlement_id,
        product_id=args.product_id,
        amount=args.amount,
        max_points=args.max_points,
    )
    try:
        result = asyncio.run(execute_uat(
            _client_from_environment(target.product_id),
            target,
            execute=args.execute,
            confirmation=args.confirm,
        ))
    except (MolingError, RuntimeError, ValueError) as exc:
        print(json.dumps({
            "verified": False,
            "error_type": type(exc).__name__,
        }, ensure_ascii=False))
        return 1
    print(json.dumps({"verified": True, **asdict(result)}, ensure_ascii=False))
    return 0 if result.status in {"ready", "settled"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
