"""T01 集中配置模型的公开行为测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import dotenv_values

from backend.main_api.core.config import ConfigValidationError, load_settings


def _valid_billing_configuration() -> dict[str, str]:
    """返回不依赖本机环境的最小计费配置，便于逐项验证 fail-closed。"""
    return {
        "APP_ENV": "test",
        "SSO_ENABLED": "true",
        "PERSISTENCE_ENABLED": "true",
        "BILLING_ENABLED": "true",
        "TASK_WORKER_ENABLED": "true",
        "TASK_HANDLER_FACTORY": "backend.main_api.workers.example:create_handler",
        "MOLING_API_BASE_URL": "https://moling.example.com/api",
        "APP_BASE_URL": "https://ppt.example.com/app",
        "INTERNAL_API_TOKEN": "test-internal-token",
        "MOLING_APP_ID": "1001",
        "MOLING_PRODUCT_ID": "2001",
        "SESSION_SECRET": "s" * 32,
        "DATABASE_URL": "mysql+pymysql://user:password@db.example.com/trainppt",
        "PPT_GENERATION_RESERVE_POINTS": "1",
        "PPT_GENERATION_SETTLE_POINTS": "1",
    }


def test_new_features_are_closed_by_default() -> None:
    """未显式开启的墨灵能力必须保持关闭，避免旧部署意外进入新链路。"""
    settings = load_settings({})

    assert settings.sso_enabled is False
    assert settings.persistence_enabled is False
    assert settings.storage_enabled is False
    assert settings.billing_enabled is False


def test_moling_client_timeouts_are_bounded_and_configurable() -> None:
    """墨灵连接与读取超时必须独立配置，避免内部调用无限占用请求。"""
    settings = load_settings(
        {
            "MOLING_CONNECT_TIMEOUT_SECONDS": "2",
            "MOLING_READ_TIMEOUT_SECONDS": "15",
        }
    )

    assert settings.moling_connect_timeout_seconds == 2
    assert settings.moling_read_timeout_seconds == 15


def test_session_absolute_and_idle_ttls_are_configurable() -> None:
    """Session同时具有绝对和空闲期限，且空闲期限必须更短。"""
    settings = load_settings(
        {
            "SESSION_TTL_SECONDS": "86400",
            "SESSION_IDLE_TTL_SECONDS": "7200",
        }
    )

    assert settings.session_ttl_seconds == 86400
    assert settings.session_idle_ttl_seconds == 7200


def test_session_idle_ttl_must_be_shorter_than_absolute_ttl() -> None:
    """禁止配置永远不会触发的空闲过期规则。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(
            {
                "SESSION_TTL_SECONDS": "7200",
                "SESSION_IDLE_TTL_SECONDS": "7200",
            }
        )

    assert "SESSION_IDLE_TTL_SECONDS" in str(exc_info.value)


def test_sso_requires_persistence_and_database() -> None:
    """SSO Session必须持久化，禁止依靠assert或内存状态在运行期崩溃。"""
    base = {
        "SSO_ENABLED": "true",
        "MOLING_API_BASE_URL": "https://moling.example.test",
        "INTERNAL_API_TOKEN": "token",
        "MOLING_APP_ID": "15",
        "MOLING_PRODUCT_ID": "73",
        "SESSION_SECRET": "x" * 32,
    }
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(base)

    message = str(exc_info.value)
    assert "PERSISTENCE_ENABLED" in message
    assert "DATABASE_URL" in message


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("MOLING_CONNECT_TIMEOUT_SECONDS", "0"),
        ("MOLING_READ_TIMEOUT_SECONDS", "301"),
        ("MOLING_READ_TIMEOUT_SECONDS", "secret-like-invalid"),
    ],
)
def test_invalid_moling_timeout_fails_without_echoing_value(key: str, value: str) -> None:
    """超时必须为安全范围内整数，错误只包含键名。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({key: value})

    assert key in str(exc_info.value)
    assert value not in str(exc_info.value)


@pytest.mark.parametrize("raw_value", ["yes", "1", "token-like-super-secret"])
def test_invalid_boolean_fails_without_echoing_input(raw_value: str) -> None:
    """布尔值只接受 true/false，错误文本不得回显可能包含秘密的原值。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"SSO_ENABLED": raw_value})

    message = str(exc_info.value)
    assert "SSO_ENABLED" in message
    assert raw_value not in message


