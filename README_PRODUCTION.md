# TrainPPTAgent 正式部署与回滚手册

正式入口为 `https://ppt.axicomin.cn`。前端由 Nginx 提供 Vite 的 `dist` 静态文件，正式域名不得运行 `vite`、`vite preview` 或 HMR WebSocket。本手册只准备部署配置；执行生产迁移、启动容器和切换流量仍需单独授权。

## 1. 拓扑与边界

- 公网/TLS终止层只转发到宿主机 `127.0.0.1:5778` 的前端 Nginx。
- Nginx 精确代理 `/enter`，并把 `/api/*` 去前缀转发到容器网络的 `main_api:6800`。
- main、outline、content、PersonalDB 与可选 Worker 只在 Docker 网络 `expose`，不映射宿主机公网端口。
- `/enter` 关闭访问日志，防止一次性 ticket 落盘；API 与入口都有来源 IP 外层限流，应用仍按 Session owner 限流。
- TLS层必须覆盖 `X-Forwarded-Proto=https`、`X-Forwarded-Host` 和 `X-Forwarded-Port=443`。不要信任公网客户端自行提交这些头。

## 2. 上线前配置

从 `env_template.txt` 复制本地 `.env`，真实密钥只写入该忽略文件，禁止打印或提交。至少确认：

```dotenv
APP_ENV=production
APP_BASE_URL=https://ppt.axicomin.cn
SSO_ENABLED=true
SESSION_COOKIE_SECURE=true
PERSISTENCE_ENABLED=true
STORAGE_ENABLED=true
BILLING_ENABLED=false
RATE_LIMIT_ENABLED=true
```

同时填写数据库、对象存储、墨灵应用身份和模型供应商配置。T23 完成真实积分验收并获得单独放行前，`BILLING_ENABLED=false` 必须保持不变。生产容量值不能直接沿用未确认的 100件/1GiB 默认值。

公开构建变量：

```dotenv
SERVER_NAME=ppt.axicomin.cn
VITE_MOLING_PORTAL_URL=https://moling.axicomin.cn
FRONTEND_BIND_ADDRESS=127.0.0.1
FRONTEND_PORT=5778
TRAINPPT_SUBNET=172.29.23.0/24
TRAINPPT_GATEWAY_IP=172.29.23.1
```

若该私网段与宿主现有网络冲突，必须成对调整 subnet 与 gateway；Nginx 只信任这个固定网关提供的 `X-Forwarded-For`，不得扩大为任意公网地址。

## 3. 只读检查与构建

```powershell
docker compose -f docker-compose.production.yml config --quiet
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml run --rm --no-deps frontend nginx -t
```

检查构建产物不含 Vite/HMR 客户端：

```powershell
rg -n "/@vite/client|__vite_ping|vite-hmr|new WebSocket" frontend/dist
```

该命令应无命中。`dist/index.html`只能引用带hash的`/assets/`文件。

## 4. 迁移与启动（需单独生产授权）

先备份数据库并核对当前 Alembic 版本，再由发布负责人执行：

```powershell
docker compose -f docker-compose.production.yml run --rm --no-deps -w /app main_api alembic -c alembic.ini current
docker compose -f docker-compose.production.yml run --rm --no-deps -w /app main_api alembic -c alembic.ini upgrade head
docker compose -f docker-compose.production.yml up -d
```

只有 `TASK_WORKER_ENABLED=true` 且真实 handler 配置完成时，才显式启动 Worker profile：

```powershell
docker compose -f docker-compose.production.yml --profile worker up -d task_worker
```

## 5. 发布验证

1. `https://ppt.axicomin.cn/api/healthz` 经外层代理可达，`/api/readyz` 的所有必需依赖为 `up`。
2. 直接访问 `/works` 和 `/editor/<合法作品ID>` 返回同一正式 `index.html`，刷新不404。
3. 浏览器 Network 不出现 `/@vite/client`、`__vite_ping`、HMR 或 WebSocket 开发连接。
4. `/assets/` 带 `Cache-Control: public, max-age=31536000, immutable`；HTML带 `no-store`。
5. `/enter?ticket=...` 响应的 Session Cookie 必须为 `Secure; HttpOnly; SameSite=Lax`，且地址栏跳转后不再含ticket。
6. CORS/CSRF只接受 `https://ppt.axicomin.cn`；伪造Origin、跨用户资源和超频写入分别返回稳定403/404/429。
7. 四档 UI、真实墨灵、积分、对象存储与PowerPoint打开由T23分别验收，不能用本地静态服务代替。

## 6. 回滚

- 切回上一版前端镜像和主API镜像；数据库迁移均为向前兼容新增，禁止生产降级删表。
- 保持数据库、exports/files索引和对象存储原件；暂停新归档或Worker，不批量删除用户数据。
- 计费异常立即保持或恢复 `BILLING_ENABLED=false`，保留幂等记录供对账。
- 依赖不就绪时不把实例加入流量；不得修改 `/readyz` 的 required 依赖伪造健康。
- 回滚后复验 `/works`、一个历史编辑深链、只读历史下载和 `/api/readyz`，并记录镜像摘要与时间窗口。
