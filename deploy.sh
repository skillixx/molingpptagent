#!/usr/bin/env bash
set -Eeuo pipefail

# BG05 生产发布入口。每次只执行一个显式动作，不拉代码、不覆盖工作区、不自动跨授权门。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/.release/backups}"
PRODUCTION_URL="${PRODUCTION_URL:-https://ppt.axicomin.cn}"
EXPECTED_DATABASE="${EXPECTED_DATABASE:-ppt_ai_app}"
EXPECTED_DB_VERSION="${EXPECTED_DB_VERSION:-20260723_0007}"
RELEASE_COMMIT="${RELEASE_COMMIT:-}"
TRAINPPT_IMAGE_TAG="${TRAINPPT_IMAGE_TAG:-${RELEASE_COMMIT:0:12}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
COMPOSE_PROJECT="trainpptagent-production"
BILLING_MODE="${BILLING_MODE:-off}"
BILLING_ENABLED="false"
BILLING_LABEL="OFF"

die() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 2
}

require_tool() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"
}

require_confirmation() {
  local expected="$1"
  [[ "${CONFIRM:-}" == "$expected" ]] || die "确认文本不匹配，需要: $expected"
}

validate_release_identity() {
  case "$BILLING_MODE" in
    on)
      BILLING_ENABLED="true"
      BILLING_LABEL="ON"
      ;;
    off)
      BILLING_ENABLED="false"
      BILLING_LABEL="OFF"
      ;;
    *)
      die "BILLING_MODE 必须是 on 或 off"
      ;;
  esac
  [[ "$RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "RELEASE_COMMIT 必须是40位小写Git提交"
  [[ "$TRAINPPT_IMAGE_TAG" == "${RELEASE_COMMIT:0:12}" ]] \
    || die "TRAINPPT_IMAGE_TAG 必须等于 RELEASE_COMMIT 前12位"
  local actual
  actual="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  [[ "$actual" == "$RELEASE_COMMIT" ]] || die "当前工作区提交与 RELEASE_COMMIT 不一致"
  git -C "$ROOT_DIR" diff --quiet || die "工作区存在未提交修改"
  git -C "$ROOT_DIR" diff --cached --quiet || die "暂存区存在未提交修改"
  [[ -f "$ENV_FILE" ]] || die "生产环境文件不存在"
  export RELEASE_COMMIT TRAINPPT_IMAGE_TAG BILLING_ENABLED
}

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -f "$ROOT_DIR/docker-compose.production.yml" \
    -p "$COMPOSE_PROJECT" \
    "$@"
}

run_static_preflight() {
  "$PYTHON_BIN" "$ROOT_DIR/backend/main_api/tools/production_preflight.py" \
    --env-file "$ENV_FILE" \
    --expected-release "$RELEASE_COMMIT" \
    --expected-billing-enabled "$BILLING_ENABLED"
  compose config --quiet
}

run_database_preflight() {
  local version="$1"
  "$PYTHON_BIN" "$ROOT_DIR/backend/main_api/tools/production_preflight.py" \
    --env-file "$ENV_FILE" \
    --expected-release "$RELEASE_COMMIT" \
    --expected-billing-enabled "$BILLING_ENABLED" \
    --expected-db-version "$version"
}

verify_backup_evidence() {
  [[ -n "${BACKUP_FILE:-}" && -f "$BACKUP_FILE" ]] || die "BACKUP_FILE 不存在"
  [[ -n "${BACKUP_SHA256:-}" ]] || die "BACKUP_SHA256 未提供"
  require_tool sha256sum
  local actual
  actual="$(sha256sum "$BACKUP_FILE" | awk '{print $1}')"
  [[ "$actual" == "$BACKUP_SHA256" ]] || die "生产备份 SHA-256 不匹配"
}

verify_release_images() {
  local image
  for image in main-api personaldb outline-api content-api frontend; do
    docker image inspect "trainpptagent-$image:$TRAINPPT_IMAGE_TAG" >/dev/null \
      || die "发布镜像不存在: trainpptagent-$image:$TRAINPPT_IMAGE_TAG"
  done
}

