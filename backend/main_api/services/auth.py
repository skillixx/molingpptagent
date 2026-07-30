"""一次性票据消费与本地Session生命周期服务。"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from ..integrations.moling import LaunchClaims
from ..models.auth import AppSession
from ..repositories.sessions import SessionRepository, hash_session_token


class LaunchTicketVerifier(Protocol):
    """AuthService只依赖verify能力，便于契约测试且不耦合HTTP实现。"""

    async def verify_launch_ticket(self, launch_ticket: str) -> LaunchClaims: ...


@dataclass(frozen=True)
class SessionIssue:
    """新会话签发结果；原始随机值只允许写入响应Cookie。"""

    raw_token: str = field(repr=False)
    expires_at: datetime
    max_age_seconds: int


class AuthService:
    """负责票据单次消费、Session轮换以及绝对/空闲过期判定。"""

    def __init__(
        self,
        *,
        moling_client: LaunchTicketVerifier,
        session_repository: SessionRepository,
        absolute_ttl: timedelta,
        idle_ttl: timedelta,
        token_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        if idle_ttl >= absolute_ttl:
            raise ValueError("Session空闲期限必须小于绝对期限")
        self._moling_client = moling_client
        self._sessions = session_repository
        self._absolute_ttl = absolute_ttl
        self._idle_ttl = idle_ttl
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    async def enter(
        self,
        launch_ticket: str,
        *,
        current_session_token: str | None = None,
    ) -> SessionIssue:
        """调用平台verify恰好一次；只有平台明确成功后才创建本地Session。"""
        claims = await self._moling_client.verify_launch_ticket(launch_ticket)
        issued = self.create_session(claims)
        if current_session_token:
            # 新值落库成功后再撤销本浏览器旧值，避免签发失败导致现有登录意外丢失。
            self.rotate_existing_session(current_session_token)
        return issued

    def create_session(self, claims: LaunchClaims, *, now: datetime | None = None) -> SessionIssue:
        """每次登录生成全新随机ID，以轮换阻断浏览器预置的Session固定攻击。"""
        issued_at = _utc_naive(now or self._now_factory())
        raw_token = self._token_factory()
        expires_at = issued_at + self._absolute_ttl
        self._sessions.add(
            AppSession(
                id=hash_session_token(raw_token),
                user_id=claims.user_id,
                app_id=claims.app_id,
                product_id=claims.product_id,
                entitlement_id=claims.entitlement_id or None,
                created_at=issued_at,
                expires_at=expires_at,
                last_seen_at=issued_at,
                revoked_at=None,
            )
        )
        return SessionIssue(
            raw_token=raw_token,
            expires_at=expires_at.replace(tzinfo=UTC),
            max_age_seconds=int(self._absolute_ttl.total_seconds()),
        )

    def resolve_session(self, raw_token: str, *, now: datetime | None = None) -> AppSession | None:
        """绝对过期、空闲过期或撤销任一成立即fail-closed。"""
        current_time = _utc_naive(now or self._now_factory())
        row = self._sessions.get_by_raw_token(raw_token)
        if row is None or row.revoked_at is not None:
            return None
        if current_time >= row.expires_at or current_time >= row.last_seen_at + self._idle_ttl:
            return None
        self._sessions.touch(row.id, current_time)
        row.last_seen_at = current_time
        return row

    def rotate_existing_session(self, raw_token: str, *, now: datetime | None = None) -> None:
        """撤销当前浏览器携带的旧Session；不按用户批量撤销其他设备。"""
        self._sessions.revoke_by_raw_token(raw_token, _utc_naive(now or self._now_factory()))

    def logout(self, raw_token: str | None, *, now: datetime | None = None) -> None:
        """幂等撤销当前Cookie会话；缺失或已撤销时仍按成功退出处理。"""
        if raw_token:
            self._sessions.revoke_by_raw_token(raw_token, _utc_naive(now or self._now_factory()))


def _utc_naive(value: datetime) -> datetime:
    """数据库统一保存UTC无时区值，API边界再显式附加UTC。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
