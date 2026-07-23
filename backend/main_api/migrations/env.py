"""Alembic 运行环境：从未跟踪配置读取 URL，并统一使用 PyMySQL。"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import dotenv_values
from sqlalchemy import engine_from_config, pool

from backend.main_api.core.db import DatabaseConnectionError, normalize_database_url


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
repository_root = Path(__file__).resolve().parents[3]


def _database_url() -> str:
    """按测试显式值、环境变量、本地 .env 的顺序读取，异常不回显凭据。"""
    configured = config.get_main_option("sqlalchemy.url").strip()
    raw_url = configured or os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not raw_url:
        raw_url = dotenv_values(repository_root / ".env").get("DATABASE_URL")
    if not raw_url:
        raise DatabaseConnectionError("数据库迁移配置缺失")
    # SQLite 只能由测试 Config.attributes 显式放行，部署环境不能靠 URL 自行切换方言。
    allow_sqlite = bool(config.attributes.get("allow_sqlite", False))
    return normalize_database_url(str(raw_url), allow_sqlite=allow_sqlite)


def run_migrations_offline() -> None:
    """离线生成 SQL 时仍使用脱敏配置入口。"""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线迁移使用 NullPool，避免迁移进程长期持有数据库连接。"""
    section = config.get_section(config.config_ini_section, {})
    # ConfigParser 使用百分号插值，写回前必须转义 URL 中可能存在的百分号。
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