case "$ACTION" in
  preflight)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    run_database_preflight "$EXPECTED_DB_VERSION"
    ;;

  backup)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    require_confirmation "BACKUP-$EXPECTED_DATABASE-$RELEASE_COMMIT"
    "$PYTHON_BIN" "$ROOT_DIR/backend/main_api/tools/production_backup.py" \
      --env-file "$ENV_FILE" \
      --output-dir "$BACKUP_DIR" \
      --expected-database "$EXPECTED_DATABASE" \
      --release-commit "$RELEASE_COMMIT" \
      --confirm "$CONFIRM"
    ;;

  build)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    require_confirmation "BUILD-$RELEASE_COMMIT"
    compose --profile worker build
    ;;

  migrate)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    verify_backup_evidence
    verify_release_images
    run_database_preflight "20260723_0007"
    require_confirmation "MIGRATE-$EXPECTED_DATABASE-20260730_0008-$RELEASE_COMMIT"
    compose run --rm --no-deps -w /app main_api alembic -c alembic.ini upgrade 20260730_0008
    run_database_preflight "20260730_0008"
    ;;

  deploy)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    verify_release_images
    [[ "${MIGRATION_VERIFIED:-}" == "20260730_0008" ]] || die "缺少迁移完成证据"
    run_database_preflight "20260730_0008"
    require_confirmation "DEPLOY-$RELEASE_COMMIT-BILLING-$BILLING_LABEL"
    compose up -d --no-build personaldb outline_api content_api main_api frontend
    compose --profile worker up -d --no-build task_worker
    ;;

  verify)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    run_static_preflight
    verify_release_images
    run_database_preflight "20260730_0008"
    "$PYTHON_BIN" - "$PRODUCTION_URL" "$RELEASE_COMMIT" <<'PY'
import json
import sys
from urllib.request import urlopen

base_url, expected_commit = sys.argv[1:]
for endpoint in ("/api/healthz", "/api/readyz"):
    with urlopen(base_url.rstrip("/") + endpoint, timeout=10) as response:
        payload = json.load(response)
    if payload.get("release_commit") != expected_commit:
        raise SystemExit(f"发布身份不匹配: {endpoint}")
    if payload.get("release_channel") != "production":
        raise SystemExit(f"发布通道不匹配: {endpoint}")
print(json.dumps({"verified": True, "release_commit": expected_commit}))
PY
    compose ps
    expected_log_value="False"
    [[ "$BILLING_ENABLED" == "true" ]] && expected_log_value="True"
    compose --profile worker logs --no-color --tail=200 task_worker \
      | grep -F "release=$RELEASE_COMMIT channel=production billing_enabled=$expected_log_value" >/dev/null \
      || die "Worker 发布身份或计费关闭日志缺失"
    ;;

  rollback)
    require_tool git
    require_tool docker
    require_tool "$PYTHON_BIN"
    validate_release_identity
    [[ "${ROLLBACK_COMMIT:-}" =~ ^[0-9a-f]{40}$ ]] || die "ROLLBACK_COMMIT 无效"
    [[ "${ROLLBACK_IMAGE_TAG:-}" =~ ^[0-9a-f]{12}$ ]] || die "ROLLBACK_IMAGE_TAG 无效"
    require_confirmation "ROLLBACK-$RELEASE_COMMIT-TO-$ROLLBACK_COMMIT-BILLING-OFF"
    # 回滚只允许关闭计费，避免旧镜像继续接收新的真实扣分任务。
    export BILLING_ENABLED="false"
    for image in main-api personaldb outline-api content-api frontend; do
      docker image inspect "trainpptagent-$image:$ROLLBACK_IMAGE_TAG" >/dev/null \
        || die "回滚镜像不存在: trainpptagent-$image:$ROLLBACK_IMAGE_TAG"
    done
    export RELEASE_COMMIT="$ROLLBACK_COMMIT"
    export TRAINPPT_IMAGE_TAG="$ROLLBACK_IMAGE_TAG"
    # 数据库迁移保持向前兼容版本，不执行生产 downgrade。
    compose up -d --no-build personaldb outline_api content_api main_api frontend
    compose --profile worker up -d --no-build task_worker
    ;;

  *)
    cat <<'USAGE'
用法: ./deploy.sh <preflight|backup|build|migrate|deploy|verify|rollback>

所有动作都要求 RELEASE_COMMIT、ENV_FILE；写动作还要求对应 CONFIRM。
脚本不会拉取代码、切换分支、覆盖配置、删除卷或开启生产计费。
USAGE
    exit 2
    ;;
esac
