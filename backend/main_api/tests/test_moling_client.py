"""T03 墨灵内部接口客户端的公开契约测试。"""

from __future__ import annotations

import asyncio
import traceback

import httpx
import pytest

from backend.main_api.integrations.moling import (
    EntitlementFinalization,
    EntitlementReservation,
    MolingAuthenticationError,
    MolingBusinessError,
    MolingClient,
    MolingIdentityMismatchError,
    MolingProtocolError,
    MolingUnavailableError,
)


def _run(coroutine):
    """当前仓库未引入异步测试插件，使用标准事件循环执行客户端协程。"""
    return asyncio.run(coroutine)


def _client(handler, *, request_id_factory=lambda: "req_test_123") -> MolingClient:
    """用 MockTransport 冻结 HTTP 契约，不接触真实票据或共享密钥。"""
    transport = httpx.MockTransport(handler)
    return MolingClient(
        base_url="https://moling.example.test",
        internal_api_token="test-internal-token",
        app_id=15,
        product_id=73,
        transport=transport,
        request_id_factory=request_id_factory,
    )


def test_verify_ticket_sends_internal_auth_and_returns_matching_claims() -> None:
    """verify 必须由服务端发送内部令牌和请求ID，并校验应用/商品归属。"""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/internal/app-launch/verify"
        assert request.headers["X-Internal-Token"] == "test-internal-token"
        assert request.headers["X-Request-Id"] == "req_test_123"
        assert request.read() == b'{"launch_ticket":"lt_one_time"}'
        return httpx.Response(
            200,
            json={"code": 0, "message": "ok", "data": {"user_id": 9, "app_id": 15, "product_id": 73}},
        )

    claims = _run(_client(handler).verify_launch_ticket("lt_one_time"))

    assert claims.user_id == 9
    assert claims.app_id == 15
    assert claims.product_id == 73
    assert claims.request_id == "req_test_123"


@pytest.mark.parametrize("status_code", [401, 403])
def test_http_authentication_failures_map_to_stable_error(status_code: int) -> None:
    """HTTP鉴权失败统一映射，且异常不得回显一次性票据或内部令牌。"""
    secret_ticket = "lt_sensitive_ticket"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"code": 40003, "message": "forbidden"})

    with pytest.raises(MolingAuthenticationError) as exc_info:
        _run(_client(handler).verify_launch_ticket(secret_ticket))

    message = str(exc_info.value)
    assert exc_info.value.request_id == "req_test_123"
    assert exc_info.value.retryable is False
    assert secret_ticket not in message
    assert "test-internal-token" not in message


def test_http_authentication_failure_maps_even_when_body_is_not_json() -> None:
    """IP白名单或网关可能返回HTML，HTTP 401/403仍应稳定归为鉴权失败。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="<html>forbidden</html>")

    with pytest.raises(MolingAuthenticationError) as exc_info:
        _run(_client(handler).verify_launch_ticket("lt_hidden"))

    assert exc_info.value.platform_code is None
    assert "forbidden" not in str(exc_info.value)


def test_platform_authentication_code_maps_even_with_http_200() -> None:
    """平台统一信封可能用HTTP 200承载业务失败，code=40003仍必须拒绝。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 40003, "message": "ticket expired", "data": None})

    with pytest.raises(MolingAuthenticationError) as exc_info:
        _run(_client(handler).verify_launch_ticket("lt_expired"))

    assert exc_info.value.platform_code == 40003
    assert exc_info.value.retryable is False


def test_platform_business_error_preserves_code_without_leaking_payload() -> None:
    """额度等平台业务码保持稳定分类，但不把任意下游正文直接暴露给调用方。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 60005, "message": "quota secret detail", "data": None})

    with pytest.raises(MolingBusinessError) as exc_info:
        _run(_client(handler).get_entitlement_balance(entitlement_id=8, user_id=9))

    assert exc_info.value.platform_code == 60005
    assert "quota secret detail" not in str(exc_info.value)


def test_timeout_maps_to_retryable_unavailable_without_automatic_retry() -> None:
    """verify消费终态不明时只返回可重试分类，不自动重放同一张一次性票据。"""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("contains-sensitive-url", request=request)

    with pytest.raises(MolingUnavailableError) as exc_info:
        _run(_client(handler).verify_launch_ticket("lt_do_not_retry"))

    assert calls == 1
    assert exc_info.value.retryable is True
    assert "contains-sensitive-url" not in str(exc_info.value)
    rendered_traceback = "".join(traceback.format_exception(exc_info.value))
    assert "contains-sensitive-url" not in rendered_traceback


def test_transport_protocol_failure_maps_without_leaking_detail() -> None:
    """连接被网关异常中断时也必须进入可重试不可用分类。"""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError("sensitive upstream detail")

    with pytest.raises(MolingUnavailableError) as exc_info:
        _run(_client(handler).list_user_entitlements(user_id=9))

    assert exc_info.value.retryable is True
    assert "sensitive upstream detail" not in str(exc_info.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json={"code": 0, "message": "ok", "data": {"app_id": 15, "product_id": 73}}),
        httpx.Response(200, json={"message": "ok", "data": {}}),
        httpx.Response(200, json={"code": 0, "data": {"user_id": 9, "app_id": 15, "product_id": 73}}),
    ],
)
def test_non_json_or_missing_fields_are_protocol_errors(response: httpx.Response) -> None:
    """非JSON、信封缺字段或身份字段缺失都不能被当成成功。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    with pytest.raises(MolingProtocolError) as exc_info:
        _run(_client(handler).verify_launch_ticket("lt_invalid_response"))

    assert exc_info.value.retryable is False


