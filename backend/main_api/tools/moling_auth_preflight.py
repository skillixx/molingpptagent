"""用只读请求判断墨灵内部Token/IP主闸，不消费一次性登录票据。"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

import dotenv

from backend.main_api.core.config import Settings, load_settings
from backend.main_api.integrations.moling import (
    MolingAuthenticationError,
    MolingBusinessError,
    MolingClient,
    MolingProtocolError,
    MolingUnavailableError,
)


# 该用户ID只用于只读空查询，不对应业务用户，也不会产生余额、权益或Session写入。
PREFLIGHT_SENTINEL_USER_ID = 2_147_483_647
ProbeStatus = Literal["accepted", "rejected", "unreachable", "protocol_error"]


@dataclass(frozen=True)
class ProbeResult:
    """只保留稳定分类、请求ID和平台码，绝不携带响应正文或配置值。"""

    status: ProbeStatus
    request_id: str
    platform_code: int | None


async def probe_internal_auth(client: MolingClient, request_id: str) -> ProbeResult:
    """执行一次只读权益查询；任何非鉴权业务响应都证明Token/IP主闸已通过。"""

    try:
        await client.list_user_entitlements(user_id=PREFLIGHT_SENTINEL_USER_ID)
    except MolingAuthenticationError as exc:
        return ProbeResult("rejected", exc.request_id, exc.platform_code)
    except MolingUnavailableError as exc:
        return ProbeResult("unreachable", exc.request_id, exc.platform_code)
    except MolingProtocolError as exc:
        return ProbeResult("protocol_error", exc.request_id, exc.platform_code)
    except MolingBusinessError as exc:
        # 按冻结契约，鉴权失败只能是40003；其他业务码说明请求已越过内部主闸。
        return ProbeResult("accepted", exc.request_id, exc.platform_code)
    return ProbeResult("accepted", request_id, None)


def format_probe_result(result: ProbeResult) -> str:
    """输出可复制的脱敏结果，禁止加入URL、令牌、响应正文或用户数据。"""

    suffix = f" platform_code={result.platform_code}" if result.platform_code is not None else ""
    return f"status={result.status} request_id={result.request_id}{suffix}"


def _build_client(settings: Settings, request_id: str) -> MolingClient:
    """从现有本地配置构建客户端；缺项只报告键名，不报告敏感值。"""

    required = {
        "MOLING_API_BASE_URL": settings.moling_api_base_url,
        "INTERNAL_API_TOKEN": settings.internal_api_token,
        "MOLING_APP_ID": settings.moling_app_id,
        "MOLING_PRODUCT_ID": settings.moling_product_id,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(",".join(missing))

    return MolingClient(
        base_url=settings.moling_api_base_url,
        internal_api_token=settings.internal_api_token.get_secret_value(),
        app_id=settings.moling_app_id,
        product_id=settings.moling_product_id,
        connect_timeout_seconds=settings.moling_connect_timeout_seconds,
        read_timeout_seconds=settings.moling_read_timeout_seconds,
        request_id_factory=lambda: request_id,
    )


def main() -> int:
    """运行单次预检；返回码可直接用于自动化Gate判断。"""

    repository_root = Path(__file__).resolve().parents[3]
    dotenv.load_dotenv(repository_root / ".env")
    settings = load_settings(os.environ)
    request_id = f"req_t04preflight_{uuid4().hex}"
    try:
        client = _build_client(settings, request_id)
    except ValueError as exc:
        print(f"status=config_error missing={exc}")
        return 5

    result = asyncio.run(probe_internal_auth(client, request_id))
    print(format_probe_result(result))
    return {
        "accepted": 0,
        "rejected": 2,
        "unreachable": 3,
        "protocol_error": 4,
    }[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
