# TrainPPTAgent 持久任务租约与容量基线

> 状态：`FROZEN_FOR_M0`
> 对应任务：T02
> 适用范围：TrainPPTAgent 墨灵对接第一期
> 生产约束：用户级作品数和存储总量未确认前，不得通过 G5

## 1. 目的与边界

本文冻结 B-01 的租约执行模型和 B-04 的容量设计。T02 只建立配置、迁移和设计基线，不提前实现 T06 的业务表、T08 的 Worker、T14 的检查点服务或 T19/T20 的对象存储与文件接口。

## 2. 容量配置

| 对象 | 配置键 | 第一版默认值 | 计量与处理 |
|---|---|---:|---|
| 当前作品 JSON | `PRESENTATION_JSON_MAX_BYTES` | 10 MiB | 按 UTF-8 序列化后的请求字节计量；超限拒绝保存 |
| 检查点数量 | `CHECKPOINT_MAX_COUNT` | 20 | 只保留最近版本；清理不得删除当前作品 |
| 数据库内联检查点 | `CHECKPOINT_INLINE_MAX_BYTES` | 1 MiB | 压缩后不超过阈值才进入 MySQL；更大对象转存 Storage Adapter |
| 单个依据文件 | `UPLOAD_FILE_MAX_BYTES` | 50 MiB | 流式读取期间计量，超过阈值立即中止 |
| 单个 PPTX | `EXPORT_PPTX_MAX_BYTES` | 100 MiB | 浏览器 Blob 与归档对象使用同一字节和哈希 |
| 单个缩略图 | `THUMBNAIL_MAX_BYTES` | 2 MiB | 只接受后续文件协议允许的图片格式 |
| 软删除保留 | `SOFT_DELETE_RETENTION_DAYS` | 30 天 | 删除后立即不可见，到期后才进入物理清理候选集 |
| 清理周期/批次 | `CLEANUP_INTERVAL_SECONDS` / `CLEANUP_BATCH_SIZE` | 3600 秒 / 100 | 小批量、可重试、记录审计，不进行无界扫描 |
| 用户作品数 | `USER_PRESENTATION_LIMIT` | 非生产100件 | O-09可逆默认；生产值须在T23确认 |
| 用户存储量 | `USER_STORAGE_QUOTA_BYTES` | 非生产1GiB | 上传中、删除中和软删除未物理清理对象均计入，生产值须在T23确认 |

配置中的 `0` 不表示无限，非法值会阻止启动。仓库模板采用100件/1GiB非生产默认；`STORAGE_ENABLED=true`时两个值均为必填，生产发布仍必须按运营容量重新确认。T19已以单条条件更新原子占额，避免SQLite忽略`FOR UPDATE`或MySQL并发时双重通过。

## 3. 超限与清理规则

1. 当前作品 JSON 超限返回 HTTP 413，稳定错误码 `PRESENTATION_DOCUMENT_TOO_LARGE`，保留原版本不覆盖。
2. 上传、PPTX、缩略图分别使用 `UPLOAD_TOO_LARGE`、`EXPORT_TOO_LARGE`、`THUMBNAIL_TOO_LARGE`；不能先完整读入内存后再判断。
3. 用户作品数或存储量超限返回 HTTP 409 和 `USER_QUOTA_EXCEEDED`；配额检查与创建/占额必须在同一事务或等价原子操作中完成。
4. 检查点超过 20 个时，从最旧的非保护检查点开始清理；恢复操作先创建新版本，再异步清理旧版本。
5. 大检查点在对象存储未启用时返回 `CHECKPOINT_STORAGE_UNAVAILABLE`，禁止回退为无限写入 MySQL。
6. 物理清理先锁定候选记录并写审计，再删除对象，最后标记或删除数据库索引；任何一步失败都保留可重试状态，不批量忽略错误。

T14已将内联检查点冻结为规范JSON的确定性gzip，并以`gzip+base64-v1`自描述信封写入既有LONGTEXT；读取限制压缩体和最大10MiB解压输出，防止压缩炸弹。T19前没有可用Storage Adapter，因此压缩后超过1MiB即稳定返回`CHECKPOINT_STORAGE_UNAVAILABLE`。检查点创建或恢复先提交新版本，再以独立事务清理最旧记录至最近20个；清理失败保留新版本并记录不含正文和原始作品ID的错误。

按默认上限估算，单作品在 MySQL 中最多约为 10 MiB 当前稿加 20 MiB 内联检查点，即约 30 MiB（不含索引和行开销）；更大的历史版本转对象存储并计入1GiB非生产用户占额。该数字只用于开发/契约验证，不是生产容量承诺。

## 4. T19对象占额与恢复

