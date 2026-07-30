# TrainPPTAgent BG04 隔离 UAT 实例运行手册

> 适用范围：BG04 Gate C4 的非生产应用实例。本文不授权生产迁移、生产重启、墨灵配置修改或真实积分写入。

## 1. 不可跨越的边界

- 只能使用独立的 `trainppt_uat` 数据库和独立 Docker volume，禁止复用公网生产数据库 URL。
- `APP_ENV=test`，Cookie 名使用 `trainppt_uat_session`，监听端口默认 `15778`。
- 首次启动保持 `UAT_BILLING_ENABLED=false`、`UAT_TASK_WORKER_ENABLED=false`。
- 修改墨灵测试应用 `15` 的 `access_url`、执行真实积分动作、启动计费 Worker 前，分别取得明确授权。
- 已完成的 BG04 应用 UAT 1 积分授权已经用完；后续不得继续真实扣分，也不得把既有授权延续到余额不足或部署场景。

## 2. 准备私有配置

在目标测试服务器把 `env_uat_template.txt` 复制为未跟踪的 `.env.uat`，只在服务器本地填入测试密码、Token、Session 密钥和真实 UAT 地址。检查：

```powershell
git check-ignore .env.uat
Select-String -Path .env.uat -Pattern 'REPLACE_WITH|example\.test'
```

第二条命令必须无结果。确认 `DATABASE_URL` 的主机是 `uat_db`、数据库名以 `_uat` 结尾，并确认没有 `ppt.axicomin.cn` 等生产地址。

## 3. 静态检查与构建

下列命令仍不应启动服务：

```powershell
docker compose --env-file .env.uat -f docker-compose.uat.yml config --quiet
docker compose --env-file .env.uat -f docker-compose.uat.yml build
```

构建完成后先保持两个开关为 `false`。迁移只会作用于 Compose 内新建的 `uat_db`，但执行前仍须核对目标。

## 4. 首次启动顺序

1. 启动独立数据库并确认健康。
2. 执行 `migrate`，确认 `alembic_version=20260730_0008`。
3. 启动 Agent、API 和前端，不启动 `worker` profile。
4. 检查前端代理的 `/api/readyz`、页面身份、数据库名和 Session Cookie 名。
5. 取得授权后，临时把墨灵测试应用 `15` 的入口改到 UAT 地址，重新进入并只读核对 Session 的 `user_id=479`、`app_id=15`、`product_id=73`、`entitlement_id=990306`。

## 5. Worker 与计费门禁

只有入口权益固化和环境身份核对通过后，才进入 Worker 验收。计费场景需要新的积分写入授权；授权前两个开关保持关闭。获批后同时设置：

```text
UAT_BILLING_ENABLED=true
UAT_TASK_WORKER_ENABLED=true
BILLING_ENABLED=true
TASK_WORKER_ENABLED=true
```

然后仅启动 UAT Worker：

```powershell
docker compose --env-file .env.uat -f docker-compose.uat.yml --profile worker up -d task_worker
```

每个任务必须核对 `task_id -> entitlement_id -> hold_id -> reserve/settle/release key`，并确认本轮新增活动持有单归零。达到授权消费上限后立即关闭新计费，但保留对账能力收敛已有持有单。

## 6. 恢复与清理

- 测试完成后先恢复墨灵测试应用原 `access_url`，再停止 UAT 入口。
- 不使用 `docker compose down -v`，除非已导出证据并再次明确批准删除 UAT 数据。
- 生产实例、生产数据库和生产 Compose 不属于本手册操作范围。
