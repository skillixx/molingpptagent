"""Cookie认证写操作的CSRF来源校验。"""

from __future__ import annotations

from urllib.parse import urlsplit


class CsrfOriginError(RuntimeError):
    """请求没有可信Origin，必须在进入业务写操作前拒绝。"""


def enforce_trusted_origin(origin: str | None, trusted_origins: tuple[str, ...]) -> None:
    """仅允许完整Origin精确匹配；缺失、null、子域或不同端口均拒绝。"""
    if origin is None or origin == "null" or origin not in trusted_origins:
        raise CsrfOriginError("请求来源不可信")


def trusted_origin_from_url(base_url: str) -> str:
    """按浏览器Origin序列化规则移除路径和默认端口，供CSRF精确匹配。"""
    parsed = urlsplit(base_url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if not scheme or not hostname:
        raise ValueError("应用地址无法转换为可信Origin")
    # IPv6 Origin必须保留方括号，避免主机与端口边界产生歧义。
    serialized_host = f"[{hostname}]" if ":" in hostname else hostname
    port = parsed.port
    is_default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    port_suffix = f":{port}" if port is not None and not is_default_port else ""
    return f"{scheme}://{serialized_host}{port_suffix}"


def uvicorn_access_log_enabled(*, sso_enabled: bool) -> bool:
    """SSO开启时禁用可能记录完整query的Uvicorn请求行日志。"""
    return not sso_enabled