def test_sso_requires_platform_and_session_configuration() -> None:
    """开启 SSO 后，缺少平台身份或会话配置必须在启动前失败。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"SSO_ENABLED": "true"})

    message = str(exc_info.value)
    assert "MOLING_API_BASE_URL" in message
    assert "INTERNAL_API_TOKEN" in message
    assert "MOLING_APP_ID" in message
    assert "MOLING_PRODUCT_ID" in message
    assert "SESSION_SECRET" in message
    assert "APP_BASE_URL" in message


def test_invalid_url_fails_without_echoing_secret() -> None:
    """启用功能使用的 URL 必须是 HTTP(S)，异常不得包含内部令牌。"""
    secret = "internal-token-must-not-leak"

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(
            {
                "SSO_ENABLED": "true",
                "MOLING_API_BASE_URL": "ftp://platform.example.invalid",
                "INTERNAL_API_TOKEN": secret,
                "MOLING_APP_ID": "1001",
                "MOLING_PRODUCT_ID": "2001",
                "SESSION_SECRET": "s" * 32,
            }
        )

    message = str(exc_info.value)
    assert "MOLING_API_BASE_URL" in message
    assert secret not in message


@pytest.mark.parametrize(
    "invalid_url",
    ["https://moling.example.com:99999", "https://bad host.example.com"],
)
def test_url_rejects_invalid_port_and_whitespace_host(invalid_url: str) -> None:
    """URL 解析器的宽松结果不能绕过端口范围和主机字符校验。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"MOLING_API_BASE_URL": invalid_url})

    assert "MOLING_API_BASE_URL" in str(exc_info.value)


def test_invalid_duration_fails_instead_of_silently_using_default() -> None:
    """超时和对账间隔写错时必须阻止启动，不能静默退回默认值。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(
            {
                "SESSION_TTL_SECONDS": "not-a-number",
                "BILLING_RECONCILE_INTERVAL_SECONDS": "5",
            }
        )

    message = str(exc_info.value)
    assert "SESSION_TTL_SECONDS" in message
    assert "BILLING_RECONCILE_INTERVAL_SECONDS" in message


def test_production_sso_requires_secure_cookie() -> None:
    """生产 SSO 禁止通过明文 Cookie，避免 Session 在 HTTP 中泄漏。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(
            {
                "APP_ENV": "production",
                "SSO_ENABLED": "true",
                "MOLING_API_BASE_URL": "https://moling.example.com",
                "INTERNAL_API_TOKEN": "secret-token",
                "MOLING_APP_ID": "1001",
                "MOLING_PRODUCT_ID": "2001",
                "SESSION_SECRET": "s" * 32,
                "SESSION_COOKIE_SECURE": "false",
            }
        )

    assert "SESSION_COOKIE_SECURE" in str(exc_info.value)


def test_storage_and_billing_validate_feature_dependencies() -> None:
    """存储和计费不得绕过持久化、身份等前置能力独立开启。"""
    with pytest.raises(ConfigValidationError) as storage_error:
        load_settings({"STORAGE_ENABLED": "true"})
    assert "PERSISTENCE_ENABLED" in str(storage_error.value)

    with pytest.raises(ConfigValidationError) as billing_error:
        load_settings({"BILLING_ENABLED": "true"})
    message = str(billing_error.value)
    assert "SSO_ENABLED" in message
    assert "PERSISTENCE_ENABLED" in message
    assert "TASK_WORKER_ENABLED" in message


@pytest.mark.parametrize(
    ("missing_key", "expected_error_key"),
    [
        ("SSO_ENABLED", "SSO_ENABLED"),
        ("PERSISTENCE_ENABLED", "PERSISTENCE_ENABLED"),
        ("TASK_WORKER_ENABLED", "TASK_WORKER_ENABLED"),
        ("TASK_HANDLER_FACTORY", "TASK_HANDLER_FACTORY"),
        ("DATABASE_URL", "DATABASE_URL"),
        ("MOLING_API_BASE_URL", "MOLING_API_BASE_URL"),
        ("INTERNAL_API_TOKEN", "INTERNAL_API_TOKEN"),
        ("MOLING_APP_ID", "MOLING_APP_ID"),
        ("MOLING_PRODUCT_ID", "MOLING_PRODUCT_ID"),
        ("SESSION_SECRET", "SESSION_SECRET"),
        ("APP_BASE_URL", "APP_BASE_URL"),
        ("PPT_GENERATION_RESERVE_POINTS", "PPT_GENERATION_RESERVE_POINTS"),
        ("PPT_GENERATION_SETTLE_POINTS", "PPT_GENERATION_SETTLE_POINTS"),
    ],
)
def test_billing_rejects_each_missing_runtime_dependency(
    missing_key: str,
    expected_error_key: str,
) -> None:
    """打开计费后，任一身份、持久化、Worker 或金额缺失都必须阻止启动。"""
    values = _valid_billing_configuration()
    values.pop(missing_key)

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(values)

    message = str(exc_info.value)
    assert expected_error_key in message
    configured_token = values.get("INTERNAL_API_TOKEN")
    if configured_token is not None:
        assert configured_token not in message


def test_minimal_billing_configuration_is_accepted() -> None:
    settings = load_settings(_valid_billing_configuration())

    assert settings.billing_enabled is True
    assert settings.task_worker_enabled is True
    assert settings.ppt_generation_reserve_points == 1
    assert settings.ppt_generation_settle_points == 1


