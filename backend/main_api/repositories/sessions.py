"""应用Session仓储，集中执行哈希键查询与撤销。"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from sqlalchemy import Engine, func, inspect, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..models.auth import AppSession


def hash_session_token(raw_token: str) -> str:
    """使用固定SHA-256摘要作为查找键，数据库绝不保存可直接复用的Cookie。"""
    return sha256(raw_token.encode("utf-8")).hexdigest()


class SessionSchemaError(RuntimeError):
    """SSO所需数据库结构缺失或不可检查，消息不得包含连接详情。"""


class SessionRepository:
    """应用Session的最小事务边界；每个公开方法独立提交或回滚。"""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def add(self, app_session: AppSession) -> None:
        """持久化已由服务层构造且仅含哈希ID的会话。"""
        with self._session_factory.begin() as db:
            db.add(app_session)

    def ensure_schema(self) -> None:
        """服务监听前检查迁移结果，但绝不在应用启动时自动建表。"""
        expected_columns = {
            "id",
            "user_id",
            "app_id",
            "product_id",
            "entitlement_id",
            "created_at",
            "expires_at",
            "last_seen_at",
            "revoked_at",
        }
        try:
            inspector = inspect(self.engine)
            if "app_sessions" not in inspector.get_table_names():
                raise SessionSchemaError("Session数据库结构未就绪")
            actual_columns = {column["name"] for column in inspector.get_columns("app_sessions")}
            if not expected_columns.issubset(actual_columns):
                raise SessionSchemaError("Session数据库结构未就绪")
        except SessionSchemaError:
            raise
        except SQLAlchemyError:
            raise SessionSchemaError("Session数据库结构未就绪") from None

    def get_by_raw_token(self, raw_token: str) -> AppSession | None:
        """对原始Cookie做单向摘要后查询，不把原值写入SQL或日志。"""
        with self._session_factory() as db:
            return db.get(AppSession, hash_session_token(raw_token))

    def touch(self, app_session_id: str, last_seen_at: datetime) -> None:
        """以单条条件更新刷新活动时间，乱序并发不得让时间倒退。"""
        with self._session_factory.begin() as db:
            db.execute(
                update(AppSession)
                .where(
                    AppSession.id == app_session_id,
                    AppSession.revoked_at.is_(None),
                    AppSession.last_seen_at < last_seen_at,
                )
                .values(last_seen_at=last_seen_at)
            )

    def revoke_by_raw_token(self, raw_token: str, revoked_at: datetime) -> None:
        """只撤销Cookie对应的一条会话，保留同一用户其他设备登录。"""
        with self._session_factory.begin() as db:
            db.execute(
                update(AppSession)
                .where(
                    AppSession.id == hash_session_token(raw_token),
                    AppSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )

    def count(self) -> int:
        """仅供隔离测试和运维检查使用。"""
        with self._session_factory() as db:
            return int(db.scalar(select(func.count()).select_from(AppSession)) or 0)
