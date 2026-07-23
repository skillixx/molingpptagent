"""T02 数据库连接与 Alembic 基线的公开行为测试。"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.main_api.core.db import (
    DatabaseConnectionError,
    create_verified_database_engine,
    normalize_database_url,
)
from backend.main_api.repositories.resources import PresentationRepository, PresentationSchemaError


def test_legacy_mysql_url_uses_pure_python_driver() -> None:
    """旧环境的 mysql:// 契约必须稳定切换到纯 Python PyMySQL 驱动。"""
    normalized = normalize_database_url("mysql://user:password@db.example.com/trainppt")

    assert normalized.startswith("mysql+pymysql://")


def test_non_mysql_database_requires_explicit_test_override() -> None:
    """生产连接层只接受 MySQL；SQLite 只能由隔离迁移测试显式放行。"""
    with pytest.raises(DatabaseConnectionError):
        normalize_database_url("sqlite:///local.db")

    assert normalize_database_url("sqlite:///local.db", allow_sqlite=True).startswith("sqlite:///")


def test_connection_failure_does_not_leak_credentials() -> None:
    """数据库连接失败只能返回稳定中文错误，禁止透传账号、密码或完整 URL。"""
    database_url = "mysql+pymysql://secret_user:secret_password@127.0.0.1:1/trainppt"

    with pytest.raises(DatabaseConnectionError) as exc_info:
        create_verified_database_engine(database_url, connect_timeout_seconds=1)

    message = str(exc_info.value)
    assert message == "数据库连接失败"
    assert "secret_user" not in message
    assert "secret_password" not in message
    assert database_url not in message


def _alembic_config(database_url: str):
    """构造隔离的迁移配置，测试不读取开发者本地数据库凭据。"""
    from alembic.config import Config

    repository_root = Path(__file__).resolve().parents[3]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "backend/main_api/migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["allow_sqlite"] = database_url.startswith("sqlite:")
    return config


def test_empty_database_upgrade_is_repeatable(tmp_path: Path) -> None:
    """空库升级到 head 后再次升级必须幂等，并留下唯一迁移版本记录。"""
    from alembic import command

    database_path = tmp_path / "repeatable.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            versions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        assert len(versions) == 1
    finally:
        # Windows 会持有 SQLite 文件句柄，测试结束前必须主动释放连接池。
        engine.dispose()


def test_upgrade_preserves_legacy_tables_with_colliding_generic_names(tmp_path: Path) -> None:
    """新业务表必须使用独立命名空间，不能覆盖墨灵库中的旧 files/tasks 表。"""
    from alembic import command

    database_url = f"sqlite:///{(tmp_path / 'legacy-collision.db').as_posix()}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE files (id TEXT PRIMARY KEY, data TEXT)"))
            connection.execute(text("CREATE TABLE generation_tasks (id TEXT PRIMARY KEY, data TEXT)"))
            connection.execute(text("INSERT INTO files VALUES ('legacy-file', 'keep')"))
            connection.execute(text("INSERT INTO generation_tasks VALUES ('legacy-task', 'keep')"))

        command.upgrade(_alembic_config(database_url), "head")

        tables = set(inspect(engine).get_table_names())
        assert {"files", "generation_tasks", "trainppt_files", "trainppt_generation_tasks"} <= tables
        with engine.connect() as connection:
            assert connection.execute(text("SELECT data FROM files WHERE id='legacy-file'")).scalar_one() == "keep"
            assert connection.execute(
                text("SELECT data FROM generation_tasks WHERE id='legacy-task'")
            ).scalar_one() == "keep"
    finally:
        engine.dispose()