def test_protocol_validation_traceback_does_not_include_downstream_payload() -> None:
    """即使调用方记录完整traceback，也不得带出下游响应中的任意敏感字段。"""
    sensitive_marker = "downstream-sensitive-marker"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "ok",
                "data": {"app_id": 15, "product_id": 73, "detail": sensitive_marker},
            },
        )

    with pytest.raises(MolingProtocolError) as exc_info:
        _run(_client(handler).verify_launch_ticket("lt_invalid"))

    assert sensitive_marker not in "".join(traceback.format_exception(exc_info.value))


@pytest.mark.parametrize(
    "data",
    [
        {"user_id": 9, "app_id": 16, "product_id": 73},
        {"user_id": 9, "app_id": 15, "product_id": 74},
    ],
)
def test_app_or_product_mismatch_is_rejected(data: dict[str, int]) -> None:
    """平台返回的身份必须与本应用配置一致，禁止跨应用或跨商品建立会话。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "message": "ok", "data": data})

    with pytest.raises(MolingIdentityMismatchError):
        _run(_client(handler).verify_launch_ticket("lt_wrong_scope"))


def test_entitlement_list_and_balance_allow_unlimited_null_values() -> None:
    """权益查询保留Decimal字符串和不限量null语义，禁止用float改写金额。"""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("user-entitlements"):
            assert dict(request.url.params) == {"user_id": "9", "product_id": "73"}
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "entitlements": [
                            {
                                "entitlement_id": 8,
                                "user_id": 9,
                                "quota_total": None,
                                "quota_used": "1.250000",
                                "quota_reserved": "0.500000",
                                "remaining": None,
                                "status": "active",
                                "expires_at": None,
                                "usable": True,
                            }
                        ]
                    },
                },
            )
        assert request.url.path.endswith("entitlement-balance")
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "ok",
                "data": {
                    "entitlement_id": 8,
                    "user_id": 9,
                    "quota_total": None,
                    "quota_used": "1.250000",
                    "quota_reserved": "0.500000",
                    "remaining": None,
                    "status": "active",
                    "expires_at": None,
                    "usable": True,
                },
            },
        )

    client = _client(handler)
    entitlements = _run(client.list_user_entitlements(user_id=9, product_id=73))
    balance = _run(client.get_entitlement_balance(entitlement_id=8, user_id=9))

    assert len(entitlements) == 1
    assert entitlements[0].quota_used == "1.250000"
    assert entitlements[0].quota_total is None
    assert balance.remaining is None
    assert balance.usable is True


@pytest.mark.parametrize(
    ("path", "data"),
    [
        (
            "user-entitlements",
            {"entitlements": [{
                "entitlement_id": 8, "user_id": 10, "quota_total": "10",
                "quota_used": "0", "quota_reserved": "0", "remaining": "10",
                "status": "active", "expires_at": None, "usable": True,
            }]},
        ),
        (
            "entitlement-balance",
            {
                "entitlement_id": 99, "user_id": 9, "quota_total": "10",
                "quota_used": "0", "quota_reserved": "0", "remaining": "10",
                "status": "active", "expires_at": None, "usable": True,
            },
        ),
    ],
)
def test_entitlement_responses_cannot_cross_requested_scope(path: str, data: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(path)
        return httpx.Response(200, json={"code": 0, "message": "ok", "data": data})

    client = _client(handler)
    with pytest.raises(MolingProtocolError):
        if path == "user-entitlements":
            _run(client.list_user_entitlements(user_id=9))
        else:
            _run(client.get_entitlement_balance(entitlement_id=8, user_id=9))


def test_entitlement_query_cannot_override_configured_product() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    with pytest.raises(MolingIdentityMismatchError):
        _run(_client(handler).list_user_entitlements(user_id=9, product_id=74))
    assert called is False


@pytest.mark.parametrize("invalid_amount", ["abc", "NaN", "Infinity", "-1", "1.0000001", 1.25])
def test_invalid_decimal_amount_is_a_protocol_error(invalid_amount: object) -> None:
    """额度只接受非负、最多六位小数的字符串，JSON数字也不得被隐式转型。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "ok",
                "data": {
                    "entitlement_id": 8,
                    "user_id": 9,
                    "quota_total": "10",
                    "quota_used": invalid_amount,
                    "quota_reserved": "0",
                    "remaining": "8.75",
                    "status": "active",
                    "expires_at": None,
                    "usable": True,
                },
            },
        )

    with pytest.raises(MolingProtocolError):
        _run(_client(handler).get_entitlement_balance(entitlement_id=8, user_id=9))


