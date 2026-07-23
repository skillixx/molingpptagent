# TrainPPTAgent 对接墨灵平台全阶段开发规划

> 文档状态：DRAFT，待用户确认后作为开发排期基线
> 编写日期：2026-07-22
> 适用项目：`D:\molinggithub\TrainPPTAgent`
> 交付边界：本文件只进行需求规划，不开发业务代码，不修改墨灵平台与 `D:\molingproject\molinppt`
> Goal 开发入口：[TrainPPTAgent 墨灵对接 Goal 开发执行主文档](./TrainPPTAgent墨灵对接Goal开发执行主文档.md)

## 1. 结论摘要

墨灵平台侧已经具备应用接入条件，当前阻塞点全部集中在 TrainPPTAgent 应用侧。项目不能只依靠反向代理完成接入，还需要补齐可信身份、服务端数据持久化、用户隔离、积分计费、对象存储、生产部署和验收闭环。

建议采用九个阶段交付：

| 阶段 | 名称 | 核心结果 | 优先级 | 估算 |
|---|---|---|---|---:|
| M0 | 基线冻结与技术准备 | 当前能力、配置、数据库和部署基线可重复验证 | P0 | 1～2 人日 |
| M1 | 墨灵 SSO 与应用 Session | 用户从墨灵点击进入后自动登录 TrainPPTAgent | P0 | 3～4 人日 |
| M2 | 业务数据、用户隔离与任务执行基线 | 作品、版本、任务、文件拥有可信所有者，生成任务可持久执行和恢复 | P0 | 6～8 人日 |
| M3 | 我的作品与历史打开 | 用户能找到、打开和管理历史 PPT | P0 | 4～5 人日 |
| M4 | 二次编辑与可靠保存 | 自动保存、手动保存、版本冲突和另存副本可用 | P0 | 5～6 人日 |
| M5 | 生成任务与积分计费 | reserve、settle、release 和异常对账形成闭环 | P0 | 6～8 人日 |
| M6 | 对象存储与导出归档 | PPTX、缩略图和上传文件可安全保存与下载 | P0 | 4～5 人日 |
| M7 | 可恢复性、安全与运维 | 中断恢复、审计、监控、限流和后台对账可用 | P0 | 3～4 人日 |
| M8 | 生产发布与真实验收 | 正式域名、HTTPS、真实积分与多用户验收通过 | P0 | 4～5 人日 |
| **总计** |  |  |  | **36～47 人日** |

单人串行开发预计 8～10 周；两名前后端开发在 M1、M2 完成后并行推进，预计 5～7 周，不包含外部审批和运营规则确认等待时间。估算只有在下述开发阻塞项全部关闭后才能作为排期承诺。

## 2. 已核实的当前状态

核实日期：2026-07-22。以下结论同时来自代码检查和真实墨灵测试环境联调。

### 2.1 墨灵平台侧

| 检查项 | 结果 | 结论 |
|---|---|---|
| 用户控制台 | 登录成功 | 测试账号可进入商品市场 |
| PPT 商品 | 商品 ID `73`，状态已上架 | 商品配置存在 |
| 绑定应用 | 应用 ID `15` | 商品和应用关联正确 |
| 应用入口 | `https://ppt.axicomin.cn/enter?ticket=...` | 平台可以签发一次性启动票据并跳转 |
| 平台健康检查 | HTTP 200 | 平台 API 可用 |
| 票据验证 | 返回 `code=0` 及匹配的 app/product 信息 | `INTERNAL_API_TOKEN`、网络和 verify 契约可用 |
| 用户权益 | 查询到多条 active、usable 的 PPT 积分权益 | prepaid 计费具备联调数据 |

平台侧目前不需要重新创建应用或商品。后续只有在入口地址、积分单价、套餐或 IP 白名单发生变化时，才需要平台管理员配合。

### 2.2 TrainPPTAgent 应用侧

| 模块 | 已有能力 | 当前缺口 | 代码证据 |
|---|---|---|---|
| 前端路由 | `/`、`/editor`、`/ppt`、`/app/:id?` | 没有 `/enter`、`/works`、作品详情和任务恢复页 | `frontend/src/router/index.ts:4-23` |
| 主 API | 大纲、内容、模板、文件列表、代理、健康检查 | 没有 SSO、Session、作品 CRUD、任务和计费接口 | `backend/main_api/main.py:60-381` |
| 用户标识 | 请求可以传 `user_id` 或随机 `sessionId` | 服务端没有证明该 ID 属于当前访问者 | `backend/main_api/main.py:67-103, 205-217, 312-318` |
| 前端编辑状态 | Pinia 保存当前幻灯片 | 刷新或换设备后没有服务端作品可恢复 | `frontend/src/store/slides.ts` |
| 本地快照 | Dexie/IndexedDB 保存撤销快照 | 数据库超过 12 小时会清理，不能作为历史作品库 | `frontend/src/utils/database.ts:17-53` |
| PPTX 导出 | 浏览器通过 PptxGenJS 生成并下载 | 文件没有归档、归属和重复下载能力 | `frontend/src/hooks/useExport.ts:445-958` |
| CORS | 当前允许任意来源 | 生产环境需要域名白名单 | `backend/main_api/main.py:36-44` |
| 部署 | 五个服务和 5778 前端端口可运行 | 当前域名代理 Vite 开发服务，HMR WebSocket 报错 | `frontend/vite.config.ts:12-22` |
| 业务数据库 | `.env` 已配置 MySQL 连接 | 代码没有 ORM、迁移和业务表 | `backend/main_api/requirements.txt` |
| 对象存储 | `.env` 已配置 endpoint、bucket 和凭证 | 代码没有对象存储适配层 | 当前环境配置检查 |
| 配置模板 | 模型与 Agent 配置已有模板 | 墨灵、Session、数据库、存储和计费配置未写入模板 | `env_template.txt` |

### 2.3 当前线上可见故障

1. 用户从墨灵点击“进入应用”后能打开新标签页，但 `/enter` 没有匹配路由，页面为空白。
2. `ppt.axicomin.cn` 当前返回 Vite 开发客户端，WebSocket 连接错误；反向代理只解决了 HTTP 页面访问，没有形成生产部署。
3. 应用没有消费启动票据、建立会话或读取真实墨灵用户，因此即使首页可见，也不能保证多用户数据安全。