- `owner_storage_usage`以owner为主键保存`used_bytes/file_count`；0006迁移会把既有`uploading/active`文件回填，防止升级后从零计费。
- 文件先在数据库原子占额并落`uploading`，对象SHA-256/大小验证后才转`active`。平台失败只有在同键删除成功后才释放；删除结果未知保留状态和占额。
- 陈旧上传先条件认领为`recovering_upload`，与原上传者的`activate`互斥；陈旧未引用检查点由`active→deleting`认领。`deleting`可在重启后幂等重删并释放，期间出现版本引用则恢复`active`。
- 同作品、用途、MIME、大小和SHA-256一致时复用对象；复用会条件刷新租约，若GC已抢占则返回可重试状态，不能从ORM缓存返回伪`active`。
- 大检查点使用`storage-gzip-v1`文件引用，读取仍执行10MiB受限解压；版本裁剪后引用感知GC只删除无任何版本信封引用的陈旧对象。
- S3兼容适配器显式配置连接/读取超时与有限重试；服务端生成对象键，不接受文件名或路径；读取先核对声明大小再受限读取并复验SHA-256。

## 5. MySQL 租约 Worker

| 配置键 | 默认值 | 语义 |
|---|---:|---|
| `TASK_LEASE_SECONDS` | 120 | Worker 独占任务的租期 |
| `TASK_HEARTBEAT_SECONDS` | 30 | 续租周期，必须小于租期的一半 |
| `TASK_MAX_ATTEMPTS` | 3 | 包含首次执行的最大尝试次数 |
| `TASK_RETRY_BACKOFF_SECONDS` | 30 | 首次重试退避基数，后续可指数增加并设上限 |
| `TASK_CLAIM_BATCH_SIZE` | 10 | 单次事务最多领取数，避免长事务 |

T06 的任务表至少包含 `status`、`attempt`、`next_attempt_at`、`locked_by`、`lock_token`、`locked_until`、`heartbeat_at`、`last_error_code` 和时间戳。业务请求幂等键与任务 ID 分离，唯一约束在对应任务落地。

### 4.1 领取与执行

1. MySQL 8 使用短事务 `SELECT ... FOR UPDATE SKIP LOCKED` 选取 `pending` 且到期的任务，再写入随机 `lock_token`、Worker ID 和租期。
2. 不支持 `SKIP LOCKED` 时使用带 `status`、`next_attempt_at` 和租期条件的原子更新；受影响行数不是 1 即领取失败。
3. Agent 调用在领取事务提交后执行，数据库事务不得跨网络请求。
4. 心跳、成功和失败更新都必须同时匹配 `task_id + lock_token + running`；租约丢失的旧 Worker 禁止提交终态。

### 4.2 崩溃恢复、重试与幂等

1. `locked_until` 过期的 `running` 任务由回收器重新入队；达到最大尝试次数后进入 `failed`/死信状态，禁止无限重试。
2. 每次尝试保存稳定的任务请求 ID。下游支持幂等时复用同一业务键；不支持时必须先检查已持久化产物，不能仅凭客户端断线重复调用 Agent。
3. 第一版执行语义是“至少一次领取 + 带栅栏终态写入”，不宣称外部 Agent 调用严格一次。T08 必须用崩溃点测试证明不会形成两个有效终态。
4. T16 计费使用独立可复算幂等键；Worker 重试不得生成新的 reserve/settle/release 业务键。

## 6. 当前 MySQL 基线与迁移规则

- 2026-07-23 对现有配置执行只读 `SELECT 1` 和 `SELECT VERSION()`：MySQL 8.0.46，支持 `SKIP LOCKED`。
- T02 未对现有 MySQL 执行 Alembic、建表、写入或删除；空库迁移重复性使用隔离的 SQLite 测试库验证。
- Alembic 第一版只向前新增。应用二进制回滚不自动执行生产 `downgrade`，数据库对象和用户数据继续保留。
- 迁移与连接异常只能返回稳定脱敏错误；禁止在日志、测试报告或命令行输出完整 `DATABASE_URL`。

## 7. 后续关闭条件

- B-01：T06 落地任务表和原子领取，T08 完成心跳、崩溃恢复、重复领取、最大重试和死信测试后才能关闭。
- B-04：T14 完成检查点计量与清理，T19 完成用户配额、对象占额和并发超限测试后才能关闭。
- O-09：生产发布前必须给出用户作品数和存储字节上限；未确认时只能保持非生产范围。

## 8. 回滚

关闭 `PERSISTENCE_ENABLED` 可阻止新持久化流量。应用回滚不自动降级数据库；迁移故障停止后续写入并保留现有表、版本号和对象索引，由人工按迁移证据处理，禁止自动删表或批量删对象。
