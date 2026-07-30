# TrainPPTAgent 正式部署与回滚手册

正式入口为 `https://ppt.axicomin.cn`。本手册对应 BG05，仅定义可审计发布流程；执行生产备份、构建、迁移、部署、服务重启或回滚前，必须分别取得明确授权。

## 1. 安全边界

- 公网/TLS 终止层只转发到宿主机 `127.0.0.1:5778` 的前端 Nginx。
- Main API、Outline、Content、PersonalDB 和 Worker 仅在 Docker 网络中暴露端口。
- `.env` 只保存在服务器，不进入镜像、Git、日志或验收报告。
- `docker-compose.production.yml` 对 Main API 和 Worker 固定覆盖 `BILLING_ENABLED=false`。
- Worker 只通过 `worker` profile 启动；环境文件本身保持 `TASK_WORKER_ENABLED=false`。
- `deploy.sh` 不执行 `git pull/reset/checkout/clean`，不复制开发配置，不删除容器卷。
- 发布必须运行在精确的 40 位 `RELEASE_COMMIT` 上，镜像标签、容器标签、API 健康响应和 Worker 日志必须一致。

## 2. 发布包与生产配置

发布负责人应提前把已验证提交放入独立 release 目录。脚本不会修改仓库状态；目录内任何已跟踪修改都会使预检失败。

生产 `.env` 至少确认：

```dotenv
APP_ENV=production
APP_BASE_URL=https://ppt.axicomin.cn
RELEASE_COMMIT=<40位小写Git提交>
RELEASE_CHANNEL=production
SSO_ENABLED=true
SESSION_COOKIE_SECURE=true
PERSISTENCE_ENABLED=true
STORAGE_ENABLED=true
BILLING_ENABLED=false
TASK_WORKER_ENABLED=false
RATE_LIMIT_ENABLED=true
```

必须填写数据库、对象存储、墨灵应用身份、模型供应商和以下经运营确认的显式值，不能依赖代码默认值：

```dotenv
PRESENTATION_JSON_MAX_BYTES=<已确认值>
UPLOAD_FILE_MAX_BYTES=<已确认值>
EXPORT_PPTX_MAX_BYTES=<已确认值>
USER_PRESENTATION_LIMIT=<已确认值>
USER_STORAGE_QUOTA_BYTES=<已确认值>
RATE_LIMIT_REQUESTS=<已确认值>
RATE_LIMIT_WINDOW_SECONDS=<已确认值>
```

本阶段不要求填写计费金额，也不得开启计费。生产入口、网段和网关仍需核对：

```dotenv
SERVER_NAME=ppt.axicomin.cn
VITE_MOLING_PORTAL_URL=https://moling.axicomin.cn
FRONTEND_BIND_ADDRESS=127.0.0.1
FRONTEND_PORT=5778
TRAINPPT_SUBNET=172.29.23.0/24
TRAINPPT_GATEWAY_IP=172.29.23.1
```

## 3. 只读预检

以下动作不构建、不迁移、不重启服务：

```bash
export RELEASE_COMMIT="$(git rev-parse HEAD)"
export ENV_FILE="/absolute/path/to/.env"
export EXPECTED_DB_VERSION="20260723_0007"
./deploy.sh preflight
```

预检必须证明：

1. 当前 Git HEAD 与 `RELEASE_COMMIT` 完全一致且已跟踪工作区干净。
2. 配置完整、容量值显式、发布通道为 production、计费关闭。
3. Compose 可解析，API 与 Worker 使用同一不可变镜像标签。
4. 生产数据库名正确、迁移版本符合预期、0008 迁移前计费数值 ID 全部合法。
5. 只读事务完成后回滚，不输出数据库 URL、用户名、密码、Token 或业务明细。

## 4. 独立授权动作

### 4.1 备份

获得生产备份授权后执行：

