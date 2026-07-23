"""只读验证墨灵权益列表与余额；输出不含身份、权益ID、额度、令牌或下游正文。"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main_api.integrations.moling import MolingClient, MolingError


SESSION_DB = ROOT / "output" / "t04" / "real-entry.db"


def _latest_user_id() -> int:
    """以SQLite只读URI取得已验证Session主体，禁止修改T04证据库。"""
    if not SESSION_DB.is_file():
        raise RuntimeError("本地只读Session证据库不存在")
    connection = sqlite3.connect(f"file:{SESSION_DB.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT user_id FROM app_sessions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None or not isinstance(row[0], int) or row[0] <= 0:
        raise RuntimeError("本地只读Session证据不可用")
    return row[0]


async def _verify() -> dict[str, object]:
    load_dotenv(ROOT / ".env")
    base_url = os.getenv("MOLING_API_BASE_URL", "").strip()
    token = os.getenv("INTERNAL_API_TOKEN", "").strip()
    app_id = int(os.getenv("MOLING_APP_ID", "0"))
    product_id = int(os.getenv("MOLING_PRODUCT_ID", "0"))
    if not base_url or not token or app_id <= 0 or product_id <= 0:
        raise RuntimeError("墨灵只读验证配置不完整")

    user_id = _latest_user_id()
    client = MolingClient(
        base_url=base_url,
        internal_api_token=token,
        app_id=app_id,
        product_id=product_id,
    )
    entitlements = await client.list_user_entitlements(user_id=user_id)
    now = datetime.now(UTC)
    def active_expiry(item) -> datetime | None:
        if item.expires_at is None:
            return None
        return (
            item.expires_at.replace(tzinfo=UTC)
            if item.expires_at.tzinfo is None
            else item.expires_at.astimezone(UTC)
        )
    usable = [
        item for item in entitlements
        if item.status == "active"
        and item.usable
        and (active_expiry(item) is None or active_expiry(item) > now)
    ]
    usable.sort(key=lambda item: (
        active_expiry(item) or datetime.max.replace(tzinfo=UTC), item.entitlement_id
    ))
    balance_checked = False
    if usable:
        # 只读余额用于验证契约，最终可扣性仍由后续T17的原子reserve决定。
        await client.get_entitlement_balance(
            entitlement_id=usable[0].entitlement_id,
            user_id=user_id,
        )
        balance_checked = True
    return {
        "mode": "real_platform_read_only",
        "entitlement_count": len(entitlements),
        "usable_count": len(usable),
        "balance_checked": balance_checked,
        "billing_enabled": False,
    }


def main() -> int:
    try:
        result = asyncio.run(_verify())
    except MolingError as exc:
        print(json.dumps({
            "mode": "real_platform_read_only",
            "verified": False,
            "error_type": type(exc).__name__,
            "retryable": exc.retryable,
        }, ensure_ascii=False))
        return 1
    except (RuntimeError, ValueError, sqlite3.Error):
        print(json.dumps({
            "mode": "real_platform_read_only",
            "verified": False,
            "error_type": "LOCAL_PREREQUISITE_UNAVAILABLE",
        }, ensure_ascii=False))
        return 1
    print(json.dumps({**result, "verified": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