### 2.4 开发阻塞项

以下问题不是普通优化项。任一项没有形成明确契约和验收结果时，不得宣称需求已经达到“开发拿走即可执行”的状态。

| 编号 | 严重问题 | 当前证据 | 直接影响 | 解除阻塞要求 |
|---|---|---|---|---|
| B-01 | 只有任务数据表和状态机，没有持久任务执行器 | 当前 `docker-compose.yml` 没有 Worker/队列服务，规划只描述 `generation_tasks` | API 或 Agent 重启后任务可能永久停在 `running`，并可能重复生成、重复结算 | M0 确定 DB 租约 Worker 或消息队列方案；定义领取、续租、超时、重试、死信和重启恢复；M2 完成最小可用执行器 |
| B-02 | M3/M5 阶段依赖倒置 | M3 要求创建 `generation_task`，旧稿到 M5 才实现持久任务和幂等 | M3 开发时无法决定同步生成、异步生成、失败恢复和任务状态来源 | 将非计费任务基础移到 M2；M3 只消费已稳定的任务框架；M5 在其外层增加权益和计费，不重新设计任务生命周期 |
| B-03 | API 只有路径清单，没有请求/响应契约 | 当前 API 规划未给出 JSON Schema、分页、错误体、SSE 事件和上传协议 | 前后端会分别补设计，联调时出现字段、状态码和重试语义冲突 | 开发接口前冻结 OpenAPI；明确每个接口的请求、响应、错误码、幂等头、分页、权限和示例 |
| B-04 | 版本与文件容量缺少上限模型 | 单作品允许 `slides_json ≤ 10 MiB`，默认保留 20 个完整检查点，作品又默认长期保留 | 单个作品理论上仅 JSON 就可达到约 210 MiB，数据库和备份成本无法控制 | M0 完成容量测算；确定版本压缩/增量/对象存储方案、用户配额、超限错误、清理周期和恢复策略 |
| B-05 | SSO、Cookie 和状态修改接口的安全契约不完整 | 已选择 HttpOnly Cookie，但未定义 Session TTL、轮换、CSRF、Cookie Scope 和票据日志处理 | 票据可能进入访问日志或 Referrer；会话可能被固定或跨站滥用 | M1 明确绝对/空闲过期、登录轮换、Cookie 名称与作用域、Origin/CSRF 校验、`no-store`、`no-referrer` 和 Nginx 查询参数脱敏 |
| B-06 | 上传文件与知识库能力被当成稳定基线，但尚未完成真实验收 | PersonalDB 依赖文件转换和 Embedding；主 API 仍信任客户端 `user_id`；此前出现文件转换失败 | M2 改造 owner 后可能掩盖原有转换/检索故障，发布验收无法区分新回归和旧缺陷 | M0 分别验证 DOCX、PDF、PPTX、TXT 的转换、Embedding、检索和依据文件生成；未通过的格式标记为已知限制，不得写入“已稳定能力” |
| B-07 | 浏览器导出与服务端归档链路未定义 | 当前使用 `pptx.writeFile()` 直接下载，没有生成 Blob 后上传的流程 | 用户本地下载成功不代表历史文件已保存；重试可能生成重复导出记录 | M6 固定 Blob 生成、上传协议、文件哈希、进度、失败重试、幂等键和“本地下载成功但归档失败”状态 |
| B-08 | PersonalDB 用户命名空间可能碰撞 | 当前接口直接用外部 `user_id` 作为知识库归属 | 墨灵用户 ID 可能与旧用户、测试环境或其他应用 ID 重复，造成跨空间数据混用 | M0/M2 确定内部主体 ID；知识库至少使用 `platform + app_id + user_id` 的稳定命名空间，不直接复用裸数字 ID |

阻塞项处理规则：

1. 每个阻塞项必须指定责任阶段、负责人、决策结果和验证证据。
2. B-01～B-06 未关闭时，不允许承诺正式开发工期；B-05 未关闭时不得开放生产流量；B-07 未关闭时不得把“历史下载”标记完成。
3. 若决定暂缓某项，必须同时缩减对应范围。例如 B-06 未通过时，第一期只能支持主题生成，不能承诺“依据文件生成”。
4. 阻塞项关闭结果写入 M0 基线报告，并在 G0 发布门槛逐项检查。

## 3. 建设目标

### 3.1 用户目标

1. 用户从墨灵点击“进入应用”后无需再次登录。
2. 用户生成 PPT 后可以在“我的作品”中找到它。
3. 用户关闭浏览器、刷新页面或更换设备后仍可继续编辑。
4. 用户可以重新导出和下载历史 PPTX。
5. 用户只看到自己的作品、知识库文件、任务和导出文件。
6. 收费操作有明确的积分提示、成功结果和失败回滚，不重复扣分。

### 3.2 平台与运营目标

1. 每次收费生成都可以关联用户、作品、任务、计费 hold 和请求 ID。
2. 计费终态未知时可对账，不允许通过重复点击产生白嫖或重复扣费。
3. 可以查看登录、生成、计费、保存、导出和失败日志，但日志不泄露密钥和票据。
4. 新功能可以按开关分阶段发布和回滚。

### 3.3 工程目标

1. 保留 TrainPPTAgent 现有大纲、内容生成、模板、PPTist 编辑和浏览器导出能力。
2. 以适配层接入墨灵，避免平台接口散落在业务代码中。
3. 使用 MySQL 保存业务元数据和当前编辑稿，使用对象存储保存二进制文件。
4. 所有用户归属从服务端 Session 获取，不接受浏览器指定 owner。
5. 旧 `/tools/*` 接口在迁移期保持兼容，由新业务编排层调用，避免一次性重写 Agent。

## 4. 范围与非范围

### 4.1 本计划包含

