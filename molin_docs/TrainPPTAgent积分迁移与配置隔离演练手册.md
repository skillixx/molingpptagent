# TrainPPTAgent 积分迁移与配置隔离演练手册

> 适用阶段：BG02
> 目标版本：`20260730_0008`
> 安全边界：只允许使用一次性隔离数据库；禁止把生产库 URL 直接用于本手册命令

## 1. 演练目标

演练必须证明：

1. `20260723_0007 -> 20260730_0008` 能把历史数字字符串无损转换为 `BIGINT`；
2. `20260730_0008 -> 20260723_0007 -> 20260730_0008` 往返后标识和值保持一致；
3. 非 ASCII 数字、文本、零、负数和超过有符号 `BIGINT` 上限的值会阻止升级；
4. `app_sessions.entitlement_id` 只在 `0008` 及以后存在；
5. 计费依赖不完整时，应用在监听端口前 fail closed；
6. 命令输出不包含数据库 URL、密码、内部 Token 或完整业务明细。

SQLite 自动化只验证迁移逻辑，不代替 MySQL/MariaDB 同类型隔离演练。

## 2. 隔离环境门禁

开始前逐项确认：

- 数据库是临时实例或经批准的脱敏副本，不是生产实例；
- 使用独立数据库账号，权限只覆盖隔离 schema；
- 已记录隔离实例负责人、销毁时间和备份位置；
- 当前 `BILLING_ENABLED=false`，应用流量不会连接该隔离库；
- `ALEMBIC_DATABASE_URL` 由安全环境注入，不写入仓库、命令历史或报告；
- 备份文件不进入 Git，演练结束后按环境规范销毁。

无法证明数据库隔离时，停止演练，不得用生产库“只试一次”。

## 3. 自动化基线

在仓库根目录执行：

```powershell
& '.\.venv312\Scripts\python.exe' -m pytest `
  backend/main_api/tests/test_config.py `
  backend/main_api/tests/test_db_and_migrations.py -q
```

该测试包含 SQLite 隔离库的 `0007 -> 0008 -> 0007 -> 0008` 往返、合法值保留和非法值拦截。

## 4. MySQL/MariaDB 隔离演练

### 4.1 建立备份

以下命令中的主机、用户和库名由运维在安全终端填写。`--password` 不携带值，让客户端交互读取密码：

```powershell
mysqldump --single-transaction --routines --triggers `
  --host <隔离数据库主机> --user <隔离账号> --password `
  <隔离数据库名> > trainppt-bg02-before.sql
```

记录备份文件哈希，不把备份加入 Git：

```powershell
Get-FileHash .\trainppt-bg02-before.sql -Algorithm SHA256
```

### 4.2 确认当前版本

```powershell
& '.\.venv312\Scripts\python.exe' -m alembic current
& '.\.venv312\Scripts\python.exe' -m alembic history
```

开始往返前，隔离库必须处于 `20260723_0007`。若版本不同，先停止并核对副本来源。

### 4.3 执行升级、降级和再次升级

```powershell
& '.\.venv312\Scripts\python.exe' -m alembic upgrade 20260730_0008
& '.\.venv312\Scripts\python.exe' -m alembic downgrade 20260723_0007
& '.\.venv312\Scripts\python.exe' -m alembic upgrade 20260730_0008
& '.\.venv312\Scripts\python.exe' -m alembic current
```

每一步都必须保存：退出码、Alembic 起止版本、字段类型、合法样本前后值和非法样本拦截结果。报告只记录计数与脱敏样本编号。

### 4.4 结构核对

在隔离库执行：

```sql
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
    (TABLE_NAME = 'app_sessions' AND COLUMN_NAME = 'entitlement_id')
    OR
    (TABLE_NAME = 'trainppt_billing_operations'
      AND COLUMN_NAME IN ('entitlement_id', 'hold_id'))
  )
ORDER BY TABLE_NAME, COLUMN_NAME;
```

`0008` 的三个字段必须是可空 `BIGINT`。不得在报告中导出完整会话或计费业务行。

## 5. 配置 fail-closed 演练

自动化会逐项移除以下配置并断言启动校验失败：

- `SSO_ENABLED`、`PERSISTENCE_ENABLED`、`TASK_WORKER_ENABLED`；
- `DATABASE_URL`、`TASK_HANDLER_FACTORY`；
- `MOLING_API_BASE_URL`、`INTERNAL_API_TOKEN`、`MOLING_APP_ID`、`MOLING_PRODUCT_ID`；
- `SESSION_SECRET`、`APP_BASE_URL`；
- `PPT_GENERATION_RESERVE_POINTS`、`PPT_GENERATION_SETTLE_POINTS`。

错误只允许包含配置键名，不得回显配置值。

## 6. 回滚与停止条件

出现以下任一情况立即停止：

- 隔离库身份无法确认；
- 非法历史值被静默转换；
- 合法 `entitlement_id` 或 `hold_id` 前后不一致；
- 降级后仍残留 `app_sessions.entitlement_id`；
- 再次升级失败；
- 日志或报告出现秘密、数据库 URL 或完整业务明细。

应用回滚时先保持 `BILLING_ENABLED=false`，再回退应用代码。数据库降级会删除 Session 中新增的权益绑定字段，生产环境不得自动执行；必须先确认没有新会话和活动计费操作，并取得生产变更授权。

## 7. 演练记录模板

```text
环境标识：
数据库类型和版本：
隔离责任人：
备份哈希：
初始 Alembic 版本：
第一次升级结果：
降级结果：
第二次升级结果：
合法值核对：
非法值拦截：
配置 fail-closed：
秘密扫描：
遗留风险：
结论：通过 / 不通过
```
