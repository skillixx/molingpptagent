"""墨灵平台内部接口客户端与稳定错误模型。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Annotated, Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator


# 平台金额以非负decimal字符串传输，最多六位小数；严格模式禁止JSON数字被隐式转型。
DecimalString = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^(?:0|[1-9]\d*)(?:\.\d{1,6})?$"),
]


class MolingError(RuntimeError):
    """墨灵调用错误基类；消息固定且不包含下游正文、票据或令牌。"""

    def __init__(
        self,
        message: str,
        *,
        request_id: str,
        retryable: bool,
        platform_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.retryable = retryable
        self.platform_code = platform_code


class MolingAuthenticationError(MolingError):
    """内部令牌、IP白名单或一次性票据校验失败。"""


class MolingBusinessError(MolingError):
    """平台已明确返回的业务失败，例如额度不足或参数错误。"""


class MolingProtocolError(MolingError):
    """平台响应不满足已冻结的统一信封或字段契约。"""


class MolingIdentityMismatchError(MolingProtocolError):
    """verify 返回了不属于当前应用或商品的身份。"""


class MolingUnavailableError(MolingError):
    """网络、超时或平台5xx导致调用终态未知。"""


class LaunchClaims(BaseModel):
    """一次性票据消费成功后可用于建立本地会话的最小身份声明。"""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    # 从具体资产进入应用时，墨灵会把该资产对应权益写入一次性票据；0 表示旧入口未指定。
    entitlement_id: int = Field(default=0, ge=0)
    request_id: str


class EntitlementBalance(BaseModel):
    """墨灵预付权益快照；金额保持decimal字符串，null表示不限量。"""

    model_config = ConfigDict(frozen=True, extra="ignore")

    entitlement_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    quota_total: DecimalString | None = None
    quota_used: DecimalString
    quota_reserved: DecimalString
    remaining: DecimalString | None = None
    status: str
    expires_at: datetime | None = None
    usable: bool


class _BillingWriteResult(BaseModel):
    """额度写响应公共字段；平台 Go 契约要求 hold ID 保持正整数。"""

    model_config = ConfigDict(frozen=True, extra="ignore")

    hold_id: int = Field(gt=0, le=9_223_372_036_854_775_807)

    @field_validator("hold_id", mode="before")
    @classmethod
    def normalize_hold_id(cls, value: object) -> int:
        if type(value) is int and 0 < value <= 9_223_372_036_854_775_807:
            return value
        raise ValueError("invalid hold id")


class EntitlementReservation(_BillingWriteResult):
    """平台原子预占成功结果。"""

    reserved: DecimalString
    available: DecimalString | None = None
    status: Literal["holding"]


class EntitlementFinalization(_BillingWriteResult):
    """平台结算或释放成功结果；调用方法还会核对对应动作状态。"""

    status: Literal["settled", "released"]
    settled_amount: DecimalString
    quota_used: DecimalString
    quota_reserved: DecimalString
    available: DecimalString | None = None


class MolingClient:
    """集中封装墨灵内部HTTP契约，业务层不得自行拼接URL或鉴权头。"""

    def __init__(
        self,
        *,
        base_url: str,
        internal_api_token: str,
        app_id: int,
        product_id: int,
        connect_timeout_seconds: float = 3.0,
        read_timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_api_token = internal_api_token
        self._app_id = app_id
        self._product_id = product_id
        self._timeout = httpx.Timeout(
            connect=connect_timeout_seconds,
            read=read_timeout_seconds,
            write=read_timeout_seconds,
            pool=connect_timeout_seconds,
        )
        self._transport = transport
        self._request_id_factory = request_id_factory or (lambda: f"req_{uuid4().hex}")

    async def verify_launch_ticket(self, launch_ticket: str) -> LaunchClaims:
        """消费一次性票据；终态未知时绝不在客户端内部自动重放。"""
        request_id, data = await self._request(
            "POST",
            "/api/internal/app-launch/verify",
            json={"launch_ticket": launch_ticket},
        )
        try:
            claims = LaunchClaims.model_validate({**data, "request_id": request_id})
        except ValidationError:
            # Pydantic错误会携带原始输入，禁止通过异常链进入traceback日志。
            raise self._protocol_error(request_id) from None
        if claims.app_id != self._app_id or claims.product_id != self._product_id:
            raise MolingIdentityMismatchError(
                "墨灵身份与当前应用配置不匹配",
                request_id=request_id,
                retryable=False,
            )
        return claims

    async def list_user_entitlements(
        self,
        *,
        user_id: int,
        product_id: int | None = None,
    ) -> tuple[EntitlementBalance, ...]:
        """查询用户在指定商品下的权益；选择策略由后续计费服务负责。"""
        if product_id is not None and product_id != self._product_id:
            # 商品作用域来自可信启动配置，业务调用方不能借可选参数跨商品查询。
            raise MolingIdentityMismatchError(
                "墨灵权益商品与当前配置不匹配",
                request_id=self._request_id_factory(),
                retryable=False,
            )
        request_id, data = await self._request(
            "GET",
            "/api/internal/user-entitlements",
            params={"user_id": user_id, "product_id": product_id or self._product_id},
        )
        raw_items = data.get("entitlements")
        if not isinstance(raw_items, list):
            raise self._protocol_error(request_id)
        try:
            entitlements = tuple(EntitlementBalance.model_validate(item) for item in raw_items)
        except ValidationError:
            raise self._protocol_error(request_id) from None
        if any(item.user_id != user_id for item in entitlements):
            raise self._protocol_error(request_id)
        return entitlements

    async def get_entitlement_balance(
        self,
        *,
        entitlement_id: int,
        user_id: int,
    ) -> EntitlementBalance:
        """只读查询可用额度；最终是否可扣仍以平台原子扣减接口为准。"""
        request_id, data = await self._request(
            "GET",
            "/api/internal/entitlement-balance",
            params={"entitlement_id": entitlement_id, "user_id": user_id},
        )
        try:
            balance = EntitlementBalance.model_validate(data)
        except ValidationError:
            raise self._protocol_error(request_id) from None
        if balance.user_id != user_id or balance.entitlement_id != entitlement_id:
            raise self._protocol_error(request_id)
        return balance

    async def reserve_entitlement(
        self,
        *,
        entitlement_id: int,
        user_id: int,
        amount: str,
        idempotency_key: str,
    ) -> EntitlementReservation:
        """原子预占额度；客户端不在终态未知时自动重放。"""
        self._validate_write_input(amount, idempotency_key, positive=True)
        request_id, data = await self._request(
            "POST",
            "/api/internal/entitlement-reserve",
            json={
                "entitlement_id": entitlement_id,
                "user_id": user_id,
                "amount": amount,
                "idempotency_key": idempotency_key,
            },
        )
        try:
            result = EntitlementReservation.model_validate(data)
        except ValidationError:
            raise self._protocol_error(request_id) from None
        if Decimal(result.reserved) != Decimal(amount):
            raise self._protocol_error(request_id)
        return result

    async def settle_entitlement(
        self,
        *,
        hold_id: int,
        actual_amount: str,
        idempotency_key: str,
    ) -> EntitlementFinalization:
        """按已确认实际额结算；hold与动作幂等键同时发送，便于平台去重。"""
        self._validate_write_input(actual_amount, idempotency_key, positive=False)
        self._validate_hold_id(hold_id)
        request_id, data = await self._request(
            "POST",
            "/api/internal/entitlement-settle",
            json={
                "hold_id": hold_id,
                "actual_amount": actual_amount,
                "idempotency_key": idempotency_key,
            },
        )
        try:
            result = EntitlementFinalization.model_validate(data)
        except ValidationError:
            raise self._protocol_error(request_id) from None
        if (
            result.status != "settled"
            or result.hold_id != hold_id
            or Decimal(result.settled_amount) != Decimal(actual_amount)
        ):
            raise self._protocol_error(request_id)
        return result

    async def release_entitlement(
        self,
        *,
        hold_id: int,
        idempotency_key: str,
    ) -> EntitlementFinalization:
        """明确失败时释放预占；释放成功必须证明本次结算额为零。"""
        self._validate_write_input("0", idempotency_key, positive=False)
        self._validate_hold_id(hold_id)
        request_id, data = await self._request(
            "POST",
            "/api/internal/entitlement-release",
            json={"hold_id": hold_id, "idempotency_key": idempotency_key},
        )
        try:
            result = EntitlementFinalization.model_validate(data)
        except ValidationError:
            raise self._protocol_error(request_id) from None
        if (
            result.status != "released"
            or result.hold_id != hold_id
            or Decimal(result.settled_amount) != 0
        ):
            raise self._protocol_error(request_id)
        return result

    @staticmethod
    def _validate_write_input(amount: str, idempotency_key: str, *, positive: bool) -> None:
        """写接口仅接受可精确传输的decimal字符串和受限稳定幂等键。"""
        try:
            parsed = Decimal(amount)
        except (InvalidOperation, TypeError):
            raise ValueError("计费金额无效") from None
        if (
            not isinstance(amount, str)
            or not re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d{1,6})?", amount)
            or (positive and parsed <= 0)
            or parsed < 0
        ):
            raise ValueError("计费金额无效")
        if not isinstance(idempotency_key, str) or not re.fullmatch(
            r"[A-Za-z0-9._:-]{1,128}", idempotency_key
        ):
            raise ValueError("计费幂等键无效")

    @staticmethod
    def _validate_hold_id(hold_id: int) -> None:
        # bool 是 int 的子类，必须用精确类型判断阻止 True 被当成持有单 1。
        if type(hold_id) is not int or not 0 < hold_id <= 9_223_372_036_854_775_807:
            raise ValueError("计费预占标识无效")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """执行一次请求并解析统一信封；不记录敏感请求体和下游原始响应。"""
        request_id = self._request_id_factory()
        headers = {
            "X-Internal-Token": self._internal_api_token,
            "X-Request-Id": request_id,
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.RequestError:
            raise MolingUnavailableError(
                "墨灵平台暂时不可用",
                request_id=request_id,
                retryable=True,
            ) from None

        if response.status_code >= 500:
            raise MolingUnavailableError(
                "墨灵平台暂时不可用",
                request_id=request_id,
                retryable=True,
            )
        if response.status_code in (401, 403):
            # 网关或IP白名单可能返回HTML，鉴权HTTP状态不依赖响应体也必须稳定分类。
            raise MolingAuthenticationError(
                "墨灵身份或内部鉴权失败",
                request_id=request_id,
                retryable=False,
            )

        envelope = self._parse_envelope(response, request_id)
        code = envelope["code"]
        if code == 40003:
            raise MolingAuthenticationError(
                "墨灵身份或内部鉴权失败",
                request_id=request_id,
                retryable=False,
                platform_code=code,
            )
        if response.status_code >= 400 or code != 0:
            raise MolingBusinessError(
                "墨灵平台拒绝了本次业务请求",
                request_id=request_id,
                retryable=False,
                platform_code=code,
            )

        data = envelope.get("data")
        if not isinstance(data, dict):
            raise self._protocol_error(request_id)
        return request_id, data

    def _parse_envelope(self, response: httpx.Response, request_id: str) -> dict[str, Any]:
        """严格检查统一响应信封，避免把HTML错误页或残缺JSON当成业务成功。"""
        try:
            envelope = response.json()
        except ValueError:
            # JSON异常可能包含下游正文位置，不向上保留原始异常上下文。
            raise self._protocol_error(request_id) from None
        if (
            not isinstance(envelope, dict)
            or type(envelope.get("code")) is not int
            or not isinstance(envelope.get("message"), str)
            or "data" not in envelope
        ):
            raise self._protocol_error(request_id)
        return envelope

    @staticmethod
    def _protocol_error(request_id: str) -> MolingProtocolError:
        """构造不含平台原始正文的稳定协议错误。"""
        return MolingProtocolError(
            "墨灵平台响应不符合约定",
            request_id=request_id,
            retryable=False,
        )
