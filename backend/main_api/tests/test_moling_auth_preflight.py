"""T04 墨灵内部主闸只读预检测试。"""

from __future__ import annotations

import asyncio

import httpx

from backend.main_api.integrations.moling import MolingClient
from backend.main_api.tools.moling_auth_preflight import (
    ProbeResult,
    format_probe_result,
    probe_internal_auth,
)


REQUEST_ID = "req_t04_preflight_test"


def _client(handler: httpx.MockTransport) -> MolingClient:
    return MolingClient(
        base_url="https://platform.example.com",
        internal_api_token="sensitive-token",
        app_id=9,
        product_id=73,
        connect_timeout_seconds=1.0,
        read_timeout_seconds=1.0,
        transport=handler,
        request_id_factory=lambda: REQUEST_ID,
    )


def test_probe_uses_read_only_entitlement_query_and_accepts_empty_result() -> None:
    """预检不得消费ticket或调用扣费接口，空权益也能证明内部主闸已通过。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/internal/user-entitlements"
        assert request.url.params["user_id"] == "2147483647"
        assert request.url.params["product_id"] == "73"
        return httpx.Response(
            200,
            json={"code": 0, "message": "ok", "data": {"entitlements": []}},
        )

    result = asyncio.run(probe_internal_auth(_client(httpx.MockTransport(handler)), REQUEST_ID))

    assert result == ProbeResult(status="accepted", request_id=REQUEST_ID, platform_code=None)


def test_probe_classifies_http_auth_rejection_without_exposing_response() -> None:
    """401/403只输出稳定分类与request ID，不回显令牌或下游正文。"""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="sensitive gateway details")

    result = asyncio.run(probe_internal_auth(_client(httpx.MockTransport(handler)), REQUEST_ID))
    output = format_probe_result(result)

    assert result.status == "rejected"
    assert output == f"status=rejected request_id={REQUEST_ID}"
    assert "sensitive" not in output
    assert "token" not in output


def test_non_auth_business_rejection_proves_main_gate_was_accepted() -> None:
    """40003以外的业务拒绝发生在主闸之后，应归类为鉴权已通过。"""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"code": 40000, "message": "sentinel user missing", "data": None},
        )

    result = asyncio.run(probe_internal_auth(_client(httpx.MockTransport(handler)), REQUEST_ID))

    assert result == ProbeResult(status="accepted", request_id=REQUEST_ID, platform_code=40000)


def test_unavailable_and_protocol_failures_remain_distinct() -> None:
    """网络不可达与非JSON协议错误不能误报为Token/IP拒绝。"""

    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network detail", request=request)

    def invalid(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    unavailable_result = asyncio.run(
        probe_internal_auth(_client(httpx.MockTransport(unavailable)), REQUEST_ID)
    )
    invalid_result = asyncio.run(probe_internal_auth(_client(httpx.MockTransport(invalid)), REQUEST_ID))

    assert unavailable_result.status == "unreachable"
    assert invalid_result.status == "protocol_error"
