"""SQLAlchemy 连接工厂与数据库兼容性检查。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError


class DatabaseConnectionError(RuntimeError):
    """数据库连接失败的稳定错误，禁止携带底层连接串或凭据。"""


@dataclass(frozen=True)
class DatabaseBaseline:
    """只读采集的 MySQL 能力基线，不包含主机、账号等部署信息。"""

    version: str
    major_version: int
    supports_skip_locked: bool


def normalize_database_url(database_url: str, *, allow_sqlite: bool = False) -> str:
    """生产只允许 MySQL+PyMySQL；SQLite 仅供显式隔离测试。"""
    try:
        parsed = make_url(database_url)
    except Exception:
        # 不把 SQLAlchemy 的解析错误向上透传，部分异常可能包含原始 URL。
        raise DatabaseConnectionError("数据库连接配置无效") from None
    backend_name = parsed.get_backend_name()
    if backend_name != "mysql" and not (allow_sqlite and backend_name == "sqlite"):
        raise DatabaseConnectionError("数据库类型不受支持")
    if backend_name == "mysql" and parsed.drivername != "mysql+pymysql":
        parsed = parsed.set(drivername="mysql+pymysql")
    return parsed.render_as_string(hide_password=False)


def _engine_options(url: URL, connect_timeout_seconds: int) -> dict[str, object]:
    """根据方言生成连接参数，测试 SQLite 与生产 MySQL 使用同一工厂。"""
    options: dict[str, object] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if url.get_backend_name() == "mysql":
        options["connect_args"] = {"connect_timeout": connect_timeout_seconds}
    return options


def create_database_engine(
    database_url: str,
    *,
    connect_timeout_seconds: int = 5,
    allow_sqlite: bool = False,
) -> Engine:
    """创建延迟连接的 Engine；失败错误始终脱敏。"""
    try:
        normalized = normalize_database_url(database_url, allow_sqlite=allow_sqlite)
        parsed = make_url(normalized)
        return create_engine(normalized, **_engine_options(parsed, connect_timeout_seconds))
    except DatabaseConnectionError:
        raise
    except Exception:
        raise DatabaseConnectionError("数据库连接配置无效") from None


def create_verified_database_engine(
    database_url: str,
    *,
    connect_timeout_seconds: int = 5,
    allow_sqlite: bool = False,
) -> Engine:
    """验证最小只读连接并返回 Engine；调用方使用完必须执行 dispose()。"""
    engine = create_database_engine(
        database_url,
        connect_timeout_seconds=connect_timeout_seconds,
        allow_sqlite=allow_sqlite,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        engine.dispose()
        raise DatabaseConnectionError("数据库连接失败") from None
    return engine


def inspect_mysql_baseline(engine: Engine) -> DatabaseBaseline:
    """读取 MySQL 版本并判断租约 Worker 能否使用 SKIP LOCKED。"""
    try:
        with engine.connect() as connection:
            version = str(connection.execute(text("SELECT VERSION()")).scalar_one())
    except SQLAlchemyError:
        raise DatabaseConnectionError("数据库基线检查失败") from None

    try:
        major_version = int(version.split(".", 1)[0])
    except (TypeError, ValueError):
        major_version = 0
    # MySQL 8 支持 SKIP LOCKED；MariaDB 方言差异较大，首版走原子条件更新回退。
    supports_skip_locked = major_version >= 8 and "mariadb" not in version.lower()
    return DatabaseBaseline(
        version=version,
        major_version=major_version,
        supports_skip_locked=supports_skip_locked,
    )
