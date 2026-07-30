"""T02 容量、配额、保留与清理配置测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import dotenv_values

from backend.main_api.core.config import ConfigValidationError, load_settings


def test_capacity_defaults_match_m0_decisions() -> None:
    """默认值采用已批准基线，未知的用户配额继续保持未启用。"""
    settings = load_settings({})

    assert settings.presentation_json_max_bytes == 10 * 1024 * 1024
    assert settings.checkpoint_max_count == 20
    assert settings.checkpoint_inline_max_bytes == 1024 * 1024
    assert settings.upload_file_max_bytes == 50 * 1024 * 1024
    assert settings.export_pptx_max_bytes == 100 * 1024 * 1024
    assert settings.thumbnail_max_bytes == 2 * 1024 * 1024
    assert settings.soft_delete_retention_days == 30
    assert settings.cleanup_batch_size == 100
    assert settings.user_presentation_limit is None
    assert settings.user_storage_quota_bytes is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("PRESENTATION_JSON_MAX_BYTES", "0"),
        ("CHECKPOINT_MAX_COUNT", "0"),
        ("CHECKPOINT_INLINE_MAX_BYTES", "not-a-number"),
        ("UPLOAD_FILE_MAX_BYTES", "0"),
        ("EXPORT_PPTX_MAX_BYTES", "-1"),
        ("THUMBNAIL_MAX_BYTES", "0"),
        ("SOFT_DELETE_RETENTION_DAYS", "-1"),
        ("CLEANUP_BATCH_SIZE", "0"),
        ("USER_PRESENTATION_LIMIT", "unlimited"),
        ("USER_STORAGE_QUOTA_BYTES", "-1"),
    ],
)
def test_invalid_capacity_value_fails_without_echoing_input(key: str, value: str) -> None:
    """容量配置错误必须阻止启动，异常只报告键名而不回显输入。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({key: value})

    message = str(exc_info.value)
    assert key in message
    assert value not in message


def test_inline_checkpoint_cannot_exceed_presentation_limit() -> None:
    """数据库内联检查点上限不得高于单作品 JSON 上限。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(
            {
                "PRESENTATION_JSON_MAX_BYTES": "1024",
                "CHECKPOINT_INLINE_MAX_BYTES": "2048",
            }
        )

    assert "CHECKPOINT_INLINE_MAX_BYTES" in str(exc_info.value)


def test_task_lease_defaults_and_heartbeat_invariant() -> None:
    """租约心跳必须明显短于租期，给进程抖动和超时回收留下窗口。"""
    settings = load_settings({})

    assert settings.task_lease_seconds == 120
    assert settings.task_heartbeat_seconds == 30
    assert settings.task_max_attempts == 3
    assert settings.task_claim_batch_size == 10
    assert settings.task_worker_enabled is False
    assert settings.task_agent_timeout_seconds == 600
    assert settings.task_poll_seconds == 2

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"TASK_LEASE_SECONDS": "60", "TASK_HEARTBEAT_SECONDS": "30"})

    assert "TASK_HEARTBEAT_SECONDS" in str(exc_info.value)


def test_worker_start_requires_persistence_database_and_handler_factory() -> None:
    """独立 Worker 不能在缺少持久化或业务处理器时启动，以免误领后丢弃任务。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"TASK_WORKER_ENABLED": "true"})

    message = str(exc_info.value)
    assert "PERSISTENCE_ENABLED" in message
    assert "DATABASE_URL" in message
    assert "TASK_HANDLER_FACTORY" in message

    settings = load_settings(
        {
            "TASK_WORKER_ENABLED": "true",
            "PERSISTENCE_ENABLED": "true",
            "DATABASE_URL": "mysql+pymysql://worker:secret@db/trainppt",
            "TASK_HANDLER_FACTORY": "backend.main_api.workers.example:create_handler",
        }
    )
    assert settings.task_worker_enabled is True
    assert settings.task_handler_factory == "backend.main_api.workers.example:create_handler"


def test_environment_template_contains_capacity_and_lease_defaults() -> None:
    """部署模板必须与集中配置的容量和租约默认值保持一致。"""
    repository_root = Path(__file__).resolve().parents[3]
    template = dotenv_values(repository_root / "env_template.txt")

    assert template["PRESENTATION_JSON_MAX_BYTES"] == str(10 * 1024 * 1024)
    assert template["CHECKPOINT_MAX_COUNT"] == "20"
    assert template["TASK_LEASE_SECONDS"] == "120"
    assert template["TASK_HEARTBEAT_SECONDS"] == "30"
    assert template["TASK_WORKER_ENABLED"] == "false"
    assert template["TASK_AGENT_TIMEOUT_SECONDS"] == "600"
    assert template["TASK_POLL_SECONDS"] == "2"
    assert template["TASK_HANDLER_FACTORY"] == (
        "backend.main_api.workers.presentation_handler:create_handler"
    )
    assert template["USER_PRESENTATION_LIMIT"] == "100"
    assert template["USER_STORAGE_QUOTA_BYTES"] == str(1024 * 1024 * 1024)


def test_uat_templates_are_isolated_and_default_to_closed_billing() -> None:
    """UAT 部署包必须使用独立数据库命名，并在未授权时保持 Worker 和计费关闭。"""
    repository_root = Path(__file__).resolve().parents[3]
    template = dotenv_values(repository_root / "env_uat_template.txt")
    compose = (repository_root / "docker-compose.uat.yml").read_text(encoding="utf-8")

    assert template["APP_ENV"] == "test"
    assert template["UAT_DB_NAME"] == "trainppt_uat"
    assert str(template["DATABASE_URL"]).split("?", 1)[0].endswith("/trainppt_uat")
    assert template["UAT_BILLING_ENABLED"] == "false"
    assert template["UAT_TASK_WORKER_ENABLED"] == "false"
    assert template["TASK_HANDLER_FACTORY"] == (
        "backend.main_api.workers.presentation_handler:create_handler"
    )
    assert "ppt.axicomin.cn" not in compose
    assert "condition: service_completed_successfully" in compose