def test_valid_enabled_configuration_is_parsed() -> None:
    """依赖齐全时集中配置应产生可供后续任务复用的强类型值。"""
    settings = load_settings(
        {
            "APP_ENV": "test",
            "SSO_ENABLED": "true",
            "PERSISTENCE_ENABLED": "true",
            "STORAGE_ENABLED": "true",
            "BILLING_ENABLED": "true",
            "TASK_WORKER_ENABLED": "true",
            "TASK_HANDLER_FACTORY": "backend.main_api.workers.example:create_handler",
            "MOLING_API_BASE_URL": "https://moling.example.com/api",
            "APP_BASE_URL": "https://ppt.example.com/app",
            "INTERNAL_API_TOKEN": "secret-token",
            "MOLING_APP_ID": "1001",
            "MOLING_PRODUCT_ID": "2001",
            "SESSION_SECRET": "s" * 32,
            "DATABASE_URL": "mysql+pymysql://user:password@db.example.com/trainppt",
            "STORAGE_ENDPOINT": "https://storage.example.com",
            "STORAGE_BUCKET": "trainppt",
            "STORAGE_ACCESS_KEY_ID": "access-key",
            "STORAGE_SECRET_ACCESS_KEY": "secret-key",
            "USER_PRESENTATION_LIMIT": "100",
            "USER_STORAGE_QUOTA_BYTES": "1073741824",
            "PPT_GENERATION_RESERVE_POINTS": "20",
            "PPT_GENERATION_SETTLE_POINTS": "15",
        }
    )

    assert settings.main_api_port == 6800
    assert settings.moling_app_id == 1001
    assert settings.moling_product_id == 2001
    assert settings.billing_enabled is True
    assert settings.internal_api_token.get_secret_value() == "secret-token"


def test_fixed_settlement_points_cannot_exceed_reserved_points() -> None:
    """固定结算第一版必须满足actual不超过预占，且错误不回显具体运营数值。"""
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({
            "PPT_GENERATION_RESERVE_POINTS": "8",
            "PPT_GENERATION_SETTLE_POINTS": "9",
        })
    message = str(exc_info.value)
    assert "PPT_GENERATION_SETTLE_POINTS" in message
    assert "9" not in message


def test_billing_reconciliation_retry_limit_is_bounded() -> None:
    settings = load_settings({"BILLING_RECONCILE_MAX_RETRIES": "5"})
    assert settings.billing_reconcile_max_retries == 5

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"BILLING_RECONCILE_MAX_RETRIES": "101"})
    assert "BILLING_RECONCILE_MAX_RETRIES" in str(exc_info.value)


def test_repository_template_contains_t01_keys_and_keeps_billing_disabled() -> None:
    """仓库模板必须可复制使用，并以关闭真实计费作为安全默认值。"""
    repository_root = Path(__file__).resolve().parents[3]
    template = dotenv_values(repository_root / "env_template.txt")

    required_keys = {
        "MOLING_API_BASE_URL",
        "INTERNAL_API_TOKEN",
        "MOLING_APP_ID",
        "MOLING_PRODUCT_ID",
        "SESSION_SECRET",
        "DATABASE_URL",
        "STORAGE_ENDPOINT",
        "STORAGE_BUCKET",
        "STORAGE_ACCESS_KEY_ID",
        "STORAGE_SECRET_ACCESS_KEY",
        "DOWNLOAD_SIGNING_SECRET",
        "DOWNLOAD_URL_TTL_SECONDS",
        "SSO_ENABLED",
        "PERSISTENCE_ENABLED",
        "STORAGE_ENABLED",
        "BILLING_ENABLED",
        "MAIN_API_PORT",
        "OUTLINE_API_PORT",
        "CONTENT_API_PORT",
        "PERSONALDB_PORT",
        "FRONTEND_PORT",
    }

    assert required_keys <= template.keys()
    assert template["BILLING_ENABLED"] == "false"


def test_operational_safety_configuration_is_bounded_and_production_cannot_disable_rate_limit() -> None:
    settings = load_settings({
        "RATE_LIMIT_REQUESTS": "45",
        "RATE_LIMIT_WINDOW_SECONDS": "90",
        "HEALTH_PROBE_TIMEOUT_SECONDS": "5",
        "AUDIT_LOG_ENABLED": "true",
    })
    assert settings.rate_limit_requests == 45
    assert settings.rate_limit_window_seconds == 90
    assert settings.health_probe_timeout_seconds == 5
    assert settings.audit_log_enabled is True

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings({"APP_ENV": "production", "RATE_LIMIT_ENABLED": "false"})
    assert "RATE_LIMIT_ENABLED" in str(exc_info.value)


def test_repository_template_contains_t21_safety_keys() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    template = dotenv_values(repository_root / "env_template.txt")
    assert {
        "RATE_LIMIT_ENABLED", "RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW_SECONDS",
        "AUDIT_LOG_ENABLED", "HEALTH_PROBE_TIMEOUT_SECONDS",
    } <= template.keys()
    assert template["RATE_LIMIT_ENABLED"] == "true"
    assert template["AUDIT_LOG_ENABLED"] == "true"