```bash
export CONFIRM="BACKUP-ppt_ai_app-$RELEASE_COMMIT"
export BACKUP_DIR="/secure/offline/trainppt-backups"
./deploy.sh backup
```

记录输出的绝对路径、字节数和 SHA-256。备份文件权限为 `0600`，必须离线留存且禁止提交 Git。

### 4.2 构建

获得生产服务器构建授权后执行：

```bash
export CONFIRM="BUILD-$RELEASE_COMMIT"
./deploy.sh build
```

构建只创建以提交前 12 位命名的镜像，不启动或重建运行容器。当前机器若没有 Docker CLI，不能用 YAML 解析冒充构建通过。

### 4.3 迁移

获得生产迁移授权后，绑定已验证备份：

```bash
export BACKUP_FILE="/secure/offline/trainppt-backups/<backup>.sql"
export BACKUP_SHA256="<上一步SHA-256>"
export CONFIRM="MIGRATE-ppt_ai_app-20260730_0008-$RELEASE_COMMIT"
./deploy.sh migrate
```

脚本先复核 `0007` 和迁移前数据，再升级到 `20260730_0008`，最后只读验证目标列和版本。生产数据库禁止执行 Alembic downgrade。

### 4.4 部署与 Worker 启动

迁移通过并获得部署、重启授权后执行：

```bash
export MIGRATION_VERIFIED="20260730_0008"
export CONFIRM="DEPLOY-$RELEASE_COMMIT-BILLING-OFF"
./deploy.sh deploy
```

该动作更新 API、Agent、PersonalDB、静态前端并显式启动 Worker profile；`BILLING_ENABLED=false` 不可被 `.env` 覆盖。

## 5. 发布验证

```bash
./deploy.sh verify
```

验证项：

1. `/api/healthz` 和 `/api/readyz` 返回与 `RELEASE_COMMIT` 一致的提交和 `production` 通道。
2. `/api/readyz` 的 Outline、Content、PersonalDB、database、storage、moling 全部为 `up`。
3. Worker 日志包含同一提交、production 通道和 `billing_enabled=False`。
4. `/`、`/works` 和合法编辑器深链不包含 Vite/HMR 开发资源，例如 `/@vite/client` 或开发 WebSocket。
5. `/assets/` 使用 immutable 缓存，HTML 使用 `no-store`。
6. Session Cookie 为 `Secure; HttpOnly; SameSite=Lax`，地址栏不保留一次性 ticket。
7. 数据库保持 `20260730_0008`，新增活动计费操作为 0，未处理历史平台持有单。

对账 Worker 的 `billing_reconciliation_snapshot` 日志必须接入现有日志告警：`stale_holds>0` 或 `manual>0` 立即 P1，`errors>0` 持续两个周期触发 P1。`/readyz` 连续 2 分钟非 200 触发 P1；发布后 15 分钟内保持人工观察。

## 6. 回滚

回滚只切换到服务器上已经存在的上一版本镜像，不降级数据库，不删除数据或对象。获得回滚与重启授权后：

```bash
export ROLLBACK_COMMIT="<上一版40位提交>"
export ROLLBACK_IMAGE_TAG="<上一版提交前12位>"
export CONFIRM="ROLLBACK-$RELEASE_COMMIT-TO-$ROLLBACK_COMMIT-BILLING-OFF"
./deploy.sh rollback
```

回滚后重新执行发布验证。若依赖不就绪，不得伪造 `/readyz` 或把实例加入流量；计费始终保持关闭，所有本地幂等记录留待对账。

## 7. Gate C5 证据

Gate C5 只有在以下真实证据全部归档后才能通过：生产备份及摘要、`0007 -> 0008` 迁移结果、镜像/容器/API/Worker 同提交身份、静态前端、六项依赖就绪、监控告警接入、计费关闭、回滚镜像存在且流程可执行。仓库测试、只读预检或脚本就绪都不能单独代表 BG05 完成。
