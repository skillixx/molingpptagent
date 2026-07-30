"""BG05 生产预部署静态与数据库只读预检，输出仅包含脱敏结论。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main_api.core.config import ConfigValidationError, Settings, load_settings
from backend.main_api.core.db import DatabaseConnectionError, create_verified_database_engine


EXPECTED_HEAD = "20260730_0008"
EXPECTED_PREVIOUS = "20260723_0007"
_MAX_SIGNED_BIGINT = 9_223_372_036_854_775_807
_REQUIRED_EXPLICIT_OPERATION_KEYS = (
    "PRESENTATION_JSON_MAX_BYTES",
    "UPLOAD_FILE_MAX_BYTES",
    "EXPORT_PPTX_MAX_BYTES",
    "USER_PRESENTATION_LIMIT",
    "USER_STORAGE_QUOTA_BYTES",
    "RATE_LIMIT_REQUESTS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "PPT_GENERATION_RESERVE_POINTS",
    "PPT_GENERATION_SETTLE_POINTS",
)


@dataclass(frozen=True)
class DatabaseAudit:
    database_name: str
    version: str
    entitlement_column_present: bool
    invalid_billing_id_count: int
    active_billing_operation_count: int


def _read_environment(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError("生产环境文件不存在")
    values = dotenv_values(path)
    return {str(key): str(value) for key, value in values.items() if value is not None}


def validate_static_environment(
    values: Mapping[str, str], *, expected_release: str
) -> Settings:
    """复用应用校验并增加 BG05 的显式运营值和关闭计费约束。"""
    errors: list[str] = []
    if str(values.get("APP_ENV", "")).strip().lower() != "production":
        errors.append("APP_ENV 必须为 production")
    if str(values.get("RELEASE_COMMIT", "")).strip() != expected_release:
        errors.append("RELEASE_COMMIT 与待发布提交不一致")
    if str(values.get("BILLING_ENABLED", "")).strip().lower() != "false":
        errors.append("BG05 必须保持 BILLING_ENABLED=false")
    if str(values.get("TASK_WORKER_ENABLED", "")).strip().lower() != "false":
        errors.append("环境文件必须保持 TASK_WORKER_ENABLED=false，由受控 Worker profile 覆盖")
    for key in _REQUIRED_EXPLICIT_OPERATION_KEYS:
        if not str(values.get(key, "")).strip():
            errors.append(f"{key} 必须使用已确认的生产显式值")

    settings: Settings | None = None
    try:
        settings = load_settings(values)
    except ConfigValidationError as exc:
        errors.append(str(exc))

    # 用生产 Compose 的 Worker 覆盖值再校验一次，确保处理器和持久化依赖完整。
    worker_values = {
        **values,
        "TASK_WORKER_ENABLED": "true",
        "TASK_HANDLER_FACTORY": "backend.main_api.workers.presentation_handler:create_handler",
        "BILLING_ENABLED": "false",
    }
    try:
        load_settings(worker_values)
    except ConfigValidationError as exc:
        errors.append(f"Worker 配置无效：{exc}")
    if errors:
        raise RuntimeError("；".join(dict.fromkeys(errors)))
    assert settings is not None
    return settings


def _valid_numeric_identifier(value: object) -> bool:
    if value is None:
        return True
    raw = str(value)
    return raw.isascii() and raw.isdigit() and 0 < int(raw) <= _MAX_SIGNED_BIGINT


def audit_database(settings: Settings, *, expected_version: str) -> DatabaseAudit:
    """只读事务核对迁移版本、目标列和迁移前数据，始终回滚并释放连接。"""
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL 未配置")
    engine = create_verified_database_engine(settings.database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            connection.execute(text("SET SESSION TRANSACTION READ ONLY"))
            connection.commit()
            transaction = connection.begin()
            try:
                database_name = str(
                    connection.execute(text("SELECT DATABASE()")).scalar_one()
                )
                version = str(
                    connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                )
                columns = {
                    column["name"]
                    for column in inspect(connection).get_columns("app_sessions")
                }
                rows = connection.execute(text(
                    "SELECT entitlement_id, hold_id FROM trainppt_billing_operations "
                    "WHERE entitlement_id IS NOT NULL OR hold_id IS NOT NULL"
                )).all()
                invalid_count = sum(
                    not _valid_numeric_identifier(value)
                    for row in rows
                    for value in row
                    if value is not None
                )
                active_count = int(
                    connection.execute(text(
                        "SELECT COUNT(*) FROM trainppt_billing_operations "
                        "WHERE status IN "
                        "('planned','reserving','reserved','settling','releasing',"
                        "'billing_pending','reconciling','manual_required')"
                    )).scalar_one()
                )
            finally:
                transaction.rollback()
    except SQLAlchemyError:
        raise RuntimeError("生产数据库只读审计失败") from None
    finally:
        engine.dispose()

    entitlement_present = "entitlement_id" in columns
    if version != expected_version:
        raise RuntimeError("生产数据库迁移版本与预期不一致")
    if expected_version == EXPECTED_PREVIOUS and entitlement_present:
        raise RuntimeError("迁移前数据库已出现 0008 目标列")
    if expected_version == EXPECTED_HEAD and not entitlement_present:
        raise RuntimeError("迁移后数据库缺少 0008 目标列")
    if invalid_count:
        raise RuntimeError(f"迁移前存在 {invalid_count} 个非法计费标识")
    if active_count:
        # BG05 未授权处理任何历史账务；只要存在非终态或人工记录，就禁止启动 Worker。
        raise RuntimeError(f"生产应用库存在 {active_count} 个未关闭计费操作")
    return DatabaseAudit(
        database_name=database_name,
        version=version,
        entitlement_column_present=entitlement_present,
        invalid_billing_id_count=invalid_count,
        active_billing_operation_count=active_count,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TrainPPTAgent BG05 生产预检")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--expected-release", required=True)
    parser.add_argument(
        "--expected-db-version",
        choices=(EXPECTED_PREVIOUS, EXPECTED_HEAD),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        values = _read_environment(args.env_file)
        settings = validate_static_environment(values, expected_release=args.expected_release)
        audit = (
            audit_database(settings, expected_version=args.expected_db_version)
            if args.expected_db_version
            else None
        )
    except (ConfigValidationError, DatabaseConnectionError, RuntimeError, ValueError) as exc:
        print(json.dumps({
            "ready": False,
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }, ensure_ascii=False))
        return 2

    print(json.dumps({
        "ready": True,
        "release_commit": settings.release_commit,
        "release_channel": settings.release_channel,
        "billing_enabled": settings.billing_enabled,
        "database": asdict(audit) if audit else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