- 墨灵启动票据校验和 TrainPPTAgent 自有 Session。
- 当前用户、权益摘要和退出登录接口。
- 作品、当前编辑稿、版本快照、生成任务、计费操作、文件和导出记录。
- “我的作品”列表、历史打开、删除、二次编辑、自动保存和版本冲突处理。
- prepaid 权益解析、预占、结算、释放、一步扣减和对账。
- PPTX、缩略图、用户上传文件的对象存储和下载鉴权。
- 桌面、平板、手机响应式适配。
- 生产静态构建、Nginx、HTTPS Cookie、CORS、日志、指标和发布验收。

### 4.2 明确不包含

- 不修改墨灵平台后端、用户控制台和管理后台代码。
- 不修改、复制或覆盖 `D:\molingproject\molinppt`。
- 不迁移 molinppt 的历史用户、作品或模板数据。
- 不开发多人实时协同编辑、评论、审批和团队空间。
- 不开发公开模板交易市场。
- 不保证任意外部 PPTX 导入后百分之百还原 PowerPoint 特效。
- 不开发原生 iOS、Android 或桌面客户端。
- 不在浏览器中暴露墨灵内部 Token、数据库或对象存储凭证。

## 5. 已确定的技术决策

| 决策 | 选型 | 原因 |
|---|---|---|
| 登录交接 | Nginx 将精确路径 `/enter` 转发给主 API | ticket 直接由后端消费，减少前端和日志暴露 |
| 应用会话 | 服务端随机 Session ID + MySQL `app_sessions` | 支持主动失效、审计和后续扩展；Cookie 不保存用户声明 |
| Cookie | `HttpOnly`、`SameSite=Lax`、生产 `Secure` | 兼容跨站跳转并降低脚本窃取风险 |
| 业务数据库 | 使用当前已配置的 MySQL | 环境已具备连接配置，避免新增数据库供应链 |
| 编辑稿 | MySQL 保存当前 `slides_json` 和递增版本号 | 自动保存需要低延迟和并发版本检查 |
| 版本快照 | 手动保存、AI 操作、导出和周期检查点生成快照 | 避免每 2 秒自动保存都产生完整历史副本 |
| 二进制文件 | 对象存储保存 PPTX、缩略图和上传原文件 | 避免数据库保存大二进制，支持受控下载 |
| PPTX 生成 | 保留浏览器端 PptxGenJS | 复用已验证能力，第一期不引入服务端渲染器 |
| 计费模式 | 墨灵 prepaid | 当前商品和用户权益已经按积分额度配置 |
| 贵操作计费 | `reserve → settle`，失败 `release` | 生成耗时且可能失败，需要防并发透支和失败回滚 |
| 手工编辑 | 默认不收费 | 自动保存和普通编辑不应产生频繁积分扣减 |
| Agent 改造 | 外层业务编排，内部复用现有 outline/content 服务 | 降低对生成链路的破坏范围 |

尚未确定的积分数值、保留期限和配额不写死在代码中，必须通过配置或业务策略表管理。

## 6. 目标架构

```text
墨灵用户控制台
    │  GET /enter?ticket=<一次性票据>
    ▼
Nginx / HTTPS
    ├─ /enter  ───────────────► Main API
    ├─ /api/*  ───────────────► Main API
    └─ /*      ───────────────► 前端静态文件
                                  │
Main API                           │
    ├─ Auth/Session                │
    ├─ Presentation Service ◄──────┘
    ├─ Generation Orchestrator
    ├─ Billing Service ───────────► 墨灵内部 API
    ├─ Storage Service ───────────► 对象存储
    ├─ Repository ────────────────► MySQL
    ├─ Outline Client ────────────► Outline Agent
    ├─ Content Client ────────────► Content Agent
    └─ PersonalDB Client ─────────► PersonalDB
```

### 6.1 模块边界

建议在 `backend/main_api` 内按以下职责拆分：

```text
backend/main_api/
├── api/                 # auth、presentations、tasks、files 路由
├── core/                # 配置、Session、安全、错误、request_id
├── integrations/        # moling、storage、outline、content、personaldb 客户端
├── models/              # ORM 数据模型
├── repositories/        # 数据访问与 owner 条件
├── services/            # 作品、生成、计费、导出业务编排
├── migrations/          # MySQL 迁移
└── main.py              # 应用装配，不堆叠业务实现
```

前端建议增加：

```text
frontend/src/
├── services/auth.ts
├── services/presentations.ts
├── services/tasks.ts
├── store/auth.ts
├── store/presentations.ts
├── views/Works/
├── views/AuthFailure/
└── hooks/usePresentationAutosave.ts
```

## 7. 核心数据模型

### 7.1 `app_sessions`

| 字段 | 类型建议 | 约束/用途 |
|---|---|---|
| `id` | `char(64)` | 随机 Session ID 的哈希，主键 |
| `user_id` | `bigint` | 墨灵用户 ID，索引 |
| `app_id` | `bigint` | 必须等于配置的应用 ID |
| `product_id` | `bigint` | 必须等于配置的商品 ID |
| `created_at` | `datetime(6)` | 创建时间 |
| `expires_at` | `datetime(6)` | 过期时间，索引 |
| `last_seen_at` | `datetime(6)` | 最近活动时间 |
| `revoked_at` | `datetime(6) null` | 退出或管理员失效 |

浏览器 Cookie 只保存原始随机 Session ID；数据库只保存哈希，数据库泄露时不能直接复用会话。

### 7.2 `presentations`

| 字段 | 类型建议 | 约束/用途 |
|---|---|---|
| `id` | `char(36)` | UUID 主键 |
| `owner_user_id` | `bigint` | 墨灵用户 ID |
| `title` | `varchar(255)` | 作品标题 |
| `status` | `varchar(32)` | 状态机字段 |
| `slides_json` | `longtext` | 当前完整编辑稿 |
| `current_version` | `bigint` | 乐观锁版本，默认 1 |
| `slide_count` | `int` | 列表展示 |
| `template_id` | `varchar(64) null` | 模板标识 |
| `thumbnail_file_id` | `char(36) null` | 封面文件 |
| `created_at` | `datetime(6)` | 创建时间 |
| `updated_at` | `datetime(6)` | 最近保存时间 |
| `deleted_at` | `datetime(6) null` | 软删除 |

必须建立联合索引：

```text
(owner_user_id, deleted_at, updated_at)
(owner_user_id, status, updated_at)
```

