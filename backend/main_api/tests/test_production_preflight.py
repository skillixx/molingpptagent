"""BG05 生产预检与备份命令的安全契约测试。"""

from __future__ import annotations

import pytest

from backend.main_api.tools.production_backup import build_dump_command
from backend.main_api.tools.production_preflight import (
    _valid_numeric_identifier,
    validate_static_environment,
)


RELEASE = "a" * 40


def _valid_environment() -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "APP_BASE_URL": "https://ppt.example.com",
        "RELEASE_COMMIT": RELEASE,
        "RELEASE_CHANNEL": "production",
        "SSO_ENABLED": "true",
        "PERSISTENCE_ENABLED": "true",
        "STORAGE_ENABLED": "true",
        "BILLING_ENABLED": "false",
        "TASK_WORKER_ENABLED": "false",
        "SESSION_COOKIE_SECURE": "true",
        "SESSION_SECRET": "s" * 32,
        "DOWNLOAD_SIGNING_SECRET": "d" * 32,
        "DATABASE_URL": "mysql+pymysql://user:password@db.example.com/ppt_ai_app",
        "MOLING_API_BASE_URL": "https://moling.example.com",
        "INTERNAL_API_TOKEN": "internal-secret",
        "MOLING_APP_ID": "15",
        "MOLING_PRODUCT_ID": "73",
        "STORAGE_ENDPOINT": "https://storage.example.com",
        "STORAGE_BUCKET": "ppt",
        "STORAGE_ACCESS_KEY_ID": "access",
        "STORAGE_SECRET_ACCESS_KEY": "storage-secret",
        "PRESENTATION_JSON_MAX_BYTES": "10485760",
        "UPLOAD_FILE_MAX_BYTES": "52428800",
        "EXPORT_PPTX_MAX_BYTES": "104857600",
        "USER_PRESENTATION_LIMIT": "1000",
        "USER_STORAGE_QUOTA_BYTES": "10737418240",
        "RATE_LIMIT_REQUESTS": "30",
        "RATE_LIMIT_WINDOW_SECONDS": "60",
        "PPT_GENERATION_RESERVE_POINTS": "1",
        "PPT_GENERATION_SETTLE_POINTS": "1",
    }


def test_static_preflight_accepts_versioned_production_with_billing_off() -> None:
    settings = validate_static_environment(_valid_environment(), expected_release=RELEASE)

    assert settings.app_env == "production"
    assert settings.release_commit == RELEASE
    assert settings.billing_enabled is False
    assert settings.task_worker_enabled is False
    assert settings.ppt_generation_reserve_points == 1
    assert settings.ppt_generation_settle_points == 1


def test_static_preflight_accepts_explicit_billing_on_release() -> None:
    values = _valid_environment()
    values["BILLING_ENABLED"] = "true"

    settings = validate_static_environment(
        values,
        expected_release=RELEASE,
        expected_billing_enabled=True,
    )

    assert settings.billing_enabled is True
    assert settings.ppt_generation_reserve_points == 1
    assert settings.ppt_generation_settle_points == 1


def test_static_preflight_rejects_billing_state_different_from_release_mode() -> None:
    values = _valid_environment()
    values["BILLING_ENABLED"] = "true"

    with pytest.raises(RuntimeError) as exc_info:
        validate_static_environment(values, expected_release=RELEASE)

    assert "BILLING_ENABLED" in str(exc_info.value)


@pytest.mark.parametrize(
    "missing_key",
    ("PPT_GENERATION_RESERVE_POINTS", "PPT_GENERATION_SETTLE_POINTS"),
)
def test_static_preflight_requires_billing_policy_even_while_billing_is_off(
    missing_key: str,
) -> None:
    values = _valid_environment()
    values.pop(missing_key)

    with pytest.raises(RuntimeError) as exc_info:
        validate_static_environment(values, expected_release=RELEASE)

    assert missing_key in str(exc_info.value)


def test_static_preflight_rejects_missing_capacity_and_release_mismatch_without_secrets() -> None:
    values = _valid_environment()
    values.pop("USER_STORAGE_QUOTA_BYTES")

    with pytest.raises(RuntimeError) as exc_info:
        validate_static_environment(values, expected_release="b" * 40)

    message = str(exc_info.value)
    assert "USER_STORAGE_QUOTA_BYTES" in message
    assert "RELEASE_COMMIT" in message
    assert "internal-secret" not in message
    assert "storage-secret" not in message


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        (None, True),
        ("1", True),
        (str(9_223_372_036_854_775_807), True),
        ("0", False),
        ("-1", False),
        ("１２", False),
        ("text", False),
        (str(9_223_372_036_854_775_808), False),
    ],
)
def test_numeric_identifier_audit_matches_migration_contract(value: object, valid: bool) -> None:
    assert _valid_numeric_identifier(value) is valid


def test_backup_command_keeps_password_out_of_arguments() -> None:
    command, database, password = build_dump_command(
        "mysql+pymysql://backup_user:super-secret@db.example.com:3307/ppt_ai_app",
        "/usr/bin/mysqldump",
    )

    assert database == "ppt_ai_app"
    assert password == "super-secret"
    assert all("super-secret" not in item for item in command)
    assert "--single-transaction" in command
    assert "--routines" in command
    assert "--triggers" in command
    assert command[-1] == "ppt_ai_app"


def test_backup_command_rejects_non_mysql_database() -> None:
    with pytest.raises(RuntimeError):
        build_dump_command("sqlite:///local.db", "mysqldump")
