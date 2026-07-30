# TrainPPTAgent 生产预部署验收报告（BG05）

> 状态：准备中，Gate C5 未通过
> 首次只读核验：2026-07-30
> 工作分支：`codex/trainppt-billing-closed-loop`

## 1. 当前生产只读基线

| 项目 | 当前证据 | 结论 |
|---|---|---|
| 正式首页与 `/works` | HTTP 200、`Cache-Control=no-cache`，正文包含 `/@vite/client` | 仍为 Vite 开发态，静态生产前端未部署 |
| `/api/healthz` | HTTP 200 | 只能证明进程存活 |
| `/api/readyz` | HTTP 200，Outline、Content、PersonalDB、database、storage、moling 均为 `up` | 当前后端依赖就绪，但响应尚无不可变发布提交身份 |
| 生产开关 | `BILLING_ENABLED=false`、`TASK_WORKER_ENABLED=false` | 当前不会创建新预占，生产 Worker 尚未启用 |
| 生产数据库 | 数据库 `ppt_ai_app`，Alembic `20260723_0007` | 尚未执行 `20260730_0008` |
| 0008 目标字段 | `app_sessions.entitlement_id` 不存在 | 当前生产 Session 不能固化资产权益 |
| 本地计费操作 | `trainppt_billing_operations` 状态聚合为空，非终态或人工状态为 0 | Worker 启动前没有应用侧历史计费操作需要处理 |
| 生产写入 | 本轮只使用只读事务并回滚 | 未备份、未迁移、未部署、未重启 |

## 2. 仓库预部署加固

- 生产配置新增完整 Git 提交和 production 通道校验，缺失时启动失败。
- `/healthz`、`/readyz` 输出 Main API 组件、发布通道和配置后的完整提交。
- Worker 启动日志输出相同提交、通道和计费关闭状态，不输出凭据。
- Compose 使用提交派生镜像标签，并为 API、Worker、前端添加 OCI revision 标签。
- Main API 增加容器就绪健康检查；Worker profile 固定 `TASK_WORKER_ENABLED=true`，API 与 Worker 均固定 `BILLING_ENABLED=false`。
- 生产静态预检要求运营容量和限流值显式配置，禁止依赖未确认默认值。
- 数据库预检使用只读事务检查版本、0008 目标列、非法旧计费 ID 和未关闭本地计费操作；任一非终态或人工记录都会阻止 Worker 部署。
- 备份工具只接受 MySQL，密码仅通过子进程环境传递，备份使用一致性参数、`0600` 权限和流式 SHA-256。
- `deploy.sh` 拆分为 preflight、backup、build、migrate、deploy、verify、rollback；所有生产动作绑定精确确认文本。
- 旧脚本中的 `git reset --hard`、分支切换、开发配置覆盖和错误 Compose 参数已移除。

## 3. Gate C5 矩阵

| 编号 | 验收项 | 当前状态 | 完成证据 |
|---|---|---|---|
| C5-01 | 精确发布提交与干净 release 目录 | 待生产验证 | Git HEAD、镜像标签、容器标签、API、Worker 五方一致 |
| C5-02 | 生产配置与运营容量值 | 阻塞 | 发布负责人提供七项显式容量/限流值，预检通过 |
| C5-03 | 生产一致性备份 | 未授权 | 备份路径、字节数、SHA-256、离线留存 |
| C5-04 | 迁移前数据审计 | 待授权窗口复核 | `0007`、非法计费 ID 为 0、目标库身份正确 |
| C5-05 | 执行 `0007 -> 0008` | 未授权 | Alembic head 与字段类型只读复核 |
| C5-06 | 构建不可变镜像 | 未授权 | 五个提交标签镜像存在并记录摘要 |
| C5-07 | 部署 API 与静态前端 | 未授权 | 正式域名无 Vite/HMR，API 发布身份正确 |
| C5-08 | 启动 Worker 与对账器 | 未授权 | Worker 同提交、计费关闭、周期快照日志 |
| C5-09 | 监控与告警 | 待接入 | readyz、stale hold、manual、error 阈值真实触发记录 |
| C5-10 | 回滚可执行 | 待验证 | 上一版镜像存在，前向兼容回滚演练或发布负责人确认 |
| C5-11 | 生产计费保持关闭 | 当前通过 | Compose 双重覆盖和生产运行时只读核验 |

## 4. 本地验证证据

```text
python -m pytest backend/main_api/tests -q
335 passed, 1 warning

npm.cmd run test:unit
94 passed

npm.cmd run build
vue-tsc 与 Vite production build 通过

python -m compileall -q backend/main_api
通过

alembic -c alembic.ini heads
20260730_0008 (head)
```

此外，`deploy.sh` 通过 Git for Windows Bash 语法检查，生产 Compose 通过 YAML 结构解析，前端 `dist` 未命中 `/@vite/client`、`__vite_ping`、`vite-hmr` 或开发 WebSocket。当前机器没有 Docker CLI，因此没有执行 `docker compose config`、生产镜像构建或 Nginx 容器校验；这些必须在获批的生产服务器构建步骤补齐。唯一 Python 告警为既有 Starlette/httpx 弃用提示。

## 5. 当前阻塞与恢复顺序

BG05 仍需两类人工输入：

1. 运营确认 `PRESENTATION_JSON_MAX_BYTES`、`UPLOAD_FILE_MAX_BYTES`、`EXPORT_PPTX_MAX_BYTES`、`USER_PRESENTATION_LIMIT`、`USER_STORAGE_QUOTA_BYTES`、`RATE_LIMIT_REQUESTS`、`RATE_LIMIT_WINDOW_SECONDS` 的生产值。
2. 分别授权生产备份、服务器构建、数据库迁移、部署和服务重启；授权不得包含开启计费、真实扣分、处理历史持有单或数据库降级。

恢复后严格执行：更新服务器私有 `.env` -> preflight -> backup -> build -> migrate -> deploy -> verify -> 15 分钟观察。任一步身份不一致、备份摘要失败、迁移数据非法、依赖不就绪或计费开关异常，立即停止后续动作。