### 7.3 `presentation_versions`

| 字段 | 类型建议 | 约束/用途 |
|---|---|---|
| `id` | `char(36)` | 主键 |
| `presentation_id` | `char(36)` | 作品 ID |
| `version` | `bigint` | 与作品版本对应 |
| `slides_json` | `longtext` | 检查点数据 |
| `reason` | `varchar(32)` | manual、ai、export、periodic |
| `created_by` | `bigint` | 操作用户 |
| `created_at` | `datetime(6)` | 创建时间 |

`(presentation_id, version)` 必须唯一。默认保留最近 20 个检查点；最终保留策略在 M0 确认。

### 7.4 `generation_tasks`

核心字段：`id`、`presentation_id`、`owner_user_id`、`request_id`、`status`、`stage`、`progress`、`input_json`、`error_code`、`error_message`、`retryable`、`attempt_count`、`max_attempts`、`lease_owner`、`lease_expires_at`、`heartbeat_at`、`started_at`、`finished_at`、`created_at`、`updated_at`。

`request_id` 必须唯一，前端重试同一业务请求时返回原任务，不重复创建收费任务。

任务领取必须使用数据库原子更新或等价锁语义。Worker 只有持有有效租约时才能调用 Agent 和写入任务终态；租约过期后由恢复扫描重新排队或标记明确失败。

### 7.5 `billing_operations`

核心字段：`id`、`task_id`、`owner_user_id`、`product_id`、`entitlement_id`、`hold_id`、`action`、`reserved_amount`、`actual_amount`、`status`、`reserve_key`、`settle_key`、`release_key`、`last_error_code`、`retry_count`、`next_retry_at`、`created_at`、`updated_at`。

三个幂等键分别唯一，禁止复用同一个字符串表示不同计费动作。

### 7.6 `files` 与 `exports`

`files` 保存 owner、作品、用途、对象存储 key、MIME、大小、哈希、状态；`exports` 保存作品版本、文件 ID、导出格式和创建时间。对象存储 key 由服务端生成，禁止使用客户端传入的绝对路径或 `..`。

## 8. 状态机

### 8.1 作品状态

```text
draft → generating → ready
                 ├─> failed
                 └─> billing_pending
ready → deleted
```

`billing_pending` 状态禁止继续收费生成和导出，但允许管理员对账；对账完成后进入 `ready` 或 `failed`。

### 8.2 生成任务状态

```text
queued
  → reserving
  → running
  → settling
  → succeeded

reserving/running/settling
  → releasing
  → failed

任一计费终态未知
  → billing_pending
```

SSE 断开只表示浏览器失去实时连接，不得直接把任务标记为失败。

### 8.3 保存状态

```text
clean → dirty → saving → saved
                    ├─> failed
                    └─> conflict
```

## 9. API 规划

### 9.1 身份

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/enter?ticket=` | 后端验证票据、创建 Session、302 跳转 `/works` |
| GET | `/api/auth/me` | 返回当前用户、产品、Session 到期和权益摘要 |
| POST | `/api/auth/logout` | 撤销 Session 并清除 Cookie |

### 9.2 作品

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/presentations` | 当前用户作品分页、搜索和筛选 |
| POST | `/api/presentations` | 创建作品和生成任务，返回 HTTP 202 |
| GET | `/api/presentations/{id}` | 加载作品当前编辑稿 |
| PATCH | `/api/presentations/{id}` | 使用 `version` 乐观锁保存 |
| POST | `/api/presentations/{id}/duplicate` | 另存副本 |
| DELETE | `/api/presentations/{id}` | 幂等软删除 |
| GET | `/api/presentations/{id}/versions` | 查询检查点版本 |
| POST | `/api/presentations/{id}/versions/{version}/restore` | 恢复为新版本，不覆盖历史 |

所有资源接口都从 Session 读取 `owner_user_id`。访问不存在、已删除或他人资源统一返回 404。