def test_core_resource_migration_creates_owner_and_lease_indexes(tmp_path: Path) -> None:
    """从空库执行真实 Alembic 链后检查 T06 表、唯一约束和领取索引。"""
    from alembic import command

    database_path = tmp_path / "t06-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    try:
        schema = inspect(engine)
        assert {
            "trainppt_presentations",
            "trainppt_presentation_versions",
            "trainppt_generation_tasks",
            "trainppt_billing_operations",
            "trainppt_files",
            "trainppt_exports",
        }.issubset(schema.get_table_names())
        assert "ix_generation_tasks_claim" in {
            index["name"] for index in schema.get_indexes("trainppt_generation_tasks")
        }
        assert "ix_generation_tasks_recovery" in {
            index["name"] for index in schema.get_indexes("trainppt_generation_tasks")
        }
        assert "dispatch_started_at" in {
            column["name"] for column in schema.get_columns("trainppt_generation_tasks")
        }
        assert "ix_presentations_owner_deleted_updated" in {
            index["name"] for index in schema.get_indexes("trainppt_presentations")
        }
        task_uniques = {constraint["name"] for constraint in schema.get_unique_constraints("trainppt_generation_tasks")}
        version_uniques = {
            constraint["name"] for constraint in schema.get_unique_constraints("trainppt_presentation_versions")
        }
        assert "uq_generation_tasks_owner_request" in task_uniques
        assert "uq_presentation_versions_presentation_version" in version_uniques
    finally:
        engine.dispose()


