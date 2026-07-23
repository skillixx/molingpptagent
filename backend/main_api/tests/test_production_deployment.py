"""T22 正式静态构建、Nginx与容器边界的仓库契约测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_nginx_serves_history_routes_and_never_targets_vite_or_host_gateway() -> None:
    config = _read("frontend/nginx.conf")
    assert "server_name ${SERVER_NAME};" in config
    assert "proxy_pass http://${MAIN_API_UPSTREAM}" in config
    assert "host.docker.internal" not in config
    assert "/@vite/client" not in config
    assert "vite preview" not in config.lower()
    assert "npm run dev" not in config.lower()
    assert "5173" not in config
    assert "try_files $uri $uri/ /index.html" in config
    assert "location = /index.html" in config
    assert "location ^~ /assets/" in config
    assert "immutable" in config
    assert "no-store" in config


def test_nginx_protects_ticket_and_api_with_proxy_headers_and_rate_limits() -> None:
    config = _read("frontend/nginx.conf")
    assert "location = /enter" in config
    assert "access_log off" in config
    assert "limit_req_zone" in config
    assert "limit_req_status 429" in config
    assert "set_real_ip_from ${TRUSTED_PROXY_IP};" in config
    assert "real_ip_header X-Forwarded-For;" in config
    for header in (
        "X-Real-IP", "X-Forwarded-For", "X-Forwarded-Proto",
        "X-Forwarded-Host", "X-Forwarded-Port",
    ):
        assert f"proxy_set_header {header}" in config
    assert "add_header X-Content-Type-Options nosniff always" in config
    assert "client_max_body_size 110m" in config


def test_production_compose_exposes_only_static_frontend_and_has_no_source_mounts() -> None:
    compose = _read("docker-compose.production.yml")
    assert "dockerfile: backend/main_api/Dockerfile" in compose
    assert "VITE_SSO_ENABLED: \"true\"" in compose
    assert "SESSION_COOKIE_SECURE: \"true\"" in compose
    assert "APP_BASE_URL: https://${SERVER_NAME:-ppt.axicomin.cn}" in compose
    assert "MAIN_API_UPSTREAM: main_api:6800" in compose
    assert "TRUSTED_PROXY_IP: ${TRAINPPT_GATEWAY_IP:-172.29.23.1}" in compose
    assert "subnet: ${TRAINPPT_SUBNET:-172.29.23.0/24}" in compose
    assert "host.docker.internal" not in compose
    assert "volumes:" not in compose
    # 后端只在容器网络expose；唯一宿主机端口映射属于静态Nginx。
    assert compose.count("ports:") == 1
    assert '"${FRONTEND_BIND_ADDRESS:-127.0.0.1}:${FRONTEND_PORT:-5778}:80"' in compose
    frontend_block = compose.split("\n  frontend:\n", 1)[1]
    assert "env_file:" not in frontend_block


def test_images_build_static_assets_and_preserve_python_package_layout() -> None:
    frontend = _read("frontend/Dockerfile")
    backend = _read("backend/main_api/Dockerfile")
    vite = _read("frontend/vite.config.ts")
    assert "npm ci" in frontend and "npm run build" in frontend
    assert "/etc/nginx/templates/default.conf.template" in frontend
    assert "vite preview" not in frontend and "npm run dev" not in frontend
    assert "COPY backend /app/backend" in backend
    assert "WORKDIR /app/backend/main_api" in backend
    assert '"--no-access-log"' in backend
    # 根域history深链必须仍从/assets取资源，不能相对到/editor/assets。
    assert "base: '/'" in vite


def test_production_runbook_requires_https_migrations_and_keeps_billing_off() -> None:
    runbook = _read("README_PRODUCTION.md")
    assert "https://ppt.axicomin.cn" in runbook
    assert "alembic" in runbook.lower()
    assert "BILLING_ENABLED=false" in runbook
    assert "SESSION_COOKIE_SECURE=true" in runbook
    assert "docker compose -f docker-compose.production.yml" in runbook
    assert "Vite" in runbook and "HMR" in runbook


def test_docker_contexts_never_copy_local_secrets_or_generated_dependencies() -> None:
    root_ignore = _read(".dockerignore")
    frontend_ignore = _read("frontend/.dockerignore")
    assert "**/.env" in root_ignore
    assert "frontend/node_modules" in root_ignore
    assert ".env*" in frontend_ignore
    assert "node_modules" in frontend_ignore