### 9.3 任务、权益与文件

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/tasks/{task_id}` | 查询生成、进度、错误和计费状态 |
| POST | `/api/tasks/{task_id}/retry` | 仅在计费终态明确且任务可重试时重试 |
| GET | `/api/entitlements/current` | 返回当前 PPT 产品可用权益摘要 |
| POST | `/api/presentations/{id}/exports` | 上传浏览器生成的 PPTX 并创建导出记录 |
| GET | `/api/presentations/{id}/exports` | 查询导出历史 |
| GET | `/api/files/{file_id}` | 鉴权后下载或返回短期签名地址 |

### 9.4 旧接口迁移

现有 `/tools/aippt_outline`、`/tools/aippt_outline_from_file` 和 `/tools/aippt` 在迁移期保持可用。M2 的任务执行器通过服务端适配器调用这些能力，M3 前端逐步切换到作品和任务接口，M5 再由 `GenerationOrchestrator` 增加计费编排。未完成真实生成回归前不得删除旧接口。

## 10. 分阶段需求

## M0：基线冻结与技术准备

### 目标

建立可重复开发和验收的起点，避免在现有未提交修改、开发代理和生产配置混用的状态下直接开发。

### 工作内容

1. 复核当前 Git 修改，将端口、文档和环境模板改动与后续功能分开。
2. 记录五个服务的启动命令、健康接口和端口。
3. 将墨灵、Session、MySQL、对象存储和计费变量加入 `env_template.txt`，只写占位符。
4. 增加配置启动校验：必填配置缺失时失败退出，但不打印密钥。
5. 确认积分策略、作品保留期限、版本数、上传大小和单用户配额。
6. 选定 ORM 和迁移工具，并完成 MySQL 连通性验证。
7. 为新功能定义开关：SSO、持久化、计费、对象存储。
8. 为 B-01～B-08 建立阻塞项台账，确定责任人、关闭阶段和验证方法。
9. 冻结第一版 OpenAPI 契约，包括错误体、分页、幂等、任务事件和文件上传协议。
10. 验证 PersonalDB 的文件转换、Embedding、检索和依据文件生成基线，并记录支持格式矩阵。
11. 完成 JSON 版本、PPTX、缩略图和上传文件的容量模型与保留策略。

### 交付物

- 配置清单和环境说明。
- 数据库迁移基线。
- 当前功能回归基线报告。
- 运营决策记录。
- 开发阻塞项台账及关闭证据。
- 第一版 OpenAPI 和支持文件格式矩阵。
- 容量、配额、保留和清理策略。

### 阶段验收

- 本地五个服务和现有生成路径保持可用。
- `.env` 不被 Git 跟踪，模板中没有真实密钥。
- MySQL 和对象存储完成只读/最小写入连通测试。
- 未确认积分数值时，生产收费开关保持关闭。
- B-01～B-08 均有已批准的解决方案；B-01、B-03、B-04、B-05、B-08 的技术契约已经冻结。
- 文件转换、Embedding、检索和依据文件生成分别标记为“真实通过”“Mock 通过”或“已知限制”，不得合并描述。

## M1：墨灵 SSO 与应用 Session

### 目标

用户从墨灵进入后自动登录，并让后端获得可信的墨灵用户身份。

### 工作内容

1. 增加墨灵客户端，封装 verify 和统一错误映射。
2. 实现 `/enter`：校验 ticket、app ID、product ID，创建 Session 并清除 URL 中的 ticket。
3. 实现 `/api/auth/me` 与 `/api/auth/logout`。
4. 增加 Session 依赖和 owner 获取方法。
5. Nginx 精确代理 `/enter` 到主 API。
6. 前端增加认证初始化、登录失败页和“返回墨灵”提示。
7. 日志只记录票据哈希前缀或 request ID，不记录完整 ticket。
8. `/enter` 返回 `Cache-Control: no-store` 和 `Referrer-Policy: no-referrer`，Nginx 不记录完整 ticket 查询值。
9. 定义 Session 的绝对过期、空闲过期、登录轮换、撤销和清理规则。
10. Cookie 写操作接口启用可信 Origin 校验或 CSRF Token；CORS 不能作为唯一 CSRF 防护。

### 异常要求

- ticket 缺失、过期、已使用、伪造或重放：拒绝登录。
- app/product 不匹配：拒绝并记录安全审计事件。
- 平台超时：显示可重试提示，但不能自动重复消费同一 ticket。
- Session 过期：用户资源接口返回 401，前端引导重新从墨灵进入。

### 阶段验收

- 有效 ticket 只消费一次，302 到 `/works`。
- 地址栏跳转后不再包含 ticket。
- `/api/auth/me` 返回当前用户且不包含敏感凭证。
- 重放、伪造和错误应用票据均不能创建 Session。
- Nginx访问日志、应用日志、浏览器地址和 Referrer 中均不出现完整 ticket。
- 跨站页面不能使用用户 Cookie 成功调用作品修改、删除、生成和导出接口。

## M2：业务数据、用户隔离与任务执行基线

### 目标

让作品、版本、任务、文件和计费记录具有可信所有权，并建立不依赖浏览器连接的持久任务执行基础。

### 工作内容

1. 建立核心业务表和迁移。
2. 实现 Repository 层，所有查询默认带 `owner_user_id` 条件。
3. 将上传文件、PersonalDB 调用和生成请求中的用户 ID 改为服务端 Session 用户。
4. 保留旧 `sessionId` 仅用于生成上下文，不再充当用户身份。
5. 增加统一 401、404、409 和业务错误响应。
6. 增加跨用户访问、路径穿越和伪造 owner 测试。
7. 实现最小持久任务执行器，支持原子领取、租约续期、超时回收、有限重试和服务重启恢复。
8. 任务执行器只负责非计费任务生命周期；M5 在同一生命周期外层增加 reserve、settle 和 release。
9. PersonalDB 使用内部主体 ID 或带平台、应用维度的命名空间，不直接使用裸 `user_id`。

### 阶段验收

- 浏览器传入不同 `user_id` 不会改变资源所有者。
- 两个测试用户不能互相查询作品、文件和任务。
- 他人资源和不存在资源统一返回 404。
- 现有主题、文件、大纲和内容生成仍能工作。
- 主 API 或 Worker 重启后，未完成任务能恢复为可继续、可重试或明确失败状态，不永久停留在 `running`。
- 两个 Worker 并发领取同一任务时，只有一个获得有效租约并调用 Agent。

## M3：我的作品与历史打开

### 目标

用户能够找到生成过的 PPT，并重新进入编辑器。

### 工作内容

1. 新增 `/works` 页面和作品 Store。
2. 支持分页、标题搜索、状态筛选和更新时间排序。
3. 作品卡片显示缩略图、标题、页数、状态和更新时间。
4. 新建作品时先创建 `presentation` 和 `generation_task`。
5. 生成完成后保存完整 `slides_json` 和当前版本。
6. 编辑路由调整为 `/editor/:presentationId`，刷新后从服务端恢复。
7. 实现软删除和二次确认。

M3 只能使用 M2 已验收的任务执行器；本阶段不得另写一套前端定时器或 API 内后台协程代替持久任务。

### 响应式要求

- 1440px：4 列优先，空间不足时 3 列。
- 1024px：2～3 列。
- 768px：2 列。
- 390px：1 列，搜索和筛选收进抽屉。

### 阶段验收

- 新作品生成成功后 5 秒内出现在列表。
- 关闭浏览器后，同一用户重新进入仍可打开作品。
- 刷新 `/editor/:id` 不丢失作品。
- 删除后列表、详情、编辑和下载均不可用。

## M4：二次编辑与可靠保存

### 目标

用户修改历史作品后可以稳定保存，不因断网或多标签页覆盖数据。

### 工作内容

1. 增加手动保存和 2 秒防抖自动保存。
2. 每次保存提交当前 `version`，成功后接收递增的新版本。
3. 版本冲突返回 HTTP 409，前端提供“加载最新版本”和“另存副本”。
4. 保存失败时保留本地未提交草稿；恢复网络后由用户确认重试。
5. 页面离开前检测未保存修改。
6. 增加检查点版本，默认保留最近 20 个。
7. 手机端至少支持查看、切换页面、修改基础文字和保存。

### 阶段验收

- 停止编辑 2 秒后触发一次保存，不持续刷请求。
- 正常网络下保存完成后 1 秒内显示“已保存”。
- 两个标签页保存同一旧版本时，后提交者收到 409，服务器数据不被覆盖。
- 网络失败后刷新前仍能恢复本地草稿提示。

## M5：生成任务与积分计费

### 目标

收费生成具有幂等、并发安全、失败回滚和异常对账能力。

### 工作内容

1. 实现权益解析，按当前用户和商品选择可用 entitlement。
2. 生成前创建持久化任务和全局唯一 request ID。
3. 调用 reserve 成功后才允许调用生成 Agent。
4. 生成成功并持久化作品后调用 settle。
5. Agent 或持久化失败时调用 release。
6. 计费结果未知时进入 `billing_pending`，禁止重复收费生成。
7. 实现后台对账任务，重试 settle/release，不重复 reserve。
8. 单页 AI 重生成或 AI 修改按最终运营规则选择 reserve 或 consume。
9. 普通编辑、自动保存和默认 PPTX 下载不收费。

### 幂等键规则

```text
ppt:{task_id}:reserve
ppt:{task_id}:settle
ppt:{task_id}:release
ppt:{presentation_id}:edit:{request_id}:consume
```

### 计费发布门槛

以下配置未确认时，M5 可以开发和 Mock 测试，但不能打开生产计费：

- 整套 PPT 生成的预占额度。
- 实际结算是固定值还是按页数/模型用量计算。
- 单页重新生成、AI 修改和重新导出的收费规则。
- 多个可用 entitlement 的选择优先级。

### 阶段验收

- 成功生成只有一次 reserve 和一次 settle，reserved 最终归零。
- 明确失败执行 release，quota_used 不增加。
- 同一 request ID 重试不创建第二个任务，也不重复扣分。
- 额度不足时不调用任何生成 Agent。
- settle/release 暂时失败时进入待对账，用户看不到虚假的“已退款”。

## M6：对象存储与导出归档

### 目标

用户可以长期保存和再次下载 PPTX、缩略图和上传源文件。

### 工作内容

1. 建立 Storage Adapter，屏蔽 OSS、S3 和 MinIO 差异。
2. 服务端生成对象 key，例如 `users/{uid}/presentations/{pid}/exports/{fileId}.pptx`。
3. 保留浏览器 PptxGenJS 导出，导出完成后上传后端并创建记录。
4. 生成列表缩略图并使用懒加载。
5. 下载时重新校验 Session、作品 owner 和删除状态。
6. 使用受 Session 保护的流式下载或短期签名地址。
7. 校验 MIME、扩展名、文件签名、大小和 SHA-256。
8. 将现有 `writeFile()` 调整为可获得 Blob 的导出流程；本地下载和服务端归档使用同一份文件字节与 SHA-256。
9. 为“本地下载成功但归档失败”保留独立状态和可重试入口，重试使用幂等键，不重复创建导出记录。

### 阶段验收

- 同一作品可保存多次导出记录。
- 重新登录后可以下载历史 PPTX。
- 用户 A 无法下载用户 B 的文件。
- 软删除作品后旧下载地址失效。
- 下载文件可用 Microsoft PowerPoint 或兼容软件正常打开。

## M7：可恢复性、安全与运维

### 目标

系统在网络中断、服务重启和第三方超时时仍可判断任务和计费终态。

### 工作内容

1. 提供任务查询和受控重试。
2. 增加计费对账、失败导出重试和过期 Session 清理任务。
3. 增加 X-Request-Id、结构化日志和审计事件。
4. 增加用户级生成、保存、下载和登录限流。
5. CORS 改为配置白名单。
6. 错误响应统一中文信息、稳定错误码、retryable 和 request_id。
7. 增加数据库、对象存储、墨灵、三个 Agent 和 PersonalDB 的依赖健康检查。
8. 建立备份、恢复演练和告警阈值。

### 阶段验收

- 浏览器断开 SSE 后可以通过任务 ID恢复状态。
- 服务重启后可继续查询未完成任务和计费操作。
- 日志不包含完整 ticket、Cookie、Token、模型密钥和存储密钥。
- 每个生成任务可以关联作品、用户、request ID 和计费记录。

## M8：生产发布与真实验收

### 目标

将开发环境能力安全发布到 `https://ppt.axicomin.cn`，完成真实用户和真实积分验收。