def test_t16_idempotency_migration_preserves_rows_and_allows_same_key_for_other_owner(
    tmp_path: Path,
) -> None:
    """0005必须保留既有任务，并只放宽跨用户同键，不能放宽同用户重复。"""
    from alembic import command

    database_path = tmp_path / "t16-idempotency.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)
    command.upgrade(config, "20260723_0004")
    engine = create_engine(database_url)
    try:
        with pytest.raises(PresentationSchemaError):
            PresentationRepository(engine).ensure_schema()
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO trainppt_presentations "
                "(id, owner_user_id, title, status, slides_json, created_at, updated_at) "
                "VALUES ('p1', 1001, '原作品', 'generating', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO trainppt_generation_tasks "
                "(id, presentation_id, owner_user_id, request_id, status, stage, input_json, "
                "next_attempt_at, created_at, updated_at) "
                "VALUES ('t1', 'p1', 1001, 'shared-client-key', 'pending', 'queued', '{}', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
        engine.dispose()

        command.upgrade(config, "head")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            assert connection.execute(
                text("SELECT owner_user_id FROM trainppt_generation_tasks WHERE id='t1'")
            ).scalar_one() == 1001
            connection.execute(text(
                "INSERT INTO trainppt_presentations "
                "(id, owner_user_id, title, status, slides_json, created_at, updated_at) "
                "VALUES ('p2', 2002, '另一用户作品', 'generating', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO trainppt_generation_tasks "
                "(id, presentation_id, owner_user_id, request_id, status, stage, input_json, "
                "next_attempt_at, created_at, updated_at) "
                "VALUES ('t2', 'p2', 2002, 'shared-client-key', 'pending', 'queued', '{}', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            with pytest.raises(IntegrityError):
                connection.execute(text(
                    "INSERT INTO trainppt_generation_tasks "
                    "(id, presentation_id, owner_user_id, request_id, status, stage, input_json, "
                    "next_attempt_at, created_at, updated_at) "
                    "VALUES ('t3', 'p1', 1001, 'shared-client-key', 'pending', 'queued', '{}', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ))
    finally:
        engine.dispose()


def test_mysql_offline_core_migration_uses_longtext_and_owner_indexes() -> None:
    """生产方言 SQL 必须保留大编辑稿列和关键 owner/领取索引。"""
    from alembic import command

    output = io.StringIO()
    config = _alembic_config("mysql+pymysql://user:password@db.example.com/trainppt")
    config.output_buffer = output
    command.upgrade(config, "head", sql=True)

    sql = output.getvalue().upper()
    assert "CREATE TABLE TRAINPPT_PRESENTATIONS" in sql
    assert "LONGTEXT" in sql
    assert "IX_PRESENTATIONS_OWNER_DELETED_UPDATED" in sql
    assert "IX_GENERATION_TASKS_CLAIM" in sql
    assert "IX_GENERATION_TASKS_RECOVERY" in sql
    assert "DISPATCH_STARTED_AT" in sql


def test_t19_storage_usage_migration_backfills_existing_active_files(tmp_path: Path) -> None:
    """升级不能把既有对象当作零占额，否则用户可在迁移后绕过配额。"""
    from alembic import command

    database_url = f"sqlite:///{(tmp_path / 'storage-backfill.db').as_posix()}"
    config = _alembic_config(database_url)
    command.upgrade(config, "20260723_0005")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO trainppt_presentations "
                "(id, owner_user_id, title, status, slides_json, created_at, updated_at) "
                "VALUES ('p-storage', 1001, '存储作品', 'ready', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO trainppt_files "
                "(id, owner_user_id, presentation_id, purpose, object_key, mime_type, size_bytes, "
                "sha256, status, created_at, updated_at) VALUES "
                "('f-active', 1001, 'p-storage', 'source', 'safe/a', 'application/pdf', 9, "
                "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'active', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                "('f-failed', 1001, 'p-storage', 'source', 'safe/b', 'application/pdf', 99, "
                "'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'failed', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            usage = connection.execute(text(
                "SELECT used_bytes, file_count FROM trainppt_owner_storage_usage WHERE owner_user_id=1001"
            )).one()
        assert tuple(usage) == (9, 1)
    finally:
        engine.dispose()


def test_application_rollback_does_not_delete_business_data(tmp_path: Path) -> None:
    """迁移基线降回 base 只调整版本，不得删除已有业务表或记录。"""
    from alembic import command

    database_path = tmp_path / "rollback.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE existing_business_data (id INTEGER PRIMARY KEY, value TEXT)"))
            connection.execute(text("INSERT INTO existing_business_data (id, value) VALUES (1, 'keep')"))

        command.downgrade(config, "base")

        assert "existing_business_data" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            value = connection.execute(
                text("SELECT value FROM existing_business_data WHERE id=1")
            ).scalar_one()
        assert value == "keep"
    finally:
        # 保证临时数据库可由 pytest 清理，不把连接池生命周期泄漏到其他用例。
        engine.dispose()


def test_mysql_offline_migration_contains_no_business_drop() -> None:
    """用 MySQL 方言生成迁移 SQL，基线只能创建版本表且不得删除业务对象。"""
    from alembic import command

    output = io.StringIO()
    config = _alembic_config("mysql+pymysql://user:password@db.example.com/trainppt")
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue().upper()
    assert "CREATE TABLE ALEMBIC_VERSION" in sql
    assert "DROP TABLE" not in sql


def test_application_startup_does_not_auto_migrate_or_delete_data(tmp_path: Path) -> None:
    """应用二进制启动不得自动执行 Alembic，保证版本回滚不会隐式删表。"""
    database_path = tmp_path / "application-startup.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE existing_business_data (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO existing_business_data (id) VALUES (1)"))

        repository_root = Path(__file__).resolve().parents[3]
        # 子进程只继承 Python/Windows 启动所需变量，避免开发机上的功能开关或非法容量值污染测试。
        environment = {
            key: os.environ[key]
            for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
            if key in os.environ
        }
        environment.update(
            {
                "DATABASE_URL": database_url,
                "APP_ENV": "test",
                "PERSISTENCE_ENABLED": "true",
                "SSO_ENABLED": "false",
                "STORAGE_ENABLED": "false",
                "BILLING_ENABLED": "false",
            }
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                # 禁止主模块在隔离测试中重新载入仓库 .env，确保配置来源只有上面的白名单。
                "import dotenv; dotenv.load_dotenv=lambda *a, **k: False; import main",
            ],
            cwd=repository_root / "backend/main_api",
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        # 持久化开启但迁移缺失时必须在监听前失败，同时禁止自动建表或删除既有数据。
        assert result.returncode != 0
        assert "作品数据表迁移未完成" in result.stderr
        assert "existing_business_data" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM existing_business_data")).scalar_one() == 1
    finally:
        engine.dispose()