def test_reserve_settle_and_release_use_distinct_idempotency_contracts() -> None:
    """三种额度写动作必须发送decimal字符串和各自幂等键，不能复用动作语义。"""
    requests: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.read())
        requests.append((request.url.path, payload))
        assert request.headers["X-Internal-Token"] == "test-internal-token"
        if request.url.path.endswith("entitlement-reserve"):
            return httpx.Response(200, json={"code": 0, "message": "ok", "data": {
                "hold_id": 51, "reserved": "10", "available": "90", "status": "holding",
            }})
        if request.url.path.endswith("entitlement-settle"):
            return httpx.Response(200, json={"code": 0, "message": "ok", "data": {
                "hold_id": 51, "status": "settled", "settled_amount": "8",
                # 其他并发hold可以让权益总预占非零，本次hold仍已由settled状态证明关闭。
                "quota_used": "8", "quota_reserved": "2", "available": "90",
            }})
        return httpx.Response(200, json={"code": 0, "message": "ok", "data": {
            "hold_id": 51, "status": "released", "settled_amount": "0",
            "quota_used": "0", "quota_reserved": "2", "available": "98",
        }})

    client = _client(handler)
    reserved = _run(client.reserve_entitlement(
        entitlement_id=8, user_id=9, amount="10", idempotency_key="ppt:t1:reserve"
    ))
    settled = _run(client.settle_entitlement(
        hold_id="51", actual_amount="8", idempotency_key="ppt:t1:settle"
    ))
    released = _run(client.release_entitlement(
        hold_id="51", idempotency_key="ppt:t1:release"
    ))

    assert isinstance(reserved, EntitlementReservation) and reserved.hold_id == "51"
    assert isinstance(settled, EntitlementFinalization) and settled.status == "settled"
    assert released.status == "released"
    assert requests == [
        ("/api/internal/entitlement-reserve", {
            "entitlement_id": 8, "user_id": 9, "amount": "10",
            "idempotency_key": "ppt:t1:reserve",
        }),
        ("/api/internal/entitlement-settle", {
            "hold_id": "51", "actual_amount": "8", "idempotency_key": "ppt:t1:settle",
        }),
        ("/api/internal/entitlement-release", {
            "hold_id": "51", "idempotency_key": "ppt:t1:release",
        }),
    ]


@pytest.mark.parametrize(
    ("action", "data"),
    [
        ("reserve", {"hold_id": 51, "reserved": "10", "available": "90", "status": "wrong"}),
        ("settle", {"hold_id": 51, "settled_amount": "8", "quota_used": "8", "quota_reserved": "0", "available": "92", "status": "wrong"}),
        ("settle", {"hold_id": 99, "settled_amount": "8", "quota_used": "8", "quota_reserved": "0", "available": "92", "status": "settled"}),
        ("release", {"hold_id": 51, "settled_amount": "1", "quota_used": "1", "quota_reserved": "0", "available": "99", "status": "released"}),
        ("release", {"hold_id": 99, "settled_amount": "0", "quota_used": "0", "quota_reserved": "0", "available": "100", "status": "released"}),
    ],
)
def test_billing_write_response_requires_expected_terminal_fields(action: str, data: dict) -> None:
    """平台200但状态或释放金额不符合契约时，终态不能被本地猜成成功。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "message": "ok", "data": data})

    client = _client(handler)
    with pytest.raises(MolingProtocolError):
        if action == "reserve":
            _run(client.reserve_entitlement(
                entitlement_id=8, user_id=9, amount="10", idempotency_key="ppt:t1:reserve"
            ))
        elif action == "settle":
            _run(client.settle_entitlement(
                hold_id="51", actual_amount="8", idempotency_key="ppt:t1:settle"
            ))
        else:
            _run(client.release_entitlement(
                hold_id="51", idempotency_key="ppt:t1:release"
            ))