### 工作内容

1. 前端执行正式构建，Nginx 提供静态文件，不代理 Vite 开发服务。
2. `/enter` 和 `/api` 代理主 API，history 路由回退 `index.html`。
3. 设置正式 `APP_BASE_URL`、CORS、Secure Cookie 和可信代理头。
4. 执行数据库迁移和对象存储 Bucket 权限检查。
5. 使用两个墨灵用户做跨用户隔离测试。
6. 使用真实权益执行成功结算、失败释放、重复请求和异常对账。
7. 在 1440、1024、768、390 四档设备宽度进行视觉验收。
8. 验证生成 PPTX 的页数、内容和实际打开效果。
9. 建立发布观察期和回滚值班清单。

### 阶段验收

- 域名页面不再加载 Vite HMR，不出现 WebSocket 开发错误。
- 从墨灵点击进入、生成、保存、打开、编辑、导出和下载完整走通。
- 真实积分变化与平台消费记录一致。
- 两个用户之间没有作品、知识库和文件泄露。

## 11. 依赖关系与并行策略

```text
M0 基线与决策
 └─> M1 SSO/Session
      └─> M2 数据与所有权
           ├─> M3 作品历史 ──> M4 二次编辑
           ├─> M5 任务计费
           └─> M6 存储导出

M4 + M5 + M6 ──> M7 恢复/安全/运维 ──> M8 生产发布
```

M2 完成后可以并行三条工作流：

- 前端主线：M3、M4。
- 后端计费主线：M5。
- 文件与部署主线：M6，部分 M7。

M5 不能早于 M1，因为没有可信用户就不能扣正确权益；M3、M4 不能早于 M2，因为没有服务端作品就无法可靠保存；M8 必须等待 M4、M5、M6 的生产门槛全部通过。

## 12. 可执行任务拆分

每个任务控制在 1～3 个开发日，便于独立评审和回滚。

