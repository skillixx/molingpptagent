# TrainPPTAgent 积分迁移与配置隔离演练报告 BG02

> 演练日期：2026-07-30
> 演练结论：通过
> 证据等级：本地自动化测试 + 本机临时 MariaDB 真实方言演练
> 生产影响：无

## 1. 环境

| 项目 | 结果 |
|---|---|
| 数据库 | MariaDB 11.8.8 Windows x86_64 便携版 |
| 来源 | MariaDB Foundation 官方 Downloads REST API |
| ZIP SHA-256 | `20871a79964e1819ddaad9247b676b9d08c958c345e5e3d4748242b2b2965ff1` |
| 网络边界 | 仅监听 `127.0.0.1:33307` |
| Windows 服务 | 未安装、未注册 |
| 隔离 schema | `trainppt_bg02`、`trainppt_bg02_invalid` |
| 生产数据库 | 未连接、未读取、未写入 |
| 临时进程 | PID `78296` 已停止，端口确认无监听 |

官方参考：

- [MariaDB Downloads REST API](https://mariadb.org/downloads-rest-api/)
- [Installing MariaDB Windows ZIP Packages](https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/installing-mariadb/binary-packages/installing-mariadb-windows-zip-packages)

## 2. 迁移往返

在 `trainppt_bg02` 中写入合法历史字符串 `entitlement_id=990306`、`hold_id=51` 后执行：

```text
20260723_0007
  -> 20260730_0008
  -> 20260723_0007
  -> 20260730_0008
```

结果：

| 检查点 | `app_sessions.entitlement_id` | 计费字段类型 | 样本值 |
|---|---|---|---|
| `0007` | 不存在 | `varchar` | `990306`、`51` |
| 第一次 `0008` | `bigint` | `bigint` | `990306`、`51` |
| 降级 `0007` | 不存在 | `varchar` | `990306`、`51` |
| 第二次 `0008` | `bigint` | `bigint` | `990306`、`51` |

最终 Alembic 版本为 `20260730_0008 (head)`。合法标识无截断、置零或变化。

## 3. 非法值拦截

在独立 schema `trainppt_bg02_invalid` 中逐项注入以下 `hold_id`：

| 类别 | 结果 | 拦截后版本 | 新字段是否出现 |
|---|---|---|---|
| 文本 | DDL 前阻止升级 | `20260723_0007` | 否 |
| 零 | DDL 前阻止升级 | `20260723_0007` | 否 |
| 负数 | DDL 前阻止升级 | `20260723_0007` | 否 |
| 超过 `9223372036854775807` | DDL 前阻止升级 | `20260723_0007` | 否 |
| 非 ASCII 全角数字 | DDL 前阻止升级 | `20260723_0007` | 否 |

把非法值恢复为 `51` 后，同一 schema 可正常升级到 `0008`。错误输出只报告非法值数量，不输出业务行明细。

## 4. 配置 fail-closed

审计发现 `PPT_GENERATION_RESERVE_POINTS` 和 `PPT_GENERATION_SETTLE_POINTS` 的必填校验被错误放在“生产关闭限流”分支中。BG02 已将它们移动到 `BILLING_ENABLED=true` 分支，并新增逐项缺失测试。

以下任一配置缺失都会触发 `ConfigValidationError`：

- SSO、持久化、任务 Worker 开关；
- 数据库 URL、Worker Handler；
- 墨灵地址、内部 Token、应用 ID、商品 ID；
- Session 密钥、应用地址；
- 预占积分、结算积分。

错误消息只包含配置键名，不回显 Token、数据库 URL 或配置原值。

## 5. 自动化证据

```text
专项：test_config.py + test_db_and_migrations.py
结果：56 passed

主 API 全量：backend/main_api/tests
结果：304 passed, 1 warning
```

唯一警告为既有 Starlette `httpx` TestClient 弃用提醒，与本次计费迁移无关。

## 6. 安全与遗留事项

- 未执行生产迁移、部署、服务重启、真实扣分或历史补偿；
- 未修改墨灵仓库；
- 临时 MariaDB 进程已停止，端口无监听；
- 安全策略拒绝了递归删除命令，因此便携包和隔离数据仍位于系统 Temp 的 `codex-bg02-mariadb-11.8.8` 目录，不在 Git 工作区；
- 生产数据库降级会删除 Session 权益绑定字段，仍须单独审批，不能由自动流程执行。

## 7. Gate C2 结论

C2 通过：SQLite 自动化与 MariaDB 真实方言往返均成功；合法值无损；五类非法值在 DDL 前被阻止；计费运行依赖已 fail closed；演练过程没有生产影响或秘密入库。
