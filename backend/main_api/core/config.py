"""TrainPPTAgent 墨灵对接的集中配置与启动校验。"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, SecretStr


class ConfigValidationError(RuntimeError):
    """表示部署配置不满足安全启动条件，消息中只允许出现配置键名。"""


class Settings(BaseModel):
    """经过类型转换和功能依赖校验的只读应用配置。"""

    model_config = ConfigDict(frozen=True)

    app_env: Literal["development", "test", "staging", "production"] = "development"
    host: str = "127.0.0.1"
    main_api_port: int = 6800
    outline_api_port: int = 10001
    content_api_port: int = 10011
    personaldb_port: int = 9100
    frontend_port: int = 5778
    release_commit: str | None = None
    release_channel: str = "development"

    outline_api: str = "http://127.0.0.1:10001"
    content_api: str = "http://127.0.0.1:10011"
    personal_db: str = "http://127.0.0.1:9100"
    app_base_url: str | None = None

    sso_enabled: bool = False
    persistence_enabled: bool = False
    storage_enabled: bool = False
    billing_enabled: bool = False

    moling_api_base_url: str | None = None
    internal_api_token: SecretStr | None = None
    moling_app_id: int | None = None
    moling_product_id: int | None = None
    moling_connect_timeout_seconds: int = 3
    moling_read_timeout_seconds: int = 15

    session_secret: SecretStr | None = None
    session_cookie_name: str = "trainppt_session"
    session_cookie_secure: bool = False
    session_ttl_seconds: int = 86400
    session_idle_ttl_seconds: int = 7200

    database_url: SecretStr | None = None
    storage_endpoint: str | None = None
    storage_bucket: str | None = None
    storage_access_key_id: SecretStr | None = None
    storage_secret_access_key: SecretStr | None = None
    storage_prefix: str = "trainppt"
    storage_connect_timeout_seconds: int = 3
    storage_read_timeout_seconds: int = 30
    storage_max_attempts: int = 3
    storage_upload_stale_seconds: int = 900
    download_signing_secret: SecretStr | None = None
    download_url_ttl_seconds: int = 300

    ppt_generation_reserve_points: int | None = None
    ppt_generation_settle_points: int | None = None
    slide_regeneration_points: int | None = None
    billing_reconcile_interval_seconds: int = 60
    billing_reconcile_max_retries: int = 8

    presentation_json_max_bytes: int = 10 * 1024 * 1024
    checkpoint_max_count: int = 20
    checkpoint_inline_max_bytes: int = 1024 * 1024
    upload_file_max_bytes: int = 50 * 1024 * 1024
    export_pptx_max_bytes: int = 100 * 1024 * 1024
    thumbnail_max_bytes: int = 2 * 1024 * 1024
    soft_delete_retention_days: int = 30
    cleanup_interval_seconds: int = 3600
    cleanup_batch_size: int = 100
    user_presentation_limit: int | None = None
    user_storage_quota_bytes: int | None = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    audit_log_enabled: bool = True
    health_probe_timeout_seconds: int = 3

    task_lease_seconds: int = 120
    task_heartbeat_seconds: int = 30
    task_max_attempts: int = 3
    task_retry_backoff_seconds: int = 30
    task_claim_batch_size: int = 10
    task_worker_enabled: bool = False
    task_agent_timeout_seconds: int = 600
    task_poll_seconds: int = 2
    task_handler_factory: str | None = None


_TRUE = "true"
_FALSE = "false"


def _text(source: Mapping[str, str], key: str, default: str | None = None) -> str | None:
    """把空白环境变量视为未配置，避免占位符被误判为有效值。"""
    value = source.get(key)
    if value is None:
        return default
    normalized = str(value).strip()
    return normalized or default


def _boolean(source: Mapping[str, str], key: str, default: bool, errors: list[str]) -> bool:
    """仅接受 true/false，禁止 Python 宽松真值导致生产开关误开启。"""
    raw = _text(source, key)
    if raw is None:
        return default
    normalized = raw.lower()
    if normalized == _TRUE:
        return True
    if normalized == _FALSE:
        return False
    errors.append(f"{key} 必须是 true 或 false")
    return default


def _integer(
    source: Mapping[str, str],
    key: str,
    default: int | None,
    errors: list[str],
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int | None:
    """解析有界整数，错误仅报告键名，不回显部署输入。"""
    raw = _text(source, key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        errors.append(f"{key} 必须是整数")
        return default
    if value < minimum or (maximum is not None and value > maximum):
        errors.append(f"{key} 超出允许范围")
        return default
    return value


def _http_url(source: Mapping[str, str], key: str, errors: list[str], default: str | None = None) -> str | None:
    """校验 HTTP(S) 端点；不在错误中拼接可能含凭证的 URL。"""
    value = _text(source, key, default)
    if value is None:
        return None
    parsed = urlparse(value)
    invalid_port = False
    try:
        # urllib 只在访问 port 属性时检查 0～65535，不能仅依赖 urlparse()。
        parsed.port
    except ValueError:
        invalid_port = True
    has_unsafe_character = any(character.isspace() or ord(character) < 32 for character in value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.netloc.endswith(":")
        or invalid_port
        or has_unsafe_character
    ):
        errors.append(f"{key} 必须是不含用户凭证的 HTTP(S) URL")
    return value.rstrip("/")


def _require(condition: bool, keys: tuple[str, ...], errors: list[str]) -> None:
    """按功能开关收集全部缺失项，让部署者一次完成修复。"""
    if condition:
        errors.extend(f"{key} 为当前功能的必填配置" for key in keys)


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """从环境变量构建配置；任何失败都返回不含敏感原值的稳定错误。"""
    source = os.environ if environ is None else environ
    errors: list[str] = []

    app_env = (_text(source, "APP_ENV", "development") or "development").lower()
    if app_env not in {"development", "test", "staging", "production"}:
        errors.append("APP_ENV 必须是 development、test、staging 或 production")
        app_env = "development"
    release_commit = _text(source, "RELEASE_COMMIT")
    release_channel = (
        _text(source, "RELEASE_CHANNEL", "development") or "development"
    ).lower()

    sso_enabled = _boolean(source, "SSO_ENABLED", False, errors)
    persistence_enabled = _boolean(source, "PERSISTENCE_ENABLED", False, errors)
    storage_enabled = _boolean(source, "STORAGE_ENABLED", False, errors)
    billing_enabled = _boolean(source, "BILLING_ENABLED", False, errors)
    task_worker_enabled = _boolean(source, "TASK_WORKER_ENABLED", False, errors)
    session_cookie_secure = _boolean(source, "SESSION_COOKIE_SECURE", False, errors)
    rate_limit_enabled = _boolean(source, "RATE_LIMIT_ENABLED", True, errors)
    audit_log_enabled = _boolean(source, "AUDIT_LOG_ENABLED", True, errors)

    main_api_port = _integer(source, "MAIN_API_PORT", 6800, errors, maximum=65535) or 6800
    outline_api_port = _integer(source, "OUTLINE_API_PORT", 10001, errors, maximum=65535) or 10001
    content_api_port = _integer(source, "CONTENT_API_PORT", 10011, errors, maximum=65535) or 10011
    personaldb_port = _integer(source, "PERSONALDB_PORT", 9100, errors, maximum=65535) or 9100
    frontend_port = _integer(source, "FRONTEND_PORT", 5778, errors, maximum=65535) or 5778

    outline_api = _http_url(
        source, "OUTLINE_API", errors, f"http://127.0.0.1:{outline_api_port}"
    )
    content_api = _http_url(
        source, "CONTENT_API", errors, f"http://127.0.0.1:{content_api_port}"
    )
    personal_db = _http_url(
        source, "PERSONAL_DB", errors, f"http://127.0.0.1:{personaldb_port}"
    )
    app_base_url = _http_url(source, "APP_BASE_URL", errors)
    moling_api_base_url = _http_url(source, "MOLING_API_BASE_URL", errors)
    storage_endpoint = _http_url(source, "STORAGE_ENDPOINT", errors)

    internal_api_token = _text(source, "INTERNAL_API_TOKEN")
    moling_app_id = _integer(source, "MOLING_APP_ID", None, errors)
    moling_product_id = _integer(source, "MOLING_PRODUCT_ID", None, errors)
    # 内部接口区分连接和读取超时，既要快速发现网络故障，也要容纳正常平台处理时间。
    moling_connect_timeout_seconds = (
        _integer(source, "MOLING_CONNECT_TIMEOUT_SECONDS", 3, errors, maximum=300) or 3
    )
    moling_read_timeout_seconds = (
        _integer(source, "MOLING_READ_TIMEOUT_SECONDS", 15, errors, maximum=300) or 15
    )
    session_secret = _text(source, "SESSION_SECRET")
    database_url = _text(source, "DATABASE_URL")
    storage_bucket = _text(source, "STORAGE_BUCKET")
    storage_access_key_id = _text(source, "STORAGE_ACCESS_KEY_ID")
    storage_secret_access_key = _text(source, "STORAGE_SECRET_ACCESS_KEY")
    storage_connect_timeout_seconds = (
        _integer(source, "STORAGE_CONNECT_TIMEOUT_SECONDS", 3, errors, maximum=300) or 3
    )
    storage_read_timeout_seconds = (
        _integer(source, "STORAGE_READ_TIMEOUT_SECONDS", 30, errors, maximum=300) or 30
    )
    storage_max_attempts = (
        _integer(source, "STORAGE_MAX_ATTEMPTS", 3, errors, maximum=10) or 3
    )
    storage_upload_stale_seconds = (
        _integer(source, "STORAGE_UPLOAD_STALE_SECONDS", 900, errors, minimum=60) or 900
    )
    # 可与Session密钥分离轮换；未单独配置时复用已有高熵Session密钥。
    download_signing_secret = _text(source, "DOWNLOAD_SIGNING_SECRET") or session_secret
    download_url_ttl_seconds = (
        _integer(source, "DOWNLOAD_URL_TTL_SECONDS", 300, errors, minimum=30, maximum=3600) or 300
    )
    reserve_points = _integer(source, "PPT_GENERATION_RESERVE_POINTS", None, errors)
    settle_points = _integer(source, "PPT_GENERATION_SETTLE_POINTS", None, errors)
    slide_points = _integer(source, "SLIDE_REGENERATION_POINTS", None, errors)
    session_ttl_seconds = _integer(source, "SESSION_TTL_SECONDS", 86400, errors, minimum=60) or 86400
    session_idle_ttl_seconds = (
        _integer(source, "SESSION_IDLE_TTL_SECONDS", 7200, errors, minimum=60) or 7200
    )
    billing_reconcile_interval_seconds = (
        _integer(source, "BILLING_RECONCILE_INTERVAL_SECONDS", 60, errors, minimum=10) or 60
    )
    # 对账重试必须有硬上限，避免平台持续异常时形成永久写请求风暴。
    billing_reconcile_max_retries = (
        _integer(
            source,
            "BILLING_RECONCILE_MAX_RETRIES",
            8,
            errors,
            minimum=1,
            maximum=100,
        )
        or 8
    )
    presentation_json_max_bytes = (
        _integer(source, "PRESENTATION_JSON_MAX_BYTES", 10 * 1024 * 1024, errors) or 10 * 1024 * 1024
    )
    checkpoint_max_count = _integer(source, "CHECKPOINT_MAX_COUNT", 20, errors) or 20
    checkpoint_inline_max_bytes = (
        _integer(source, "CHECKPOINT_INLINE_MAX_BYTES", 1024 * 1024, errors) or 1024 * 1024
    )
    upload_file_max_bytes = (
        _integer(source, "UPLOAD_FILE_MAX_BYTES", 50 * 1024 * 1024, errors) or 50 * 1024 * 1024
    )
    export_pptx_max_bytes = (
        _integer(source, "EXPORT_PPTX_MAX_BYTES", 100 * 1024 * 1024, errors) or 100 * 1024 * 1024
    )
    thumbnail_max_bytes = (
        _integer(source, "THUMBNAIL_MAX_BYTES", 2 * 1024 * 1024, errors) or 2 * 1024 * 1024
    )
    soft_delete_retention_days = (
        _integer(source, "SOFT_DELETE_RETENTION_DAYS", 30, errors) or 30
    )
    cleanup_interval_seconds = (
        _integer(source, "CLEANUP_INTERVAL_SECONDS", 3600, errors, minimum=60) or 3600
    )
    cleanup_batch_size = _integer(source, "CLEANUP_BATCH_SIZE", 100, errors) or 100
    rate_limit_requests = _integer(source, "RATE_LIMIT_REQUESTS", 30, errors, maximum=10000) or 30
    rate_limit_window_seconds = _integer(source, "RATE_LIMIT_WINDOW_SECONDS", 60, errors, maximum=3600) or 60
    health_probe_timeout_seconds = _integer(source, "HEALTH_PROBE_TIMEOUT_SECONDS", 3, errors, maximum=30) or 3
    user_presentation_limit = _integer(source, "USER_PRESENTATION_LIMIT", None, errors)
    user_storage_quota_bytes = _integer(source, "USER_STORAGE_QUOTA_BYTES", None, errors)

    task_lease_seconds = _integer(source, "TASK_LEASE_SECONDS", 120, errors, minimum=30) or 120
    task_heartbeat_seconds = (
        _integer(source, "TASK_HEARTBEAT_SECONDS", 30, errors, minimum=5) or 30
    )
    task_max_attempts = _integer(source, "TASK_MAX_ATTEMPTS", 3, errors) or 3
    task_retry_backoff_seconds = (
        _integer(source, "TASK_RETRY_BACKOFF_SECONDS", 30, errors, minimum=1) or 30
    )
    task_claim_batch_size = _integer(source, "TASK_CLAIM_BATCH_SIZE", 10, errors) or 10
    task_agent_timeout_seconds = (
        _integer(source, "TASK_AGENT_TIMEOUT_SECONDS", 600, errors, minimum=10) or 600
    )
    task_poll_seconds = _integer(source, "TASK_POLL_SECONDS", 2, errors, minimum=1) or 2
    task_handler_factory = _text(source, "TASK_HANDLER_FACTORY")

    if checkpoint_inline_max_bytes > presentation_json_max_bytes:
        errors.append("CHECKPOINT_INLINE_MAX_BYTES 不能大于 PRESENTATION_JSON_MAX_BYTES")
    if reserve_points is not None and settle_points is not None and settle_points > reserve_points:
        errors.append("PPT_GENERATION_SETTLE_POINTS 不能大于 PPT_GENERATION_RESERVE_POINTS")
    if task_heartbeat_seconds * 2 >= task_lease_seconds:
        errors.append("TASK_HEARTBEAT_SECONDS 必须小于 TASK_LEASE_SECONDS 的一半")
    if session_idle_ttl_seconds >= session_ttl_seconds:
        errors.append("SESSION_IDLE_TTL_SECONDS 必须小于 SESSION_TTL_SECONDS")

    if sso_enabled:
        if not persistence_enabled:
            errors.append("SSO_ENABLED=true 需要 PERSISTENCE_ENABLED=true")
        if database_url is None:
            errors.append("DATABASE_URL 为SSO Session的必填配置")
        missing_sso = tuple(
            key
            for key, value in (
                ("MOLING_API_BASE_URL", moling_api_base_url),
                ("INTERNAL_API_TOKEN", internal_api_token),
                ("MOLING_APP_ID", moling_app_id),
                ("MOLING_PRODUCT_ID", moling_product_id),
                ("SESSION_SECRET", session_secret),
                ("APP_BASE_URL", app_base_url),
            )
            if value is None
        )
        _require(bool(missing_sso), missing_sso, errors)
        if session_secret is not None and len(session_secret) < 32:
            errors.append("SESSION_SECRET 至少需要 32 个字符")
        if app_env == "production" and not session_cookie_secure:
            errors.append("生产 SSO 必须设置 SESSION_COOKIE_SECURE=true")

    if persistence_enabled and database_url is None:
        errors.append("DATABASE_URL 为持久化功能的必填配置")

    if task_worker_enabled:
        if not persistence_enabled:
            errors.append("TASK_WORKER_ENABLED=true 需要 PERSISTENCE_ENABLED=true")
        missing_worker = tuple(
            key
            for key, value in (
                ("DATABASE_URL", database_url),
                ("TASK_HANDLER_FACTORY", task_handler_factory),
            )
            if value is None
        )
        _require(bool(missing_worker), missing_worker, errors)

    if storage_enabled:
        if not persistence_enabled:
            errors.append("STORAGE_ENABLED=true 需要 PERSISTENCE_ENABLED=true")
        missing_storage = tuple(
            key
            for key, value in (
                ("STORAGE_ENDPOINT", storage_endpoint),
                ("STORAGE_BUCKET", storage_bucket),
                ("STORAGE_ACCESS_KEY_ID", storage_access_key_id),
                ("STORAGE_SECRET_ACCESS_KEY", storage_secret_access_key),
                ("USER_PRESENTATION_LIMIT", user_presentation_limit),
                ("USER_STORAGE_QUOTA_BYTES", user_storage_quota_bytes),
                ("DOWNLOAD_SIGNING_SECRET", download_signing_secret),
            )
            if value is None
        )
        _require(bool(missing_storage), missing_storage, errors)
        if download_signing_secret is not None and len(download_signing_secret) < 32:
            errors.append("DOWNLOAD_SIGNING_SECRET 至少需要 32 个字符")

    if billing_enabled:
        if not sso_enabled:
            errors.append("BILLING_ENABLED=true 需要 SSO_ENABLED=true")
        if not persistence_enabled:
            errors.append("BILLING_ENABLED=true 需要 PERSISTENCE_ENABLED=true")
        # API 与独立 Worker 可以使用同一份计费策略但不同进程开关。
        # 生产发布预检会额外验证 Worker profile 确实以 TASK_WORKER_ENABLED=true 启动。
        # 金额由运营配置决定；只有显式开计费时才强制给值，默认始终关闭。
        missing_billing = tuple(
            key
            for key, value in (
                ("PPT_GENERATION_RESERVE_POINTS", reserve_points),
                ("PPT_GENERATION_SETTLE_POINTS", settle_points),
            )
            if value is None
        )
        _require(bool(missing_billing), missing_billing, errors)

    # 生产关键写接口不能处于无限流状态；阈值仍可通过环境变量按运营容量调整。
    if app_env == "production" and not rate_limit_enabled:
        errors.append("生产环境必须设置 RATE_LIMIT_ENABLED=true")
    if app_env == "production":
        # 生产实例必须能回答“当前运行哪个不可变提交”，禁止用分支名或latest代替发布身份。
        if (
            release_commit is None
            or re.fullmatch(r"[0-9a-f]{40}", release_commit) is None
        ):
            errors.append("生产环境必须设置 RELEASE_COMMIT 为40位小写Git提交")
        if release_channel != "production":
            errors.append("生产环境必须设置 RELEASE_CHANNEL=production")

    if errors:
        # 不透传 Pydantic 原始输入，保证令牌、数据库 URL 和存储密钥不进入日志。
        raise ConfigValidationError("配置校验失败：" + "；".join(dict.fromkeys(errors)))

    return Settings(
        app_env=app_env,
        release_commit=release_commit,
        release_channel=release_channel,
        host=_text(source, "HOST", "127.0.0.1") or "127.0.0.1",
        main_api_port=main_api_port,
        outline_api_port=outline_api_port,
        content_api_port=content_api_port,
        personaldb_port=personaldb_port,
        frontend_port=frontend_port,
        outline_api=outline_api or f"http://127.0.0.1:{outline_api_port}",
        content_api=content_api or f"http://127.0.0.1:{content_api_port}",
        personal_db=personal_db or f"http://127.0.0.1:{personaldb_port}",
        app_base_url=app_base_url,
        sso_enabled=sso_enabled,
        persistence_enabled=persistence_enabled,
        storage_enabled=storage_enabled,
        billing_enabled=billing_enabled,
        moling_api_base_url=moling_api_base_url,
        internal_api_token=SecretStr(internal_api_token) if internal_api_token else None,
        moling_app_id=moling_app_id,
        moling_product_id=moling_product_id,
        moling_connect_timeout_seconds=moling_connect_timeout_seconds,
        moling_read_timeout_seconds=moling_read_timeout_seconds,
        session_secret=SecretStr(session_secret) if session_secret else None,
        session_cookie_name=_text(source, "SESSION_COOKIE_NAME", "trainppt_session") or "trainppt_session",
        session_cookie_secure=session_cookie_secure,
        session_ttl_seconds=session_ttl_seconds,
        session_idle_ttl_seconds=session_idle_ttl_seconds,
        database_url=SecretStr(database_url) if database_url else None,
        storage_endpoint=storage_endpoint,
        storage_bucket=storage_bucket,
        storage_access_key_id=SecretStr(storage_access_key_id) if storage_access_key_id else None,
        storage_secret_access_key=SecretStr(storage_secret_access_key) if storage_secret_access_key else None,
        storage_prefix=_text(source, "STORAGE_PREFIX", "trainppt") or "trainppt",
        storage_connect_timeout_seconds=storage_connect_timeout_seconds,
        storage_read_timeout_seconds=storage_read_timeout_seconds,
        storage_max_attempts=storage_max_attempts,
        storage_upload_stale_seconds=storage_upload_stale_seconds,
        download_signing_secret=SecretStr(download_signing_secret) if download_signing_secret else None,
        download_url_ttl_seconds=download_url_ttl_seconds,
        ppt_generation_reserve_points=reserve_points,
        ppt_generation_settle_points=settle_points,
        slide_regeneration_points=slide_points,
        billing_reconcile_interval_seconds=billing_reconcile_interval_seconds,
        billing_reconcile_max_retries=billing_reconcile_max_retries,
        presentation_json_max_bytes=presentation_json_max_bytes,
        checkpoint_max_count=checkpoint_max_count,
        checkpoint_inline_max_bytes=checkpoint_inline_max_bytes,
        upload_file_max_bytes=upload_file_max_bytes,
        export_pptx_max_bytes=export_pptx_max_bytes,
        thumbnail_max_bytes=thumbnail_max_bytes,
        soft_delete_retention_days=soft_delete_retention_days,
        cleanup_interval_seconds=cleanup_interval_seconds,
        cleanup_batch_size=cleanup_batch_size,
        user_presentation_limit=user_presentation_limit,
        user_storage_quota_bytes=user_storage_quota_bytes,
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_requests=rate_limit_requests,
        rate_limit_window_seconds=rate_limit_window_seconds,
        audit_log_enabled=audit_log_enabled,
        health_probe_timeout_seconds=health_probe_timeout_seconds,
        task_lease_seconds=task_lease_seconds,
        task_heartbeat_seconds=task_heartbeat_seconds,
        task_max_attempts=task_max_attempts,
        task_retry_backoff_seconds=task_retry_backoff_seconds,
        task_claim_batch_size=task_claim_batch_size,
        task_worker_enabled=task_worker_enabled,
        task_agent_timeout_seconds=task_agent_timeout_seconds,
        task_poll_seconds=task_poll_seconds,
        task_handler_factory=task_handler_factory,
    )