| 编号 | 任务 | 阶段 | 依赖 | 验收结果 |
|---|---|---|---|---|
| T01 | 配置模板、启动校验和功能开关 | M0 | 无 | 缺配置失败退出且不泄密 |
| T02 | ORM、迁移工具和 MySQL 基线 | M0 | T01 | 空库可一键迁移和回滚应用版本 |
| T03 | 墨灵客户端与 verify 契约测试 | M1 | T01 | 成功、超时和平台错误均正确映射 |
| T04 | `/enter`、Session 和 Cookie | M1 | T02、T03 | 墨灵免登闭环通过 |
| T05 | `/api/auth/me`、logout 和前端认证 Store | M1 | T04 | 前端可识别登录态和过期态 |
| T06 | 核心业务表、Repository 和任务租约模型 | M2 | T02、T04 | owner 条件强制执行，任务可原子领取 |
| T07 | 旧接口移除客户端 user_id 信任 | M2 | T06 | 伪造 user_id 无效 |
| T08 | 持久任务 Worker、超时回收和重启恢复 | M2 | T06 | 重启不丢任务且不重复调用 Agent |
| T09 | 作品 CRUD API | M3 | T06 | 创建、列表、详情、删除通过 |
| T10 | `/works` 响应式页面 | M3 | T09 | 四档宽度通过 |
| T11 | 历史作品加载编辑器 | M3 | T09 | 刷新和换设备可恢复 |
| T12 | 自动保存、手动保存和离开保护 | M4 | T11 | 正常和断网流程通过 |
| T13 | 乐观锁、409 和另存副本 | M4 | T12 | 多标签不覆盖 |
| T14 | 检查点版本和恢复 | M4 | T13 | 恢复产生新版本 |
| T15 | 权益解析和计费策略配置 | M5 | T04、运营规则 | 选中正确 entitlement |
| T16 | 计费型生成任务与 request 幂等 | M5 | T06、T08 | 重复请求复用任务且不重复预占 |
| T17 | reserve/settle/release 编排 | M5 | T15、T16 | 三条计费路径通过 |
| T18 | billing_pending 对账任务 | M5/M7 | T17 | 终态未知可恢复 |
| T19 | 对象存储 Adapter 与文件表 | M6 | T06 | 上传、读取、删除标记通过 |
| T20 | PPTX 归档、缩略图和下载鉴权 | M6 | T19 | 历史下载与越权测试通过 |
| T21 | 统一错误、request ID、审计与限流 | M7 | T04、T06 | 安全与可观测性验收通过 |
| T22 | 正式构建和 Nginx 配置 | M8 | T10、T20 | 无 Vite HMR 错误 |
| T23 | 真实墨灵、积分、多用户和 PPTX UAT | M8 | 全部 | 发布门槛全部通过 |

## 13. 测试规划

| 层级 | 覆盖内容 | 最低新增用例 |
|---|---|---:|
| 单元测试 | 配置、Session、owner、状态机、幂等键、版本锁、文件 key | 40 |
| Repository 测试 | 所有权过滤、分页、软删除、唯一约束、并发版本 | 18 |
| 任务执行测试 | 原子领取、租约续期、Worker 崩溃、超时回收、重启恢复、重复投递 | 10 |
| API 集成测试 | SSO、作品 CRUD、任务、导出、下载、错误映射 | 28 |
| 墨灵契约测试 | verify、entitlements、reserve、settle、release、consume | 15 |
| 前端组件测试 | 登录态、作品卡片、保存状态、冲突、任务失败 | 18 |
| E2E | 免登到生成、历史、编辑、导出和下载 | 8 |
| 安全测试 | ticket 重放、伪造 owner、越权 ID、CORS、路径穿越、密钥扫描 | 15 |
| 响应式视觉测试 | 1440、1024、768、390 的作品、编辑和状态页面 | 12 个页面状态 |
| 真实联调 | 两用户、成功结算、失败释放、异常对账、实际 PPTX | 5 条主路径 |

自动化测试不能代替真实平台和真实文件验收。测试报告必须分别标注：本地自动化、Mock 墨灵、真实墨灵、真实对象存储、视觉检查和 PowerPoint 打开验证。

## 14. 非功能指标

### 14.1 性能

- 单用户 1,000 条作品时，列表 API P95 不高于 500 ms。
- `slides_json ≤ 10 MiB` 时，详情 API P95 不高于 1 秒。
- 自动保存使用 2 秒防抖，同一时刻最多一个保存请求在途。
- 列表缩略图懒加载，不下载 PPTX 作为预览。

### 14.2 可用性

- Session、任务和计费状态均持久化，服务重启后可查询。
- 对象存储不可用时允许保存编辑稿，但导出明确失败并可重试。
- 墨灵短暂不可用时不创建匿名付费任务。
- `billing_pending` 默认 fail-closed，禁止继续收费动作。

### 14.3 安全

- 所有用户资源强制 owner 校验。
- Session Cookie 生产环境必须 Secure、HttpOnly、SameSite=Lax。
- CORS 只允许正式域名和明确的本地开发地址。
- 内部 Token、模型密钥、存储密钥和完整 ticket 不进入前端、日志或错误响应。
- 上传和下载防路径穿越、MIME 欺骗和超大文件。

## 15. 发布门槛

| Gate | 放行条件 | 不通过时处理 |
|---|---|---|
| G0 基线 | 旧生成与导出回归通过，配置模板完整，B-01～B-08 有明确关闭方案 | 不开始 SSO 开发 |
| G1 身份 | ticket、Session、重放、app/product 校验通过 | 不开放历史和计费 |
| G2 数据 | 两用户隔离、作品恢复、版本冲突通过 | 不开放生产作品库 |
| G3 计费 | 成功、失败、重复、超时、对账路径通过 | 计费开关保持关闭 |
| G4 文件 | 历史下载、越权、删除失效、实际打开通过 | 暂停归档下载 |
| G5 发布 | 正式构建、HTTPS、四档 UI、真实 UAT 通过 | 回滚应用流量 |

## 16. 回滚方案

1. SSO、作品持久化、计费和对象存储分别使用功能开关。
2. 数据库迁移只新增表和字段；应用回滚时保留数据，不执行生产降级删表。
3. M1 失败时平台入口临时切回维护页，不允许匿名进入收费功能。
4. M3/M4 失败时可以临时关闭历史入口，但保留已保存作品数据。
5. M5 失败时关闭新收费任务，先完成所有 reserved 和 billing_pending 对账。
6. M6 失败时暂停新导出，保留编辑稿和文件索引，不批量删除对象。
7. 发布回滚后继续运行只读对账和数据备份，不让计费 hold 长期残留。

## 17. 风险分析

| 风险 | 级别 | 影响 | 缓解措施 |
|---|---|---|---|
| 当前工作区存在未提交修改 | 高 | 开发改动混杂，难以回滚 | M0 先分离和确认现有修改 |
| 票据只用一次且短时有效 | 高 | 自动重试导致用户无法登录 | 后端单次消费，失败引导重新从墨灵进入 |
| 前端传入 user_id | 高 | 跨用户数据泄露 | M2 全部改为 Session owner |
| SSE 断开被误判失败 | 高 | 重复生成和重复扣分 | 任务持久化，前端按 task ID 查询 |
| settle/release 终态未知 | 高 | 重复扣分或积分长期占用 | billing_pending + 后台对账 |
| 自动保存大 JSON | 中 | MySQL 压力和保存延迟 | 防抖、大小限制、索引、检查点节流 |
| 对象存储为内网地址 | 中 | 部署拓扑变化后不可达 | M0 连通性验证，应用代理下载 |
| 浏览器生成 PPTX 后上传 | 中 | 大文件占用浏览器和带宽 | 限制大小、进度提示、断点重试后续评估 |
| 手机端完整编辑复杂 | 中 | 交互拥挤和误操作 | 本期限定基础文本编辑，桌面保持完整能力 |
| Vite 开发服务直接上域名 | 中 | WebSocket 错误和不稳定 | M8 改为正式静态构建 |
| 缺少持久任务执行器 | 高 | 服务重启后任务卡死或重复执行 | M0 冻结执行模型，M2 实现租约、恢复和重试 |
| M3/M5 任务依赖倒置 | 高 | 历史作品阶段被迫临时实现生成流程 | 将非计费任务基础提前到 M2，M5 只增加计费编排 |
| 完整版本长期保存在 MySQL | 高 | 数据库、备份和恢复容量失控 | M0 完成容量模型，采用压缩、增量或对象存储版本 |
| SSO 票据进入访问日志 | 高 | 一次性票据在有效期内可能泄露 | `/enter` no-store/no-referrer，Nginx 日志脱敏 |
| PersonalDB 裸用户 ID 碰撞 | 高 | 跨应用或环境知识库数据混用 | 使用内部主体或平台、应用、用户复合命名空间 |

## 18. 不得破坏的现有能力

- 主题生成大纲。
- 根据上传文件生成大纲。
- 大纲确认后逐页生成内容。
- 模板选择和模板内容填充。
- PPTist 文本、图片、形状、表格、图表和页面编辑。
- 浏览器端 PPTX 导出。
- Outline、Content、PersonalDB 三个服务的现有职责。
- 已配置的模型提供商和独立写作/检查模型能力。
- 当前模板资源和毕业答辩模板。

每个阶段合并前必须运行现有生成和导出回归，不得以新平台功能为由重写已经可用的 Agent 或编辑器核心。

## 19. 开发前必须确认的运营项

| 决策项 | 推荐默认值 | 最晚确认时间 |
|---|---|---|
| 整套 PPT 预占积分 | 配置项，不写死 | M5 开发前 |
| 实际结算算法 | 第一版固定积分，后续再按页数扩展 | M5 开发前 |
| 单页 AI 重新生成 | 单独收费，使用配置项 | M5 联调前 |
| 手工编辑与自动保存 | 免费 | M4 开发前 |
| PPTX 导出 | 第一版免费 | M6 开发前 |
| 作品保留期限 | 默认长期保留，软删除不立即物理清理 | M2 迁移前 |
| 版本检查点 | 最近 20 个 | M4 开发前 |
| 单作品 JSON 上限 | 10 MiB | M2 开发前 |
| 手机端范围 | 查看、切页、基础文字编辑和保存 | M3 UI 开发前 |
| 单用户作品/存储上限 | 待运营配置 | M8 发布前 |

## 20. 建议启动顺序

正式开发时按以下顺序开始：

1. 先完成 M0，不立即改业务流程。
2. 单独提交 M1 的墨灵客户端、Session 和 `/enter`。
3. 使用真实墨灵入口完成 G1 验收。
4. 完成 M2 数据模型和 owner 隔离后，再允许前端开发历史作品。
5. M3/M4、M5、M6 分支并行，但分别通过独立 Gate。
6. 最后统一完成 M7 和 M8，不把生产部署问题留到功能开发结束后临时处理。

## 21. 需求完成定义

只有以下条件全部满足，才能将“TrainPPTAgent 对接墨灵平台”标记为完成：

1. 用户可从墨灵免登录进入正式域名。
2. Session、owner 和多用户隔离测试通过。
3. 用户能生成、找到、打开、编辑、保存、导出并再次下载 PPT。
4. 成功计费、失败释放、重复请求和异常对账使用真实权益验证通过。
5. 数据库迁移、对象存储、配置模板、Nginx 和运维说明已经交付。
6. 自动化测试、四档设备视觉检查和 PowerPoint 实际打开检查通过。
7. 生产页面不再依赖 Vite 开发服务。
8. 验收报告明确区分自动化、Mock、真实平台、真实存储和人工视觉结果。

## 22. 参考基线

- `molin_docs/TrainPPTAgent对接墨灵平台及功能增强需求分析.md`
- `molin_docs/app/developer-integration-guide.md`
- `molin_docs/app/billing-integration-spec.md`
- `molin_docs/app/developer-requirements.md`
- `molin_docs/app-launch-entry-requirement.md`
- `frontend/src/router/index.ts`
- `frontend/src/utils/database.ts`
- `frontend/src/hooks/useExport.ts`
- `backend/main_api/main.py`
- `docker-compose.yml`
- `env_template.txt`
