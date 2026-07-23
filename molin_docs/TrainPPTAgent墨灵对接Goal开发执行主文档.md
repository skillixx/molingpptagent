# TrainPPTAgent 墨灵对接 Goal 开发执行主文档

> 文档类型：Goal 执行主文档
> 文档状态：`IN_PROGRESS`
> 当前阶段：`M6`
> 当前任务：`T20`
> 下一动作：实现PPTX/缩略图归档、owner下载鉴权与历史再次下载实际打开
> 建立日期：2026-07-22
> 适用仓库：`D:\molinggithub\TrainPPTAgent`
> 需求基线：[TrainPPTAgent 对接墨灵平台全阶段开发规划](./TrainPPTAgent对接墨灵平台全阶段开发规划.md)
> 顺序提示词：[TrainPPTAgent 墨灵对接 Goal 顺序开发提示词](./TrainPPTAgent墨灵对接Goal顺序开发提示词.md)

## 1. 文档用途

这份文件是后续 Goal 开发的唯一执行入口。需求基线回答“为什么做、做什么”，本文件回答“现在做哪一项、改哪些文件、如何验证、证据写在哪里”。

后续每轮开发必须先读取本文件的以下内容：

1. `项目状态块`。
2. `阻塞项台账`。
3. `任务总看板`。
4. 当前任务对应的任务卡。
5. 当前阶段对应的发布 Gate。

本文件不替代接口契约、数据库迁移和测试报告。开发过程中产生的契约与报告必须从本文件链接出去。

## 2. 项目状态块

> 这是后续 Goal 恢复上下文时优先读取的状态。每完成一个任务都必须更新。

```yaml
project: TrainPPTAgent-Moling-Integration
goal_status: in_progress
current_stage: M8
current_task: T23
current_gate: G5
completed_tasks: 22
total_tasks: 23
blocked_tasks: 1
last_completed_task: T22
last_verified_at: 2026-07-23T09:44:49+08:00
production_billing_enabled: false
production_traffic_enabled: false
```

状态值只能使用：

| 状态 | 含义 |
|---|---|
| `pending` | 依赖未完成，尚不能开始 |
| `ready` | 依赖已满足，可以创建 Goal 开发 |
| `in_progress` | 当前 Goal 正在实施 |
| `verification` | 代码完成，正在验证和收集证据 |
| `blocked` | 外部条件或连续失败阻止继续 |
| `completed` | 验收项和证据全部完成 |
| `rolled_back` | 已撤销实现，数据和外部状态完成处理 |

## 3. 如何使用 Goal 开发

如果不想逐个任务创建Goal，直接使用[Goal顺序开发提示词](./TrainPPTAgent墨灵对接Goal顺序开发提示词.md)中的“一次性总Goal提示词”。

### 3.1 开始当前任务

向开发代理发送：

```text
创建 Goal：读取《molin_docs/TrainPPTAgent墨灵对接Goal开发执行主文档.md》，
执行项目状态块中的 current_task。一次只完成一个任务，不跨越 Gate。
先检查工作区和任务依赖，再实施、测试并把证据更新回执行主文档。
不得提交或推送，除非我单独明确要求。
```

### 3.2 继续未完成 Goal

```text
继续当前 Goal。先读取 Goal 执行主文档中的项目状态块、当前任务卡和最新证据记录，
保留工作区已有修改，从上次未完成的验收项继续。
```

### 3.3 只检查，不实施

```text
只检查 Goal 执行主文档当前任务的完成情况，运行只读检查并报告缺口，
不要修改代码、配置、外部平台或任务状态。
```

### 3.4 每个 Goal 的固定流程

```text
读取状态 → 检查依赖 → 检查 git 状态 → 标记 in_progress
  → 实施最小完整任务 → 自动化验证 → 真实/人工验证
  → 写入证据 → 标记 completed → 推进 current_task
```

每个 Goal 必须遵守：

1. 一次只实施一个任务卡，不顺手开发后续任务。
2. 开始前运行 `git status --short`，保留不属于当前任务的修改。
3. 代码使用中文注释解释非显而易见的业务规则、并发语义和安全边界。
4. 前端新增页面必须验证 1440、1024、768、390 四档宽度。
5. 本地自动化通过不等于真实墨灵、真实对象存储、真实积分或 PowerPoint 打开验收通过。
6. 未经明确授权，不修改墨灵平台项目和 `D:\molingproject\molinppt`。
7. 未经明确授权，不执行 Git commit、push、生产迁移、生产扣费或流量切换。

## 4. 当前事实基线

核实日期：2026-07-22。

| 项目 | 当前事实 | 开发含义 |
|---|---|---|
| Git | GitHub远程仓库，当前分支 `main` | 不因文档存在而自动提交或推送 |
| 前端 | Vue 3、Vite、Pinia、PPTist，端口默认5778 | Windows命令优先使用 `npm.cmd` |
| 主API | FastAPI，默认端口6800 | 新路由从 `backend/main_api` 接入 |
| 大纲Agent | 默认端口10001 | 保留现有调用契约 |
| 内容Agent | 默认端口10011 | 保留现有流式生成能力 |
| PersonalDB | 默认端口9100 | 文件转换和Embedding必须单独验收 |
| 当前入口 | 没有 `/enter` 和 `/works` | M1/M3分别补齐 |
| 当前身份 | 浏览器可传 `user_id/sessionId` | M2必须消除对客户端owner的信任 |
| 当前编辑稿 | Pinia + Dexie本地状态 | 不能作为长期作品库 |
| 当前导出 | `pptx.writeFile()` 本地下载 | M6补服务端归档 |
| 数据库 | `.env`已有MySQL连接键 | 代码尚无ORM和迁移 |
| 对象存储 | `.env`已有存储配置键 | 代码尚无Storage Adapter |
| 部署 | 根启动器管理4个后端服务和前端 | README中的3服务说明不是当前事实来源 |

现有主API入口：

- `POST /tools/aippt_outline`
- `POST /tools/aippt_outline_from_file`
- `POST /tools/aippt`
- `POST /tools/aippt_by_id`
- `GET /data/{filename}`
- `GET /templates`
- `GET /files/{user_id}`
- `GET /proxy`
- `GET /healthz`

## 5. 开发基线决策

以下决策作为第一版默认实现。若后续要变更，必须先修改本节并记录原因，不能由单个任务临时改路线。

| 主题 | 第一版决策 |
|---|---|
| 主应用结构 | 在 `backend/main_api` 内拆分 `api/core/integrations/models/repositories/services/migrations` |
| ORM与迁移 | SQLAlchemy 2.x + Alembic；MySQL驱动优先使用纯Python兼容方案 |
| 业务时间 | 数据库存UTC，API返回带时区ISO 8601 |
| ID | 业务实体使用UUID字符串；墨灵用户ID保留平台原始整数 |
| Session | 浏览器存随机Session ID，数据库只存SHA-256哈希 |
| Session Cookie | HttpOnly、SameSite=Lax、生产Secure、Path=/，名称通过配置管理 |
| 任务执行 | 第一版使用MySQL租约Worker，不新增Redis/RabbitMQ依赖 |
| 任务并发 | MySQL 8优先使用事务锁与 `SKIP LOCKED`；不满足版本时使用带条件原子更新 |
| API契约 | FastAPI/Pydantic模型生成OpenAPI，接口实现前先冻结请求、响应和错误体 |
| 当前编辑稿 | MySQL保存当前版本；大检查点压缩或转存对象存储，禁止无限复制10MiB JSON |
| PPTX生成 | 保留浏览器PptxGenJS，同一Blob用于本地下载和归档 |
| 二进制文件 | Storage Adapter统一封装，业务代码不拼接厂商URL |
| 计费 | 墨灵prepaid；贵操作reserve→settle，失败release |
| 计费安全 | balance只用于提示，是否可扣由平台reserve/consume原子判断 |
| 用户归属 | 只从服务端Session读取，浏览器不能指定owner |
| PersonalDB命名空间 | `moling:{app_id}:{user_id}`或等价内部主体ID，不使用裸用户数字 |
| 手机端 | 第一版至少保证查看、切页、基础文字编辑和保存，完整桌面编辑不强行缩放复刻 |

## 6. 阻塞项台账

| 编号 | 状态 | 责任任务 | 关闭条件 | 证据路径 |
|---|---|---|---|---|
| B-01 持久任务执行器 | `closed` | T02、T06、T08 | 任务租约方案冻结，重启恢复和重复领取测试通过 | T08已完成独立Worker、心跳、派发标记、崩溃恢复、有限重试、死信和Agent调用计数；证据见T08验证记录 |
| B-02 阶段依赖倒置 | `resolved_in_plan` | T08、T16 | 非计费任务在M2完成，M5只增加计费 | 本文任务依赖 |
| B-03 API契约缺失 | `closed` | T01～T20 | 对应接口实现前已有Pydantic/OpenAPI和错误示例 | T09～T20已冻结作品、版本、计费任务、平台三动作、对账、文件、PPTX归档和下载契约；T20二进制requestBody与400/403/404/409/410/413/415/503响应经OpenAPI测试通过 |
| B-04 容量模型缺失 | `closed` | T02、T14、T19 | 配额、版本、清理、超限规则通过评审 | T19已完成100件/1GiB非生产默认、owner原子占额、0006回填、大检查点对象化、引用GC和崩溃恢复；生产值仍由T23确认但代码阻塞已关闭 |
| B-05 SSO/CSRF安全缺失 | `closed` | T03～T05、T21 | 日志脱敏、Session、Origin/CSRF测试通过 | T21已补齐全局Request ID、安全错误、owner限流、元数据审计、依赖健康和秘密扫描；结合T03～T05的verify、Session、防重放、Origin/CSRF与退出证据关闭 |
| B-06 依据文件能力未验收 | `closed` | T01、T07、T23 | 支持格式矩阵和真实生成结果形成报告 | G0/T07真实验证四格式转换、Embedding和检索；T23在隔离端口完成TXT上传、转换、向量化、依据大纲、知识库检索及最小正文HTTP 200/5095字符/`[DONE]`终态，详见真实UAT报告 |
| B-07 导出归档链路缺失 | `closed` | T19、T20 | 同Blob下载与归档、失败重试和幂等通过 | T20完成同Blob、同SHA归档、本地优先、同键重试、历史下载、owner/软删除/过期隔离；真实对象存储回读与PowerPoint打开见T20记录 |
| B-08 PersonalDB命名空间碰撞 | `closed` | T06、T07 | 复合命名空间和跨用户测试通过 | T07已完成环境/应用/用户复合主体、两个主体同文件名同file ID真实上传与交叉检索隔离；证据见文件能力报告T07复验 |

## 7. 运营决策台账

以下项目没有确认前，可以开发Mock和配置能力，但不能开启生产计费或正式发布。

| 编号 | 决策 | 当前状态 | 推荐默认值 | 最晚关闭任务 |
|---|---|---|---|---|
| O-01 | 整套PPT预占积分 | `defaulted` | 配置项，不写死；真实值未配前保持计费关闭 | T15 |
| O-02 | 实际结算算法 | `defaulted` | 第一版固定积分，结算不得超过预占 | T15 |
| O-03 | 单页AI重新生成费用 | `defaulted` | 独立`SLIDE_REGENERATION_POINTS`；真实值未确认前不开放该收费入口 | T17 |
| O-04 | 多权益选择顺序 | `defaulted` | 可用且最早过期优先，不拆分扣多个权益，同到期按ID稳定排序 | T15 |
| O-05 | PPTX导出收费 | `defaulted` | 第一版免费 | T20 |
| O-06 | 作品保留期限 | `defaulted` | 长期保留，软删除30天后物理清理；期限保持配置项 | T02 |
| O-07 | 检查点数量 | `defaulted` | 最近20个，但受容量上限约束 | T14 |
| O-08 | 单作品JSON上限 | `defaulted` | 10MiB | T02 |
| O-09 | 单用户作品/存储上限 | `defaulted_nonproduction` | 契约测试默认100件/1GiB且保持配置项；生产值必须在T23前确认 | T19/T23 |

## 8. 阶段与Gate

| 阶段 | 任务 | Gate | 阶段完成条件 |
|---|---|---|---|
| M0 基线与准备 | T01～T02 | G0 | 配置、迁移、阻塞方案、容量与真实基线明确 |
| M1 SSO/Session | T03～T05 | G1 | 真实ticket免登、重放防护、Session安全通过 |
| M2 数据/任务基础 | T06～T08 | G2-A | owner隔离、任务租约、重启恢复通过 |
| M3 作品历史 | T09～T11 | G2-B | 创建、列表、历史打开和刷新恢复通过 |
| M4 二次编辑 | T12～T14 | G2 | 自动保存、冲突、版本恢复通过 |
| M5 计费 | T15～T18 | G3 | 成功、失败、重复、未知终态和对账通过 |
| M6 文件归档 | T19～T20 | G4 | 历史归档、越权、删除失效和实际打开通过 |
| M7 安全运维 | T21 | G4.5 | 错误、审计、限流、监控和恢复说明完成 |
| M8 发布验收 | T22～T23 | G5 | 正式构建和真实UAT通过 |

依赖主链：

```text
T01 → T02 → T03 → T04 → T05
             └────→ T06 → T07
                         ├→ T08 → T16 → T17 → T18
                         ├→ T09 → T10
                         │        └→ T11 → T12 → T13 → T14
                         └→ T19 → T20

T04 + T06 → T21
T10 + T20 → T22
全部任务 → T23
```

## 9. 任务总看板

| 任务 | 状态 | 阶段 | 依赖 | 预计 | 交付结果 |
|---|---|---|---|---:|---|
| T01 配置、启动校验和功能开关 | `completed` | M0 | 无 | 1～2日 | 配置缺失安全失败 |
| T02 ORM、迁移、容量与MySQL基线 | `completed` | M0 | T01 | 2～3日 | 空库可迁移，容量策略冻结 |
| T03 墨灵客户端与verify契约 | `completed` | M1 | T01 | 1～2日 | 平台错误稳定映射 |
| T04 `/enter`、Session与Cookie | `completed` | M1 | T02、T03 | 2～3日 | 真实免登、Cookie恢复和重放防护通过 |
| T05 当前用户、退出和认证Store | `completed` | M1 | T04 | 1～2日 | 当前用户、退出、多标签失效和四档错误页通过 |
| T06 核心表、Repository和租约模型 | `completed` | M2 | T02、T04 | 2～3日 | owner强制过滤，任务可领取 |
| T07 旧接口身份与PersonalDB改造 | `completed` | M2 | T06 | 2～3日 | 客户端伪造user_id无效 |
| T08 持久Worker与重启恢复 | `completed` | M2 | T06 | 2～3日 | 不丢任务、不重复调用Agent |
| T09 作品CRUD API | `completed` | M3 | T06 | 2～3日 | 创建、列表、详情、删除通过 |
| T10 `/works`响应式页面 | `completed` | M3 | T09 | 2～3日 | 四档宽度通过 |
| T11 历史作品加载编辑器 | `completed` | M3 | T09 | 2～3日 | 刷新和换设备恢复 |
| T12 自动保存与离开保护 | `completed` | M4 | T11 | 2～3日 | 正常、断网流程通过 |
| T13 乐观锁、409和另存副本 | `completed` | M4 | T12 | 2～3日 | 多标签不覆盖 |
| T14 检查点版本和恢复 | `completed` | M4 | T13 | 2～3日 | 恢复产生新版本 |
| T15 权益解析和计费策略 | `completed` | M5 | T04、O-01/O-02/O-04 | 2～3日 | 确定性选择权益 |
| T16 计费型任务与request幂等 | `completed` | M5 | T06、T08 | 2～3日 | 重复请求复用任务 |
| T17 reserve/settle/release编排 | `completed` | M5 | T15、T16 | 2～3日 | 三条计费路径通过 |
| T18 billing_pending自动对账 | `completed` | M5/M7 | T17 | 2～3日 | 未知终态可恢复 |
| T19 Storage Adapter与文件表 | `completed` | M6 | T06、O-09 | 2～3日 | 上传、读取、配额通过 |
| T20 PPTX归档、缩略图和下载 | `completed` | M6 | T19 | 2～3日 | 历史下载和越权通过 |
| T21 错误、审计、限流和健康检查 | `completed` | M7 | T04、T06 | 2～3日 | 可观测和安全验收通过 |
| T22 正式构建与Nginx | `completed` | M8 | T10、T20 | 1～2日 | 域名无Vite HMR |
| T23 真实墨灵、积分、多用户UAT | `blocked` | M8 | 全部 | 2～3日 | G5全部通过 |

## 10. 任务卡

### T01 配置、启动校验和功能开关

- 目标：所有新能力有显式配置，缺少必填配置时安全失败且不打印密钥。
- 主要文件：`env_template.txt`、`backend/main_api/core/config.py`、`backend/main_api/main.py`、配置测试。
- 实施：补充墨灵、Session、数据库、存储、计费、端口和功能开关占位符；建立集中配置模型；按功能开关校验依赖。
- 必测：缺失配置、非法布尔值、非法URL、生产Secure Cookie、敏感值不进入异常文本。
- 完成证据：配置键清单、测试输出、`git diff --check`。
- 禁止：复制真实 `.env` 值到模板、日志、测试或文档。

### T02 ORM、迁移、容量与MySQL基线

- 目标：建立可重复升级的数据库基线，并关闭B-04的设计部分。
- 主要文件：`backend/main_api/requirements.txt`、`alembic.ini`、`backend/main_api/migrations/`、`backend/main_api/core/db.py`。
- 实施：加入SQLAlchemy/Alembic；验证MySQL版本；建立空迁移基线；写容量、配额、保留和清理配置。
- 必测：空库升级、重复升级、应用版本回滚不删业务数据、连接失败不泄露URL凭证。
- 完成证据：迁移日志、表清单、容量决策记录。
- Gate：G0不要求生产执行迁移，只要求本地或测试库可重复执行。

### T03 墨灵客户端与verify契约

- 目标：平台调用集中在一个适配器中，业务代码不直接拼接内部API。
- 主要文件：`backend/main_api/integrations/moling.py`、配置模型、契约测试。
- 实施：封装verify、权益查询、余额和计费错误模型；设置连接/读取超时；生成request ID。
- 必测：成功、401/403、平台业务码、超时、非JSON、字段缺失、app/product不匹配。
- 完成证据：Mock契约测试；真实verify结果只记录状态与request ID，不保存ticket。

### T04 `/enter`、Session与Cookie

- 目标：有效ticket建立可信Session，重放和跨站修改失败。
- 主要文件：auth路由、Session模型/Repository/Service、Nginx入口配置。
- 实施：消费ticket；校验app/product；生成随机Session并只存哈希；302到 `/works`；设置no-store/no-referrer；校验Origin或CSRF。
- 必测：缺失、过期、已用、伪造、重放、平台超时、Session过期、Cookie属性、日志脱敏。
- 完成证据：真实入口录屏或请求链、日志扫描、跨站失败测试。

### T05 当前用户、退出和认证Store

- 目标：前端可靠区分已登录、过期和平台错误。
- 主要文件：`frontend/src/services/auth.ts`、`frontend/src/store/auth.ts`、认证初始化、`AuthFailure`页面。
- 实施：`/api/auth/me`、logout、路由守卫、返回墨灵提示；所有请求携带Cookie。
- 必测：首次加载、刷新、401、退出、多标签页Session失效。
- UI：1440/1024/768/390均无横向溢出，错误页操作可见。

### T06 核心表、Repository和任务租约模型

- 目标：所有资源有可信owner，任务具备原子领取的数据条件。
- 主要文件：models、repositories、Alembic迁移、Repository测试。
- 实施：sessions、presentations、versions、tasks、billing、files、exports；owner默认过滤；加入lease字段和索引。
- 必测：跨用户404、软删除、唯一request ID、版本唯一、两个事务只有一个领取任务。
- 完成证据：迁移SQL、索引检查、并发测试输出。

### T07 旧接口身份与PersonalDB改造

- 目标：旧接口继续工作，但客户端不能决定资源归属。
- 主要文件：`backend/main_api/main.py`、PersonalDB Client、前端旧服务调用。
- 实施：从Session读取平台用户；生成复合知识库主体；`sessionId`只保留为生成上下文。
- 必测：伪造user_id、两个用户同名文件、跨环境命名空间、DOCX/PDF/PPTX/TXT支持矩阵。
- 完成证据：真实文件测试报告；未支持格式写明限制和用户提示。

### T08 持久Worker与重启恢复

- 目标：浏览器、API或Worker中断不造成任务丢失和重复Agent调用。
- 主要文件：`backend/main_api/workers/`、task service/repository、启动配置、测试。
- 实施：领取、租约、心跳、超时回收、有限重试、明确失败；Worker单独进程启动。
- 必测：双Worker竞争、领取后崩溃、Agent超时、服务重启、重复投递、超过重试次数。
- 完成证据：任务状态时间线和Agent调用计数。

### T09 作品CRUD API

- 目标：提供带owner隔离的作品创建、列表、详情、删除和复制能力。
- 主要文件：presentation API/schema/service/repository。
- 实施：分页、搜索、状态筛选、排序；幂等软删除；他人资源统一404。
- 必测：空列表、边界页码、超长标题、删除重复调用、跨用户访问。
- 完成证据：OpenAPI、API集成测试和示例响应。

### T10 `/works`响应式页面

- 目标：用户能找到、搜索和管理自己的历史作品。
- 主要文件：`frontend/src/views/Works/`、presentation service/store、router。
- 实施：卡片、状态、分页/加载、搜索、筛选、删除确认、空态和错误态。
- 必测：四档宽度；加载、空、失败、生成中、计费待处理、已删除状态。
- 完成证据：12个页面状态截图和浏览器控制台无错误。

### T11 历史作品加载编辑器

- 目标：`/editor/:presentationId`刷新和换设备可恢复。
- 主要文件：router、Editor入口、slides store、presentation service。
- 实施：按ID加载；显示加载/404/失败；兼容迁移期旧路由。
- 必测：直接URL、刷新、他人ID、删除ID、10MiB边界稿。
- 完成证据：双浏览器或双设备恢复结果。

### T12 自动保存与离开保护

- 目标：编辑后稳定保存，断网时保留本地草稿。
- 主要文件：`usePresentationAutosave.ts`、编辑Store、IndexedDB草稿、PATCH API。
- 实施：2秒防抖；单请求在途；手动保存；失败提示；离开保护；恢复网络后由用户确认重试。
- 必测：连续输入、慢请求、断网、刷新、关闭再打开、保存中离开。
- 完成证据：网络请求时间线和草稿恢复测试。

### T13 乐观锁、409和另存副本

- 目标：多标签页和多设备不会静默覆盖作品。
- 主要文件：保存Service/API、冲突对话框、duplicate接口。
- 实施：客户端提交version；后端条件更新；409返回最新版本摘要；加载最新或另存副本。
- 必测：两个标签同版本保存、冲突后重试、另存副本owner和版本初始化。
- 完成证据：并发测试和UI操作记录。

### T14 检查点版本和恢复

- 目标：手动保存、AI操作、导出和周期节点可恢复历史。
- 主要文件：version model/service/API、版本面板。
- 实施：检查点原因；恢复生成新版本；容量阈值；最近20个与清理策略。
- 必测：唯一版本、恢复不覆盖历史、清理保留最新、超限行为。
- 完成证据：版本链和恢复后的slides哈希。

### T15 权益解析和计费策略

- 前置：O-01、O-02、O-04必须关闭。
- 目标：稳定选择当前商品的可用权益，正确处理不限量和不足。
- 主要文件：Moling Client、billing policy/service、配置、契约测试。
- 实施：active/usable过滤；最早过期优先；第一版不拆分多个权益；余额仅作UX提示。
- 必测：无权益、多个权益、过期、剩余不足、不限量、平台并发拒绝。
- 完成证据：选择矩阵和真实只读余额验证。

### T16 计费型任务与request幂等

- 目标：重复点击、网络重试和前端刷新只产生一个收费任务。
- 主要文件：generation orchestrator、task API/service、幂等测试。
- 实施：request ID唯一；同请求返回原任务；任务关联作品、用户和后续计费记录。
- 必测：并发重复POST、超时重试、Worker重复投递、不同用户相同客户端request值。
- 完成证据：数据库唯一记录和Agent调用计数。

### T17 reserve/settle/release编排

- 目标：成功只结算一次，失败只释放一次，额度不足不调用Agent。
- 主要文件：billing service/repository、GenerationOrchestrator、Moling Client。
- 实施：reserve后运行；持久化成功后settle；失败release；三类幂等键独立。
- 必测：成功、生成失败、持久化失败、额度不足、重复响应、平台超时。
- 完成证据：Mock全路径；生产开关仍关闭。

### T18 billing_pending自动对账

- 目标：平台终态未知时可恢复，不向用户虚假承诺退款或成功。
- 主要文件：reconciliation worker、billing operations、任务查询。
- 实施：指数退避、最大重试、人工可查询状态；不重复reserve。
- 必测：settle超时但平台已成功、release超时、服务重启、达到最大重试。
- 完成证据：对账状态时间线和平台最终记录。

### T19 Storage Adapter与文件表

- 前置：O-09必须关闭，存储endpoint连通性已验证。
- 目标：对象key、归属、配额和厂商差异集中管理。
- 主要文件：storage integration、files/exports model/repository、迁移。
- 实施：服务端生成key；MIME/签名/大小/SHA-256；短期地址或API代理下载由部署拓扑决定。
- 必测：上传、重复哈希、超限、路径穿越、存储超时、跨用户读取。
- 完成证据：真实对象存储最小写读删测试，不记录凭证。

### T20 PPTX归档、缩略图和下载

- 目标：用户可以再次下载与当时本地导出字节一致的PPTX。
- 主要文件：`useExport.ts`、export API/service、缩略图、下载鉴权。
- 实施：PptxGenJS生成Blob；计算SHA-256；本地下载和上传同一Blob；失败可幂等重试。
- 必测：本地成功归档失败、重复上传、软删除、签名URL过期、跨用户下载。
- 完成证据：服务端和本地文件哈希一致，Microsoft PowerPoint实际打开。

### T21 错误、审计、限流和健康检查

- 目标：故障可以定位，敏感值不泄露，关键接口不能被无限调用。
- 主要文件：core/error、request_id、audit、rate_limit、health路由和运维说明。
- 实施：中文用户消息、稳定错误码、retryable、request ID；用户级限流；依赖健康检查。
- 必测：日志秘密扫描、429、下游超时、数据库/存储/墨灵/Agent/PersonalDB故障。
- 完成证据：错误矩阵、结构化日志样例和告警阈值。

### T22 正式构建与Nginx

- 目标：正式域名只提供静态构建，不再暴露Vite开发客户端。
- 主要文件：frontend构建、Nginx配置、部署说明。
- 实施：`/enter`和`/api`代理；history回退；Secure Cookie；可信代理头；静态缓存策略。
- 必测：直接访问 `/works` 和 `/editor/:id`；无HMR WebSocket；HTTPS、CORS和Cookie正确。
- 完成证据：生产构建摘要、Nginx配置检查和浏览器控制台记录。

### T23 真实墨灵、积分、多用户UAT

- 目标：使用真实入口、真实权益、真实存储和实际PPTX完成发布验收。
- 主要文件：UAT报告和发布清单，不以修改业务代码代替缺陷修复任务。
- 实施：两个用户；成功结算、失败释放、重复请求、未知终态；历史编辑和下载；四档UI。
- 必测：G0～G5全部证据；测试结果区分自动化、Mock、真实平台和人工视觉。
- 完成证据：签字验收报告、积分前后记录、跨用户隔离、PowerPoint打开结果。

## 11. 通用验证命令

以下命令以Windows PowerShell为准。运行前确认当前目录是项目根目录。

### 11.1 工作区检查

```powershell
git status --short
git diff --check
```

### 11.2 前端静态验证

```powershell
Set-Location frontend
npm.cmd run type-check
npm.cmd run build
```

`npm.cmd run lint` 当前带 `--fix`，会修改文件。只有任务明确包含格式修复时才运行。

### 11.3 Python测试

```powershell
python -m pytest backend/personaldb/test_markitdown_converter.py -q
python -m pytest backend/main_api -q
```

如果目录没有可收集测试，必须新增当前任务测试，不能把“0 tests collected”当成通过。

### 11.4 服务健康检查

```powershell
Invoke-WebRequest http://127.0.0.1:6800/healthz -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:10001/.well-known/agent.json -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:10011/.well-known/agent.json -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5778/ -UseBasicParsing
```

PersonalDB只有在服务实际提供对应健康端点后才能加入统一健康检查。端口监听不等于文件转换和Embedding可用。

### 11.5 启动方式

```powershell
python start.py
```

根启动器当前管理主API、大纲Agent、内容Agent、PersonalDB和前端。启动前必须确认端口占用进程属于本项目，不能直接停止未知进程。

## 12. 测试证据要求

每个任务至少保存以下证据：

| 证据 | 必填内容 |
|---|---|
| 代码范围 | 实际修改文件，排除无关工作区修改 |
| 自动化 | 命令、通过数、失败数、退出码 |
| 接口 | 请求类型、状态码、稳定错误码、request ID |
| 数据 | 迁移版本、关键记录数、约束或索引验证 |
| 外部系统 | Mock或真实，明确环境和验证边界 |
| UI | 设备宽度、页面状态、控制台错误 |
| 文件 | 大小、SHA-256、PowerPoint实际打开结果 |
| 安全 | 越权、重放、日志秘密扫描、路径穿越 |

证据记录格式：

```markdown
### YYYY-MM-DD Txx 验证记录

- 状态：completed / blocked
- 修改文件：
- 自动化命令：
- 自动化结果：
- 真实验证：
- 未验证边界：
- 风险与回滚：
- 下一任务：
```

## 13. Gate清单

### G0 基线

- [x] T01、T02完成。
- [x] B-01～B-08均有明确关闭路径。
- [x] `.env`未被Git跟踪，模板无真实密钥。
- [x] 主题生成、现有编辑和本地PPTX导出回归通过。
- [x] 文件支持矩阵区分真实通过和已知限制。
- [x] MySQL和对象存储完成最小连通验证。

G0于2026-07-23通过；证据见T01/T02验证记录及`molin_docs/TrainPPTAgent文件能力与G0回归基线.md`。依据文件端到端生成仍是B-06后续关闭项，不把本次长调用无终态写成通过。

### G1 身份

- [x] 有效ticket只消费一次。
- [x] 地址栏、Referrer和日志无完整ticket。
- [x] app/product不匹配不能创建Session。
- [x] Session过期、退出和跨站修改测试通过。

G1于2026-07-23通过；真实ticket、当前用户、恶意Origin、退出、Cookie清理和另一标签失效证据见T04/T05验证记录。生产Secure Cookie、真实MySQL迁移与Nginx/Docker仍属于T22/T23发布验收边界，不在G1伪称通过。

### G2 数据与编辑

- [x] 两用户作品、文件、任务完全隔离。
- [x] Worker重启不丢任务、不盲目重复调用Agent。
- [x] 作品刷新和换设备可恢复。
- [x] 自动保存、多标签冲突和版本恢复通过。

G2已于2026-07-23通过；两用户作品/任务隔离、复合PersonalDB文件隔离和Worker恢复证据分别见T06～T09记录，作品刷新与换设备恢复见T11，自动保存与断网草稿见T12，多标签冲突见T13，检查点恢复与容量见T14。该Gate只放行作品历史与编辑数据链路，不代表生产MySQL、真实墨灵、计费、对象存储或最终发布已验收。

### G3 计费

- [x] 成功只有一次reserve和settle。
- [x] 失败release且额度不增加使用量。
- [x] 额度不足不调用Agent。
- [x] 重复request不重复任务和扣费。
- [x] billing_pending对账恢复通过。

G3已于2026-07-23通过本地代码与契约Gate：T16～T18以真实SQLite状态机和Fake/Mock平台账本证明幂等、失败补偿、未知终态恢复及并发单赢家。该Gate只允许进入真实计费验收准备；没有执行真实墨灵写入，也不代表真实积分流水验收。`BILLING_ENABLED=false`、`TASK_WORKER_ENABLED=false`继续保持，真实积分与应用记录一致性仍由T23/G5关闭。

### G4 文件

- [x] 同一Blob本地下载和归档哈希一致。
- [x] 跨用户、软删除和过期地址不能下载。
- [x] 历史PPTX可再次下载并实际打开。

G4于2026-07-23通过：T20以浏览器同一Blob本地保存与归档、真实对象存储历史回读、服务端与本地SHA-256一致、owner/软删除/严格过期410契约及Microsoft PowerPoint只读实际打开形成证据。该Gate不代表正式域名、生产MySQL、真实墨灵积分或最终两个真实用户UAT通过；这些仍由T22/T23关闭。

### G5 发布

- [ ] 正式域名不加载Vite HMR。
- [ ] 真实墨灵入口完整走通。
- [ ] 真实积分记录与应用记录一致。
- [ ] 四档UI和两个真实用户隔离通过。
- [ ] 回滚与值班清单可执行。

## 14. 回滚规则

1. SSO、持久化、计费和对象存储分别受功能开关控制。
2. 数据库迁移第一期只向前新增；应用回滚不自动删除生产表和数据。
3. 计费故障先关闭新收费任务，再处理reserved和billing_pending。
4. 文件故障暂停新归档，不批量删除已有对象。
5. 身份故障将入口切到维护页，不允许匿名进入收费能力。
6. 每个任务卡完成前必须写明本任务的最小回滚动作。

## 15. 项目完成定义

只有以下条件全部满足，整个项目Goal才能标记完成：

1. T01～T23全部为 `completed`。
2. B-01～B-08全部为 `closed` 或通过明确缩减范围关闭。
3. O-01～O-09在需要生产的范围内全部确认。
4. G0～G5全部通过且有证据。
5. 用户能从墨灵进入、生成、找到、编辑、保存、导出并再次下载PPT。
6. 多用户隔离、真实积分、真实对象存储和PowerPoint打开均完成验收。
7. 生产页面不依赖Vite开发服务。
8. 文档、迁移、配置模板、部署和回滚说明与实际实现一致。

## 16. 执行记录

当前尚未开始业务开发。

### 2026-07-22 文档基线

- 状态：completed
- 工作内容：建立Goal执行主文档。
- 代码修改：无。
- 当前任务：T01。
- 当前Gate：G0。
- 下一步：创建新Goal，执行T01配置、启动校验和功能开关。

### 2026-07-23 T01 验证记录

- 状态：`completed`。
- 修改文件：`env_template.txt`、`backend/main_api/core/__init__.py`、`backend/main_api/core/config.py`、`backend/main_api/main.py`、`backend/main_api/tests/test_config.py`、本执行主文档。
- 配置键清单：墨灵与应用身份（`MOLING_API_BASE_URL`、`INTERNAL_API_TOKEN`、`MOLING_APP_ID`、`MOLING_PRODUCT_ID`）；Session（`SESSION_SECRET`、Cookie、TTL）；数据库与存储；积分占位符与对账间隔；五个服务端口；`SSO_ENABLED`、`PERSISTENCE_ENABLED`、`STORAGE_ENABLED`、`BILLING_ENABLED` 四个开关。
- TDD红灯：首次运行配置测试因 `backend.main_api.core` 不存在产生1个收集错误；审查补测后越界端口和空白主机产生2个预期失败；均在最小实现后转绿。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_config.py -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；FastAPI `TestClient` 请求 `/healthz`；缺配置子进程导入检查；`git diff --check`；T01交付文件疑似密钥模式扫描。
- 自动化结果：配置测试13通过、0失败；Python编译退出码0；`/healthz` 返回HTTP 200和`{"ok": true}`；缺失SSO配置时主API导入退出码1且错误只包含缺失键名；交付文件密钥扫描无命中；`git diff --check`退出码0（仅工作区既有LF/CRLF提示）。
- 真实验证：使用当前本地`.env`导入主API成功，确认`SSO_ENABLED=false`、`BILLING_ENABLED=false`；这是本地启动配置验证，不是端口监听、真实墨灵或生产验收。
- 安全与审查：非法布尔、非法协议、越界端口、空白主机、生产非Secure Cookie、功能依赖和敏感值不回显均有测试；Standards轴最终0项，Spec轴发现的1项URL边界问题已修复，复审0项。
- 阻塞项：B-03保持`open`，T01只冻结配置模型行为且没有新增业务API；B-06保持`open`，未把Mock、本地导入或健康检查写成文件转换、Embedding、检索和依据文件生成验收。
- 未验证边界：未调用真实墨灵、MySQL、对象存储或计费；未验证PersonalDB格式矩阵、Embedding和依据文件生成；未执行浏览器视觉、PPTX生成或PowerPoint打开。本任务无前端页面，不涉及四档UI。
- 风险与回滚：关闭四个新功能开关即可停止进入新链路；如需代码回滚，仅还原T01列出的配置接入文件并删除新增配置测试/模块，不执行数据删除、迁移降级或外部资源操作。
- 下一任务：`T02`；G0继续保持未通过，禁止进入SSO开发。

### 2026-07-23 T02 验证记录

- 状态：`completed`；G0已通过，允许进入M1的T03。
- 修改文件：`backend/main_api/requirements.txt`、`backend/main_api/core/config.py`、`backend/main_api/core/db.py`、`backend/main_api/tests/test_capacity_config.py`、`backend/main_api/tests/test_db_and_migrations.py`、`alembic.ini`、`backend/main_api/migrations/`、`env_template.txt`、`molin_docs/TrainPPTAgent持久任务租约与容量基线.md`、`molin_docs/TrainPPTAgent文件能力与G0回归基线.md`、本执行主文档；`output/g0/`和`output/playwright/`仅保存隔离验证脚本、样例与截图。
- TDD红灯：数据库模块缺失时测试收集失败；缺少Alembic/PyMySQL时3项失败；容量字段未实现时6项失败；审查补测发现非MySQL方言仍可进入部署工厂时1项失败。各红灯均以最小实现转绿。
- 自动化命令：`.venv312\\Scripts\\python.exe -m pytest backend/main_api -q`；`.venv312\\Scripts\\python.exe -m compileall -q backend/main_api`；`.venv312\\Scripts\\alembic.exe -c alembic.ini history`；隔离SQLite重复升级/降级；MySQL方言离线SQL；应用启动不自动迁移；`git diff --check`。
- 自动化结果：34通过、0失败；编译退出码0；迁移历史为`<base> -> 20260723_0001 (head)`；隔离空库重复升级后仅有`alembic_version`，降级保留哨兵业务表和数据；MySQL离线SQL创建版本表且不含`DROP TABLE`；应用导入不自动建表或删表。`git diff --check`退出码0（仅既有LF/CRLF提示）。
- 容量与租约：单作品JSON 10MiB、检查点20个/单个内联1MiB、上传50MiB、PPTX 100MiB、缩略图2MiB、软删除30天、清理批次100；用户总作品/存储配额保持未配置，等待O-09。租约120秒、心跳30秒、最大3次、退避30秒、领取批次10；以`lock_token` fencing和条件更新防止旧Worker提交，语义为at-least-once而非伪称exactly-once。
- 真实验证：使用当前`.env`对现有MySQL只读执行`SELECT 1`和版本检查成功，版本MySQL 8.0.46；未执行真实库迁移。对象存储以现有凭据只读`HeadBucket`返回HTTP 200，未写删对象；endpoint为HTTP，不能当作生产TLS验收。真实DeepSeek大纲/正文生成、四格式转换/Embedding/检索、浏览器编辑器、本地导出和PowerPoint实际打开结果详见G0文件能力报告。
- 安全与审查：部署连接工厂只接受MySQL并规范到PyMySQL；SQLite仅由隔离测试显式放行；连接错误和配置错误不回显URL或凭据；应用启动不自动迁移。Standards轴发现的Engine所有权、测试释放和子进程环境隔离问题均修复，最终0项；Spec轴发现的方言与迁移边界问题均修复，最终0项。
- 阻塞项：B-01、B-04进入`design_frozen`，实现证据分别由T06/T08和T14/T19补齐；B-06为`partial_verified`，主API依据文件串联长调用无终态，未伪造通过；O-06采用可配置的30天软删除默认值，O-09仍保持`open`。
- 未验证边界：未在真实MySQL执行迁移或锁竞争；未做对象存储写读删；未验证真实墨灵、生产计费、多用户隔离、任务重启恢复和生成PPT逐页视觉。本任务无新增前端页面，不涉及四档UI验收。
- 风险与回滚：保持`PERSISTENCE_ENABLED=false`可阻止进入新持久化链路；空迁移不含业务表，回滚仅降级版本标记并禁止删除业务数据；移除新增依赖/模块前先确认后续任务未引用。没有执行commit、push、部署、生产流量或生产计费操作。
- 下一任务：`T03`，当前Gate为G1。

### 2026-07-23 T03 验证记录

- 状态：`completed`；已自动推进T04，G1仍在进行中。
- 修改文件：`backend/main_api/integrations/__init__.py`、`backend/main_api/integrations/moling.py`、`backend/main_api/tests/test_moling_client.py`、`backend/main_api/core/config.py`、`backend/main_api/tests/test_config.py`、`env_template.txt`、本执行主文档。
- 公开契约：`MolingClient`集中封装一次性票据verify、用户权益列表和只读余额；统一发送`X-Internal-Token`与本地生成的`X-Request-Id`。verify只调用一次，超时或传输失败时不自动重放同一票据。`LaunchClaims`强制正整数身份并校验配置的app/product；权益金额只接受非负、最多六位小数的decimal字符串，`null`保留不限量语义。
- TDD红灯：客户端模块不存在时测试收集失败；超时配置缺失时4项失败；HTML鉴权响应和缺`message`信封时2项失败；RemoteProtocolError未映射时1项失败；审查补测的traceback脱敏和非法decimal产生6项失败。全部以最小实现转绿。
- 自动化命令：`.venv312\\Scripts\\python.exe -m pytest backend/main_api/tests/test_moling_client.py -q`；`.venv312\\Scripts\\python.exe -m pytest backend/main_api -q`；`.venv312\\Scripts\\python.exe -m compileall -q backend/main_api`；`git diff --check`。
- 自动化结果：T03客户端契约22通过；主API回归60通过、0失败；Python编译和`git diff --check`退出码0（仅既有LF/CRLF提示）。覆盖成功、HTTP 401/403及HTML正文、平台`40003`/业务码、超时、传输协议失败、5xx分类、非JSON、信封/身份字段缺失、app/product不匹配、权益列表/余额和非法decimal。
- 真实验证：当前配置指向的墨灵平台`GET /api/health`返回HTTP 200，并带request ID响应头；这是只读连通证据。当前环境没有可安全复用的一次性launch ticket，因此没有调用真实verify，也没有把健康检查写成verify通过。
- 安全与审查：异常消息不包含下游正文、URL、票据或内部令牌；外部RequestError、JSON与Pydantic异常均以`from None`截断，完整traceback脱敏有测试。Standards轴最初发现异常链泄漏与decimal约束2项、Spec轴发现decimal约束1项，均修复并最终复审0项。
- 阻塞项：B-03已补充T03客户端契约证据但仍保持`open`，后续业务API继续逐项冻结；B-05仍保持`open`，Session、票据日志、Origin/CSRF和退出由T04、T05、T21关闭。
- 未验证边界：未消费真实票据，未查询真实用户权益/余额，未执行任何reserve/settle/release/consume；`SSO_ENABLED`和`BILLING_ENABLED`仍为false。本任务无前端页面，不涉及四档UI。
- 风险与回滚：保持`SSO_ENABLED=false`即可不进入墨灵身份链路；回滚只移除T03适配器和超时配置，不触碰平台、数据库、用户会话或计费数据。未commit、push、部署或切换生产流量。
- 下一任务：`T04`，当前Gate为G1。

### 2026-07-23 T04 验证记录

- 状态：`completed`。本地代码、契约测试、回归、双轴审查和真实墨灵ticket请求链均通过；已推进T05，G1继续进行中。
- 修改文件：`backend/main_api/api/auth.py`、`backend/main_api/models/auth.py`、`backend/main_api/repositories/sessions.py`、`backend/main_api/services/auth.py`、`backend/main_api/core/security.py`、`backend/main_api/core/config.py`、`backend/main_api/main.py`、`backend/main_api/Dockerfile`、`backend/main_api/migrations/versions/20260723_0002_app_sessions.py`、`backend/main_api/tools/moling_auth_preflight.py`、`backend/main_api/tests/test_session_auth.py`、`backend/main_api/tests/test_config.py`、`backend/main_api/tests/test_moling_auth_preflight.py`、`env_template.txt`、`frontend/nginx.conf`、`molin_docs/TrainPPTAgent-Session安全契约.md`、`output/t04/real_entry_harness.py`、本执行主文档。
- 公开契约：`/enter`只消费一次ticket，成功302到`/works`；Session原值仅入HttpOnly/SameSite=Lax Cookie，数据库只存SHA-256摘要；绝对有效期24小时、空闲有效期2小时且可配置；同浏览器重新登录撤销旧Cookie Session并保留其他设备Session；错误响应统一no-store/no-referrer且失败不建Session。
- TDD红灯：Session模块缺失时测试收集失败；迁移、非法票据/协议错误、缺失结构、Session表示脱敏、乱序touch、SSO持久化依赖、同浏览器轮换和访问日志边界均先出现预期失败，再以最小实现转绿。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_session_auth.py backend/main_api/tests/test_config.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\alembic.exe -c alembic.ini history`；Nginx精确路由/括号结构检查；`git diff --check`。
- 自动化结果：T04定向42通过、只读主闸预检4通过、后端全量89通过、0失败；仅1条FastAPI TestClient依赖弃用告警。编译和差异空白检查退出码0；迁移历史为`20260723_0001 -> 20260723_0002 (head)`；Nginx结构检查通过。当前机器没有Nginx和Docker，未把结构检查写成真实`nginx -t`或容器验收。
- 安全与审查：ticket缺失、空白、超长和控制字符在平台调用前拒绝；过期、伪造、重放、app/product错域、平台超时/协议异常、Session绝对/空闲过期、撤销、Cookie属性、Origin精确匹配、日志脱敏均有测试。SSO开启时Uvicorn访问日志关闭，Nginx对`/enter`关闭访问日志。Standards轴和Spec轴复审均为0个本地阻塞问题。
- 真实验证：只读`user-entitlements`哨兵查询返回鉴权已接受，证明当前Token/IP主闸可用，且未消费ticket、创建Session或扣费。随后使用现有Chrome登录态从商品73签发新ticket并立即送入真实`MolingClient`：`/enter`返回302到`/works`，响应Cookie可恢复Session并返回HTTP 200，同一ticket重放返回HTTP 401；响应含no-store/no-referrer且不含ticket。ticket未写入文档、测试、控制台或应用日志，验收后已从浏览器地址和临时运行内存清除。
- 阻塞项：`T04-BLK-01`已关闭。根因是先前人工从浏览器历史提取导致的旧票据/60秒时效问题，不是Token/IP白名单；新增只读主闸预检将两类失败分离。
- 未验证边界：未在真实MySQL执行T04迁移或写入Session；未执行真实Nginx配置测试；未验证T05退出。真实联调使用本机HTTP门面，生产Secure Cookie属性由自动化测试而非公网部署证明。T04没有新增页面，不涉及四档UI视觉验收；`SSO_ENABLED`和`BILLING_ENABLED`保持false。隔离`output/t04/real-entry.db`含一条真实Session哈希记录，门面已关闭且原始Cookie已清除，但删除被环境策略拒绝，需人工清理。
- 风险与回滚：保持`SSO_ENABLED=false`即可停止新身份链路；代码回滚可移除T04路由/服务/Repository并保留`app_sessions`表，不删除用户数据。没有commit、push、部署、生产流量切换或生产计费操作。
- 下一任务：`T05`；T04依赖已满足，G1仍需T05的当前用户、退出和认证Store证据后才能通过。

### 2026-07-23 T05 验证记录

- 状态：`completed`；G1已通过，已按固定顺序推进M2的T06。
- 修改文件：`backend/main_api/api/auth.py`、`backend/main_api/services/auth.py`、`backend/main_api/core/security.py`、`backend/main_api/core/config.py`、`backend/main_api/main.py`、`backend/main_api/tests/test_current_user_auth.py`、`backend/main_api/tests/test_session_auth.py`、`backend/main_api/tests/test_config.py`、`frontend/src/services/auth.ts`、`frontend/src/services/authConfig.ts`、`frontend/src/store/auth.ts`、`frontend/src/store/index.ts`、`frontend/src/router/authGuard.ts`、`frontend/src/router/index.ts`、`frontend/src/main.ts`、`frontend/src/App.vue`、`frontend/src/views/AuthFailure/index.vue`、`frontend/src/components/AuthSessionControl.vue`、对应前端测试、`frontend/vitest.config.ts`、`frontend/package.json`、`frontend/package-lock.json`、`frontend/.env.example`、`.gitignore`、本执行主文档和Session安全契约。
- 公开契约：浏览器外部调用`GET /api/auth/me`和`POST /api/auth/logout`，Vite/Nginx只移除一次`/api`后到后端`/auth/*`；身份只从HttpOnly Session读取；logout精确校验规范化Origin并仅撤销当前设备；HTML入口错误跳转到无ticket的AuthFailure，API调用保留原401/403/502/503状态码。
- TDD红灯：后端在未实现可信Origin参数和当前用户/退出路由时出现6个预期错误；前端认证服务、Store和守卫缺失时3个测试套件收集失败；真实浏览器首次测得1440视口文档宽1632；审查补测捕获永久缓存身份和退出后旧`/me`响应复活2项失败。均以最小实现转绿。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run type-check`；`npm.cmd run build`；`git diff --check`；Playwright四档resize/overflow/screenshot、按钮交互与console检查。
- 自动化结果：后端100通过、0失败；前端18通过、0失败；Vue类型检查和生产构建退出码0。构建仍有既有主chunk大于500kB提示，不影响本任务正确性但由T22评估拆包。`git diff --check`退出码0，仅既有LF/CRLF提示。
- 前端状态：SSO默认关闭，保持旧开发流程；开启后每次受保护导航和标签重新可见均强制`/me`，认证epoch阻止退出/跨标签失效后迟到的旧响应复活。全局退出控件在进行中或失败时保持可见，成功后才清空身份；重试、返回墨灵和退出按钮均有可观察反馈。
- 四档UI：AuthFailure在1440、1024、768、390宽度的`documentElement.scrollWidth <= innerWidth`均为true，按钮完整可见；截图为`output/playwright/t05-auth-1440.png`、`t05-auth-1024.png`、`t05-auth-768.png`、`t05-auth-390.png`。点击前控制台0错误/0警告；静态preview点击重试因无反向代理产生的`/api/auth/me` 404仅作为失败态交互验证，不写成生产控制台通过。退出控件交互由组件/Store测试覆盖，未伪造登录态视觉截图。
- 真实验证：从墨灵商品73签发新ticket并立即建立本地隔离Session；`/auth/me`返回HTTP 200且只含三项身份字段；恶意Origin logout返回403且随后`/me`仍200；使用当前配置规范化Origin logout返回204、删除Cookie，模拟另一标签持有旧Cookie再请求`/me`返回401。未输出或保存ticket、Cookie及真实用户ID，验收后地址与临时变量已清理，门面已关闭。
- 安全与审查：开放重定向仅允许单斜杠站内路径；HTML错误重定向不携带ticket；错误信息不包含网络正文；退出只撤销当前设备。Standards轴最初发现永久身份缓存与旧响应竞态2项，Spec轴发现缺少退出入口与相同缓存问题2项；修复后又发现退出失败控件消失1项并修复，最终两轴均0个本地阻塞。
- 阻塞项：B-05保持`partial_verified`，身份/Session/CSRF部分已通过，T21仍需补审计、限流和安全运维证据。T05无外部阻塞。
- 未验证边界：未在真实MySQL执行Session迁移；生产Secure Cookie仅由自动化证明；没有真实Nginx/Docker和公网构建验收。当前本机`APP_BASE_URL`与公网应用origin不一致，T22/T23部署前必须按实际公网origin配置；`VITE_MOLING_PORTAL_URL`也需填真实墨灵返回地址。隔离`output/t04/real-entry.db`仍含已撤销Session哈希，删除被环境策略拒绝，需人工清理。
- 风险与回滚：`VITE_SSO_ENABLED=false`和`SSO_ENABLED=false`可分别关闭前后端身份链路；回滚移除T05前端认证模块和`/auth/me`、`/auth/logout`，保留Session表及数据。未commit、push、部署、切换生产流量或开启计费。
- 下一任务：`T06`，当前Gate为G2-A。

### 2026-07-23 T06 验证记录

- 状态：`completed`；已按固定顺序推进M2的T07，G2尚未通过。
- 修改文件：`backend/main_api/models/domain.py`、`backend/main_api/models/__init__.py`、`backend/main_api/repositories/resources.py`、`backend/main_api/repositories/tasks.py`、`backend/main_api/migrations/versions/20260723_0003_core_resources.py`、`backend/main_api/tests/test_core_persistence.py`、`backend/main_api/tests/test_db_and_migrations.py`、本执行主文档。
- 数据契约：新增`presentations`、`presentation_versions`、`generation_tasks`、`billing_operations`、`files`、`exports`六张核心表；作品、任务、文件、导出和计费记录直接带`owner_user_id`，版本通过未删除作品联结校验owner。作品使用软删除，`request_id`和`(presentation_id, version)`由数据库唯一约束兜底；编辑稿、版本和任务输入在MySQL使用`LONGTEXT`。
- 租约契约：任务最小字段包含`status`、`attempt`、`next_attempt_at`、`locked_by`、`lock_token`、`locked_until`、`heartbeat_at`、`last_error_code`。MySQL 8候选查询编译为`FOR UPDATE SKIP LOCKED`；其他方言以`status + next_attempt_at + locked_until + attempt`条件更新竞争。领取事务提交后才返回随机令牌；续租、成功和失败终态均匹配`task_id + running + lock_token + 未过期租约`，令牌不会出现在对象表示中。语义保持“至少一次领取 + 带围栏终态”，未宣称外部Agent严格一次。
- TDD红灯：首次运行`test_core_persistence.py`因`backend.main_api.models.domain`不存在产生1个收集错误；随后以最小模型、仓储、迁移和租约实现转绿。补测了从属版本owner、失败终态围栏、有效租期不可覆盖、MySQL SKIP LOCKED和真实Alembic索引。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_core_persistence.py backend/main_api/tests/test_db_and_migrations.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\alembic.exe -c alembic.ini history`；`git diff --check`。
- 自动化结果：T06定向16通过、0失败；后端全量110通过、0失败，仅1条既有Starlette TestClient弃用告警；Python编译和差异空白检查退出码0（仅既有LF/CRLF提示）。迁移历史为`20260723_0002 -> 20260723_0003 (head)`。
- 数据与并发证据：隔离SQLite从空库真实升级到head后检查六张表、owner联合索引、任务领取索引、request唯一约束和版本唯一约束均存在；两个独立连接/事务并发领取同一任务只产生1个有效租约。MySQL方言离线迁移SQL包含`LONGTEXT`、`ix_presentations_owner_deleted_updated`和`ix_generation_tasks_claim`，候选SQL包含`FOR UPDATE SKIP LOCKED`。
- 安全与审查：跨用户读取作品、版本、任务和文件均返回与不存在相同的仓储未找到语义，供T09 API统一映射404；外部owner输入不能改变查询作用域。软删除后默认查询不可见，其他用户不能删除；有效租期、错误令牌和旧令牌均不能续租或提交终态。当前任务差异复核未发现阻塞项。
- 阻塞项：B-01由`design_frozen`推进为`partial_verified`；T06已具备持久任务数据条件和原子竞争证据，仍需T08证明崩溃回收、重启恢复、有限重试、死信以及Agent不被重复调用。B-08仍为`open`，T06只固化内部owner数据，复合PersonalDB命名空间和跨用户文件验证由T07完成。
- 真实验证：没有在现有真实MySQL执行迁移、建表或锁竞争，也没有写入生产数据；当前MySQL 8.0.46能力来自T02只读基线，本任务只完成SQLite真实迁移/事务竞争和MySQL方言SQL证据，未将离线SQL写成真实库验收。
- 未验证边界：未实现T08 Worker循环、超时回收、重试和重启恢复；未实现T09业务HTTP路由，因此跨用户HTTP 404将在T09验证，本任务证明的是默认owner仓储未找到语义。没有对象存储写读删、真实墨灵变更、计费动作、UI或PPTX/PowerPoint验证；`PERSISTENCE_ENABLED`和`BILLING_ENABLED`保持false。
- 风险与回滚：保持`PERSISTENCE_ENABLED=false`可阻止新持久化流量；应用代码可回滚且保留新增表。生产回滚禁止自动执行`downgrade`或删除表/数据；迁移故障应停止后续写入并人工按迁移证据处理。未commit、push、部署、切换流量或开启生产计费。
- 下一任务：`T07`，当前Gate仍为G2-A；T07依赖已满足并立即开始。

### 2026-07-23 T07 验证记录

- 状态：`completed`；已按固定顺序推进M2的T08，G2-A仍需T08的Worker重启恢复证据。
- 修改文件：`backend/main_api/core/identity.py`、`backend/main_api/main.py`、`backend/main_api/outline_client.py`、`backend/main_api/content_client.py`、`backend/main_api/tests/test_legacy_identity.py`、`backend/personaldb/namespace.py`、`backend/personaldb/security.py`、`backend/personaldb/main.py`、`backend/personaldb/embedding_utils.py`、`backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py`、`cache_utils.py`、`tools.py`、`frontend/src/services/index.ts`、`frontend/src/views/Outline/index.vue`、`frontend/src/services/__tests__/legacyIdentity.spec.ts`、`output/t07/verify_personaldb_namespace.py`、`output/t07/verify_legacy_generation.py`、`molin_docs/TrainPPTAgent文件能力与G0回归基线.md`、本执行主文档。
- 身份契约：SSO开启时，旧`/tools/aippt_outline`、`/tools/aippt_outline_from_file`、`/tools/aippt`、`/tools/aippt_by_id`和`/files/{user_id}`统一通过同步FastAPI依赖从HttpOnly Session取得主体，数据库读取在线程池执行；query、form或JSON中的`user_id`不参与owner。SSO关闭时使用固定`local:<environment>:trainppt`主体保持单机旧流程。旧`sessionId`只在符合长度/字符约束时作为Agent context ID，不能改变知识库主体。
- PersonalDB契约：墨灵知识库主体为`moling:<environment>:<app_id>:<user_id>`；复合主体用SHA-256摘要映射为符合Chroma命名限制的集合名，旧数字集合`user_<id>`保持兼容。文件列表兼容旧元数据把数字保存为int或字符串的差异；环境、应用或用户任一维度变化都会产生不同集合。B-08已关闭。
- 上传与错误边界：主API忽略旧表单`user_id`，文件/URL必须二选一，只允许TXT、DOCX、PDF、PPTX，文件上限使用已冻结的50MiB配置，文件ID由服务端UUID生成；路径、反斜杠、控制字符和超长文件名不能逃逸PersonalDB临时目录。PersonalDB超时、连接、状态码和协议错误返回稳定中文信息，不透传下游正文。
- TDD红灯：身份测试首次因`backend.main_api.core.identity`缺失产生1个收集错误；随后先后补入伪造owner、Session过期、本地主体、跨环境/应用/用户、同名上传转发、`sessionId`上下文、非法主体、路径穿越、输入互斥、格式限制、旧数字元数据和缓存日志脱敏测试，均在最小实现后转绿。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_legacy_identity.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api backend/personaldb backend/slide_agent`；`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run type-check`；`npm.cmd run build`；`git diff --check`；敏感日志模式扫描。
- 自动化结果：T07定向22通过、0失败；后端全量132通过、0失败，仅1条既有Starlette TestClient弃用告警；前端6个测试文件19通过、0失败；Vue类型检查、生产构建、Python编译和差异空白检查退出码0。生产构建仍有既有主chunk大于500kB提示，留T22处理。
- 真实文件与隔离：使用当前代码在独立9101端口启动本仓库PersonalDB。TXT、DOCX、PDF、PPTX均返回HTTP 200、非空Markdown（62/76/74/91字符）和Embedding结果。两个隔离测试主体使用相同`same-name.txt`和相同file ID写入不同标记后，各自检索只命中自己的标记、不含另一主体标记；9101门面已停止，既有9100进程因命令行归属无法确认而保持不动。
- 真实生成边界：当前代码在本轮创建的6801主API门面调用既有真实大纲Agent，HTTP 200且出现真实流式分片，但调用端没有取得完整终态；停止的仅是本轮6801门面，未停止大纲/正文Agent。该结果不记为大纲完成、正文完成或依据文件生成通过。G0曾分别完成非文件大纲/正文真实生成；T07的身份转发由路由集成测试证明，最终依据文件端到端生成继续由B-06/T23验收。
- 日志与安全审查：主API、A2A客户端、PersonalDB和PPT Writer不再打印模型分片、提示词、检索结果、metadata、复合主体或缓存原始键；主体只记不可逆短摘要，缓存只记摘要tag。跨用户伪造、缺Session、非法/超长`sessionId`、不支持格式、空文件、文件/URL歧义、路径穿越和下游错误均有失败测试。当前任务差异复核未发现剩余阻塞项。
- 支持矩阵与限制：TXT仅验证UTF-8小文件；DOCX和PPTX仅验证文本提取，不证明版式/母版/动画；PDF仅验证文本型文件，扫描PDF OCR未验证；其他格式由主API返回HTTP 415明确提示。转换、Embedding、检索和依据生成继续分别报告。
- 阻塞项：B-08已`closed`。B-06保持`partial_verified`，原因是转换、Embedding和复合主体检索已真实通过，但依据文件生成完整终态仍未取得；依赖链未因此阻断T08。B-01保持`partial_verified`并进入T08关闭重启恢复部分。
- 未验证边界：未用两个真实墨灵账号执行旧接口；未验证真实生产Session/MySQL上的并发旧接口流量；未完成依据文件大纲/正文终态、扫描PDF OCR、复杂Office版式或生成PPT视觉。测试Chroma中保留两个隔离主体的测试向量，未批量删除或触碰既有用户数据。本任务无新增页面，不涉及四档UI。
- 风险与回滚：保持`SSO_ENABLED=false`可回到固定本地主体开发流程；如身份适配回归，可回滚旧接口的`LegacyIdentityResolver`装配并保留PersonalDB数字集合兼容。复合主体集合与旧数字集合物理隔离，应用回滚不删除任何集合或向量。未commit、push、部署、切换流量或开启计费；`BILLING_ENABLED=false`。
- 下一任务：`T08`，当前Gate仍为G2-A；T08依赖已满足并立即开始。

### 2026-07-23 T08 验证记录

- 状态：`completed`；B-01已`closed`，M2的G2-A已通过并按固定顺序推进M3的T09；G2整体仍需T09～T14完成作品恢复、编辑保存与版本冲突证据。
- 修改文件：`backend/main_api/models/domain.py`、`backend/main_api/repositories/tasks.py`、`backend/main_api/migrations/versions/20260723_0004_task_dispatch_recovery.py`、`backend/main_api/workers/__init__.py`、`runner.py`、`main.py`、`backend/main_api/core/config.py`、`backend/main_api/tests/test_task_worker.py`、`test_core_persistence.py`、`test_db_and_migrations.py`、`test_capacity_config.py`、`env_template.txt`和本执行主文档。
- 执行契约：Worker以独立进程运行，数据库领取事务提交后才执行Agent；120秒租约、30秒心跳、最多3次、30秒指数退避、10条回收批次和600秒Agent超时均为可配置默认值。每次领取使用随机`lock_token`，心跳、成功、失败和过期回收全部受任务状态、令牌及租期围栏保护；网络调用和产物探测均不在数据库事务内。
- 崩溃与幂等边界：新增`dispatch_started_at`并在调用Agent前独立提交。派发前崩溃可安全重排；派发后崩溃先只读探测持久产物，有产物直接成功，无产物进入`AGENT_OUTCOME_UNKNOWN`明确失败而不盲目再次调用。明确超时或可重试错误使用同一`request_id`有限重试；语义仍是“至少一次领取+围栏终态”，未伪称外部Agent具备严格exactly-once。
- 状态时间线和Agent调用计数：派发前崩溃为`pending → running(attempt=1) → pending(backoff) → running(attempt=2) → succeeded`，Agent共1次；派发后无产物为`pending → running(dispatch_started) → expired → failed(AGENT_OUTCOME_UNKNOWN)`，Agent共1次；派发后已有产物为`running → expired → succeeded`，Agent共1次；一次超时后成功为`running → pending(backoff) → running → succeeded`，相同request ID共2次；连续可重试失败为3次调用后`failed/dead_letter`；不可重试失败为1次后终态；成功任务再次轮询仍保持1次调用。
- TDD红灯：首次执行`test_task_worker.py`因`backend.main_api.workers`不存在产生收集错误；随后以最小执行器转绿，并补入重复轮询、真实心跳、迁移恢复索引和Worker启动门禁测试。系统Python 3.13缺少pytest，因此所有正式结果均使用仓库`.venv312`，未修改系统环境。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_task_worker.py backend/main_api/tests/test_core_persistence.py backend/main_api/tests/test_db_and_migrations.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_capacity_config.py backend/main_api/tests/test_task_worker.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\python.exe -m backend.main_api.workers.main`；`.venv312\Scripts\alembic.exe -c alembic.ini history`；`git diff --check`；当前任务敏感日志模式扫描。
- 自动化结果：生命周期/仓储/迁移定向25通过、0失败；配置与Worker定向23通过、0失败；后端全量141通过、0失败，仅1条既有Starlette TestClient弃用告警；Python编译退出码0。迁移head为`20260723_0004`，真实隔离SQLite迁移包含`dispatch_started_at`和`ix_generation_tasks_recovery`，MySQL离线SQL亦包含同名列和索引。差异空白检查无错误，仅报告既有LF/CRLF提示；敏感日志扫描无命中。
- 独立进程与真实验证：直接运行当前代码的`python -m backend.main_api.workers.main`，默认`TASK_WORKER_ENABLED=false`时退出码0且不连接数据库、不领取任务。SQLite文件数据库上真实执行了两个连接的双Worker争抢、异步心跳续租、进程崩溃/新Worker对象重启、超时退避、重复轮询、产物探测和死信状态写入；不是Mock HTTP 200或静态代码判断。
- 错误、安全与审查：非法JSON不可重试；未知异常只记录稳定`WORKER_EXECUTION_ERROR`，错误码和安全文案限制长度，不写堆栈、上游正文、数据库URL或令牌。探测异常不会被当作“无产物”，旧Worker及竞争回收器不能越过围栏覆盖终态。审查仅覆盖T08差异，未发现剩余阻塞项。
- 未验证边界：未在现有真实MySQL执行`0004`迁移、双连接锁竞争或Worker常驻；T09业务Agent处理器尚未实现，因此`TASK_HANDLER_FACTORY`保持空、`TASK_WORKER_ENABLED=false`，未调用真实Agent。未验证进程被操作系统强杀的外部编排重启、生产监控告警、真实墨灵、多用户HTTP、对象存储、计费、UI或PPTX/PowerPoint；本任务无前端页面，不涉及四档UI。
- 风险与回滚：立即回滚可保持`TASK_WORKER_ENABLED=false`并停止独立Worker，不影响旧同步链路；应用代码可回滚但保留新增列和索引，生产环境禁止自动执行迁移downgrade或删除任务数据。`PERSISTENCE_ENABLED=false`、`BILLING_ENABLED=false`和生产流量均未开启；未commit、push、创建PR、部署或停止任何未知端口进程。
- 下一任务：`T09`，当前Gate为G2-B；T09依赖已满足并立即开始。

### 2026-07-23 T09 验证记录

- 状态：`completed`；已按固定顺序推进M3的T10，当前Gate保持G2-B，G2整体尚未通过。
- 修改文件：`backend/main_api/api/presentations.py`、`backend/main_api/schemas/__init__.py`、`schemas/presentations.py`、`backend/main_api/services/presentations.py`、`backend/main_api/repositories/resources.py`、`backend/main_api/core/db.py`、`backend/main_api/main.py`、`backend/main_api/tests/test_presentations_api.py`、`test_db_and_migrations.py`、`molin_docs/TrainPPTAgent作品API契约.md`和本执行主文档。
- 公开契约：浏览器使用`/api/presentations`，现有Vite/Nginx去掉一次`/api`后转发到后端`/presentations`。`POST`以`Idempotency-Key`原子创建作品与非计费持久任务并返回202；同owner重试复用相同记录，跨owner键冲突返回409。列表支持页码、标题搜索、状态筛选和四种受限排序；详情返回当前编辑稿；复制返回201；删除为幂等软删除204。请求体禁止额外owner/状态/任务字段。
- owner与安全：列表、详情、复制、删除和幂等复用均在SQL条件中绑定服务端Session主体和未删除状态；他人、不存在和已删除作品统一`PRESENTATION_NOT_FOUND` 404。SSO开启时所有写操作精确校验`Origin`；错误体包含稳定code、中文message、retryable和脱敏request ID。损坏`slides_json`返回稳定500且不回显原始数据，输入正文仅进入任务数据、不写日志。
- 数据与并发：作品与任务在同一事务写入，数据库`request_id`唯一约束兜底并发幂等；配置用户作品上限时，创建和复制共用容量规则并锁定owner索引范围。复制只继承当前编辑稿、页数、模板和同owner缩略图引用，不继承任务、版本号或瞬时失败/计费状态；软删除最终条件更新继续绑定owner。
- TDD红灯：首次运行`test_presentations_api.py`因`backend.main_api.api.presentations`不存在产生1个收集错误；最小实现转绿后补入跨owner幂等冲突、双用户列表、迁移门禁、实际main装配、损坏数据、容量、Origin和OpenAPI错误模型。实际main测试发现当前FastAPI没有`app.add_event_handler`，改用`app.router.add_event_handler`后转绿；旧“未迁移持久库仍能启动”测试按安全门禁改为启动失败且既有数据保留。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_presentations_api.py backend/main_api/tests/test_core_persistence.py backend/main_api/tests/test_db_and_migrations.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T09文件敏感日志模式扫描。
- 自动化结果：T09/API/仓储/迁移定向39通过、0失败；后端全量163通过、0失败，仅1条既有Starlette TestClient弃用告警；Python编译和差异空白检查退出码0，差异检查仅有既有LF/CRLF提示；敏感日志扫描无命中。OpenAPI包含公共创建/列表/详情/复制/删除路径、202/201和400/403/404/409/500响应模型。
- 真实隔离验证：测试子进程以`APP_ENV=test`和真实SQLite文件装配当前`main.py`，实际调用内部`POST /presentations`返回202并写入作品/任务，随后`GET /presentations`返回`total=1`，同时旧`/tools/aippt_outline`路由仍存在。另以两个owner写入并验证列表、详情、复制和删除互不可见；这是真实本地事务/API执行，不是Mock HTTP 200，但不是生产MySQL或真实墨灵验收。
- 审查：`code-review`技能因T01～T09同处未提交工作区、没有T08结束Git ref而无法按固定点运行；改用T09文件清单执行Standards/Spec双轴审查。发现复制未执行配置容量上限、软删除UPDATE缺owner纵深条件和OpenAPI错误声明不全，均已修复；复审0项阻塞，未发现T09范围外代码。
- 阻塞项：B-03由`open`推进为`partial_verified`，作品CRUD部分已关闭，剩余任务/保存/版本/计费/文件接口由后续责任任务补齐。B-06仍为`partial_verified`；T09无外部阻塞，G2的作品刷新、换设备、自动保存和版本恢复仍未验收。
- 未验证边界：未在当前真实MySQL执行作品写入、并发幂等或性能压测；未用两个真实墨灵账号通过公共Nginx路径操作作品；未启动T08业务Agent处理器，因此202只证明持久入队，不等于Agent、PPT或计费成功。未验证`/works` UI、编辑器恢复、对象存储、PPTX/PowerPoint；`TASK_WORKER_ENABLED=false`、`BILLING_ENABLED=false`和生产流量保持关闭。
- 风险与回滚：保持`PERSISTENCE_ENABLED=false`即可不注册作品路由并保留旧同步接口；回滚应用代码不得删除已创建作品/任务或自动降级迁移。若新API异常，暂停历史入口和新任务创建，保留表及记录供恢复。未commit、push、创建PR、部署、切换生产流量或停止未知进程。
- 下一任务：`T10`，当前Gate为G2-B；T10依赖已满足并立即开始。

### 2026-07-23 T10 验证记录

- 状态：`completed`；已按固定顺序推进T11，当前Gate保持G2-B，历史作品刷新与换设备恢复尚未验收。
- 修改文件：`frontend/src/services/presentations.ts`及其测试、`frontend/src/store/presentations.ts`及其测试、`frontend/src/store/index.ts`、`frontend/src/router/index.ts`及路由测试、`frontend/src/views/Works/index.vue`及组件测试、`output/playwright/t10_*.js`、12张T10截图和本执行主文档；`frontend/dist/`为本轮生产构建产物。
- 页面与交互：`/works`完成作品卡片、五种状态、搜索防抖、筛选抽屉、排序、分页、加载/空/错误状态、新建、复制、软删除确认和可观测反馈。生成中与待结算作品不误进编辑器，失败作品进入重新开始流程；T11前可编辑作品以旧Editor路由查询参数携带ID，本任务未伪称已完成历史编辑恢复。
- TDD红灯：首轮service/store/route/page测试因模块不存在和Works占位路由如预期失败；审查补测“当新作品不匹配当前筛选时不虚增总数”时出现预期红灯（预期0、实际2），以当前筛选可见性作为计数条件后转绿。
- 自动化命令：`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run type-check`；`npm.cmd run build`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`git diff --check`；T10文件敏感日志/遗留标记扫描。
- 自动化结果：前端9个测试文件31通过、0失败；`vue-tsc` 通过；Vite生产构建成功、4151个模块完成转换，只有既有大chunk提示；后端全量163通过、0失败，只有1条既有Starlette TestClient弃用告警。`git diff --check`无空白错误，只报告工作区既有LF/CRLF提示；未发现令牌、密钥、主体ID或上游错误正文日志。
- 四档真实浏览器验证：Chromium在1440/1024/768/390宽度下分别为4/3/2/1列，文档宽度分别为1435/1019/763/385px（差值为滚动条），无水平溢出。SSO未启用时390宽度不再预留Session控件顶部空白，SSO启用时通过`has-session-control`保留70px安全区。
- 12张状态截图：`output/playwright/t10-works-{1440,1024,768,390}.png`以及`t10-state-05-loading.png`、`06-empty.png`、`07-error.png`、`08-filter-drawer.png`、`09-create-dialog.png`、`10-delete-dialog.png`、`11-generating.png`、`12-billing-pending.png`；已逐项确认空态、错误重试、抽屉展开完成态、对话框、卡片和状态提示可见。
- 浏览器交互与控制台：在390px真实Chromium中实际点击筛选开/关、新建并提交、生成中/待结算反馈、复制、删除及确认，数量与卡片状态同步变更。最终从`about:blank`先注册拦截再进页，包括可控损坏响应错误态在内的整轮为0 error、0 warning。
- 验证边界：12张截图和按钮交互使用Playwright路由拦截的Mock作品API，只证明UI/状态机/响应式行为，不是真实墨灵、生产MySQL或公网Nginx验收。后端163项回归证明T09 API本地契约未回归，但本轮浏览器没有连真实后端；历史编辑恢复由T11验收，生产Nginx不依赖Vite由T22验收。
- 审查与阻塞：因T01～T10均处于用户未提交工作区且不允许代替用户commit，`code-review`无可靠固定起点；改用T10文件清单完成局部审查。发现并修复筛选总数虚增、移动顶部空白及生成/待结算状态误导航三项，复审0项阻塞。B-03保持`partial_verified`；T10无外部阻塞，G2-B不在本任务提前通过。
- 风险与回滚：可只撤回Works路由、页面、service/store与对应测试，返回旧首页；不删除T09后端作品/任务数据、不降级迁移。本轮自有Vite 5779和Playwright会话已停止，未停止未知进程；未commit、push、创建PR、部署、切换流量或开启计费，`BILLING_ENABLED=false`。
- 下一任务：`T11`，当前Gate为G2-B；T11依赖已满足并立即开始。

### 2026-07-23 T11 验证记录

- 状态：`completed`；M3的G2-B已通过，已按固定顺序进入M4并推进T12。G2整体仍需T12～T14的自动保存、冲突和版本恢复证据。
- 修改文件：`frontend/src/services/presentations.ts`及测试、`frontend/src/store/slides.ts`、`snapshot.ts`、`presentationEditor.ts`及测试、`frontend/src/store/index.ts`、`frontend/src/router/index.ts`及测试、`frontend/src/views/Works/index.vue`及测试、`frontend/src/views/Editor/PresentationLoader.vue`、`editorViewport.ts`、Editor与Thumbnails及测试、`backend/main_api/tests/test_presentations_api.py`、`molin_docs/TrainPPTAgent作品API契约.md`、`output/playwright/t11_*.js`、T11截图与本执行主文档。
- 恢复契约：新增`GET /api/presentations/:id`客户端，使用Cookie且不接受owner输入；规范编辑文档固定`schema_version=1`，兼容迁移期仅含`slides`的旧稿。详情解析严格校验幻灯片、元素、主题和视口；未知版本或损坏数据映射为稳定502且不回显原文。服务端补测精确10MiB UTF-8编辑稿能完整读取，超过上限的写入仍由T12处理。
- 编辑器状态与原子性：新增`/editor/:presentationId`受保护路由，迁移期`/editor?presentationId=`安全重定向；加载状态区分`loading/ready/not_found/unavailable/error`，他人、删除和不存在ID保持相同404界面。详情成功后以一次Store patch原子替换作品ID、版本、标题、主题、页面和视口，清空元素选择与本页面会话的本地撤销快照；快照库清理失败时禁用旧撤销历史但保留服务端稿件。请求世代号阻止快速切换路由时旧响应覆盖新作品。
- TDD红灯：首轮定向测试因`presentationApi.get`、`presentationEditor` Store和`PresentationEditor`路由缺失产生预期失败；实现后定向21项转绿。真实浏览器首次把390px桌面UA误判为桌面布局，先新增`editorViewport`失败测试再实现响应式判定；随后发现缩略图内部仍按UA选尺寸，修复为共享响应式断点并复验。
- 自动化命令：`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run build`（含`vue-tsc`）；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_presentations_api.py -k "detail_loads_exact_10_mib or corrupted_stored_slides" -q`；`git diff --check`；T11文件敏感日志模式扫描。
- 自动化结果：前端12个测试文件45通过、0失败；生产构建成功并转换4156个模块，仅有既有大chunk提示；后端全量164通过、0失败，仅1条既有Starlette TestClient弃用告警；10MiB/损坏稿定向2通过、21未选。差异空白检查无错误，仅有工作区既有LF/CRLF提示；未发现密钥、ticket、owner主体或上游错误正文日志。
- 双设备与四档验证：两个彼此独立、从`about:blank`注册拦截后启动的Chromium会话打开同一`presentation-restore`。桌面直接URL和刷新后均保持标题、1页内容、版本、主题及备注；独立390px会话也恢复相同稿件。1440/1024/768/390的文档宽度分别等于视口宽度、无水平溢出，前三档为desktop、390为mobile；最终两个会话均为0 error、0 warning。截图为`output/playwright/t11-desktop-direct.png`、`t11-desktop-refresh.png`和`t11-mobile-second-device.png`。
- 外部与真实边界：浏览器使用Playwright路由Mock详情，只证明真实UI、刷新、第二浏览器状态恢复和响应式行为，不是生产MySQL、真实墨灵或公网Nginx验收。后端164项回归包含真实本地SQLite/API详情、跨owner/删除/不存在同404和精确10MiB读取，与浏览器Mock证据分开报告。T12前尚未实现服务端保存、断网草稿和移动端保存，不将加载恢复写成二次编辑完成。
- 审查与安全：因T01～T11均处于用户未提交工作区且禁止代替用户commit，无法建立可靠Git固定审查点，改按T11文件清单局部复核。已修复390px UA误判、缩略图尺寸不一致、快照清理失败可能保留旧撤销历史、热切换断点时快捷键未注册及移动导出原始异常进入控制台五项；未发现剩余T11阻塞项。ID只允许受限字符和长度，非可编辑状态不会展示编辑器，错误加载不会覆盖当前稿件。
- 阻塞项：B-03保持`partial_verified`；详情读取契约已冻结，PATCH保存、版本并发、任务、计费和文件子契约仍由T12～T20分别关闭。B-06仍为`partial_verified`且不阻断T12；本任务无新增外部阻塞。
- 风险与回滚：可撤回参数化Editor路由、详情服务和加载Store并恢复T10旧查询参数入口；回滚不删除任何作品、快照外的用户数据或迁移。T11自有Vite与浏览器会话已停止，未停止未知端口进程；未commit、push、创建PR、部署、切换流量或开启计费，`BILLING_ENABLED=false`。
- 下一任务：`T12`，当前Gate为G2；T11依赖已满足并立即开始自动保存与离开保护。

### 2026-07-23 T12 验证记录

- 状态：`completed`；已按固定顺序推进T13。G2仍未通过，必须完成T13多标签冲突和T14版本恢复后才能放行。
- 修改文件：`backend/main_api/schemas/presentations.py`、`api/presentations.py`、`services/presentations.py`、`repositories/resources.py`、`main.py`、`tests/test_presentations_api.py`；`frontend/src/services/presentations.ts`及测试、`services/presentationDrafts.ts`、`editor/presentationAutosaveEngine.ts`及测试、`hooks/usePresentationAutosave.ts`、`views/Editor/PresentationAutosaveStatus.vue`及测试、Editor入口和`App.vue`；`molin_docs/TrainPPTAgent作品API契约.md`、`output/playwright/t12_autosave.js`、5张T12截图和本执行主文档。
- 保存契约：新增`PATCH /api/presentations/{id}`，owner只取服务端Session，SSO写请求校验Origin；仅`ready/draft`可保存。服务端校验schema、页面/元素骨架和视口，按UTF-8紧凑JSON执行精确10MiB上限，原子更新标题、当前稿、页数、时间并递增`current_version`。他人/删除/不存在统一404，状态不可编辑409，超限413，损坏稿422；错误不回显用户内容。T12刻意不实现旧版本条件，跨标签409留T13。
- 前端行为：编辑变更立即写按`app+user+presentation`隔离的稳定IndexedDB草稿，最后一次变更静默2秒后保存；同一实例最多一个PATCH在途，慢请求期间只保留最新排队稿。手动保存、保存/失败/离线状态、恢复本地稿、忽略、联网后确认重试均有可操作按钮。离线不自动重放；IndexedDB读取、写入或清理失败时不阻断云端保存，并明确提示本地兜底不可用。成功稿清除本地草稿。
- 移动与离开保护：390px新增作品标题和当前页备注基础编辑及手动保存；1440/1024/768保持完整桌面编辑器。仅脏稿、保存中、离线稿或失败稿触发路由确认和`beforeunload`，替换旧生产环境无条件离开提示；确认取消后仍停留原作品。
- TDD与故障证据：后端PATCH测试先得到4个预期红灯（路由不存在为405；另有测试导入缺失随即修正）后转绿。前端首次红灯命令误带仓库前缀导致“no test files found”，不计作有效红灯；随后单元测试覆盖防抖、单请求、断网、草稿恢复、失败和按钮。真实浏览器首轮暴露Vue Proxy写IndexedDB的`DataCloneError`并使保存不触发，改用浅响应式与纯JSON存储边界后补回归测试；最终新会话通过。
- 自动化命令：`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run build`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_presentations_api.py -k 'patch_' -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T12文件日志与敏感模式扫描。
- 自动化结果：前端14个测试文件59通过、0失败；`vue-tsc`和生产构建通过，4162个模块完成转换，仅有既有大chunk提示。后端全量168通过、0失败，PATCH定向4通过、23未选，只有1条既有Starlette TestClient弃用告警；Python编译和差异空白检查退出码0，差异检查仅报告既有LF/CRLF提示。
- 请求时间线：最终新鲜Chromium会话中，最后一次连续输入后2026ms才发PATCH，1900ms时请求数仍为0；2600ms慢请求期间第二次编辑没有新增在途请求，整轮`maxActiveSaves=1`且`overlap=false`，随后按“慢请求第一稿→排队最终稿”顺序完成。最终6次保存把版本从1推进到7。
- 断网、重开与草稿：断网前请求数3，离线等待2.3秒后仍为3，IndexedDB存在`trainppt_moling_drafts_v1`且仅1条标题为“断网本地草稿”的记录；联网400ms内仍为3，点击“确认重试”后才变为4。同一浏览器上下文关闭原页面并新开页面，服务端标题为“断网本地草稿”，界面提示并恢复为“关闭后恢复的本地稿”；最终保存后草稿记录数为0。
- UI与浏览器证据：1440/1024/768/390的文档宽度分别为1440/1024/768/390，前三档desktop、390为mobile，均无横向溢出且保存状态可见。取消离开确认后路径保持`/editor/presentation-save`；脏稿合成`beforeunload`事件返回`dispatched=false/defaultPrevented=true`。最终会话0 error、0 warning。截图为`output/playwright/t12-autosave-{1440,1024,768,390}.png`及`t12-mobile-draft-recovery.png`，已人工检查保存控件、基础编辑、恢复按钮和各档布局可见。
- 真实与Mock边界：浏览器路由拦截Mock详情/PATCH，只证明真实UI、IndexedDB、计时、串行队列、断网、页面重开和离开保护，不是生产MySQL、真实墨灵或公网Nginx。后端168项使用真实本地SQLite事务/API，精确10MiB、owner、Origin、状态和版本递增均真实执行；未在现有MySQL写入作品。
- 审查与安全：按T12文件清单局部复核，修复Vue Proxy不可克隆、IndexedDB失败会连带禁用云端保存、同作品旧草稿异步读取覆盖新激活、服务端畸形元素可写入及旧全局无条件离开提示五项。保存请求不含owner，草稿按身份/作品隔离；代码无新增console/print或秘密输出，未发现剩余T12阻塞项。
- 阻塞项：B-03保持`partial_verified`，串行PATCH保存子契约已冻结，T13需补`base_version`条件、409摘要和另存副本；B-04仍待T14检查点容量。T12无外部阻塞。
- 风险与回滚：保持`PERSISTENCE_ENABLED=false`可不注册PATCH路由；前端可撤回autosave hook、状态条和移动基础编辑回到T11只读恢复。回滚不删除服务端作品或本地草稿库；遗留草稿按身份/作品隔离，后续同版本才提示。T12自有5781 Vite和6个Playwright会话已停止，未停止未知进程；未commit、push、创建PR、部署、切换流量或开启计费，`BILLING_ENABLED=false`。
- 下一任务：`T13`，当前Gate为G2；T12依赖已满足并立即开始乐观锁、409和另存副本。

### 2026-07-23 T13 验证记录

- 状态：`completed`；已按固定顺序推进T14。G2仍未通过，必须完成T14检查点版本与恢复后才能放行。
- 修改文件：`backend/main_api/schemas/presentations.py`、`api/presentations.py`、`services/presentations.py`、`repositories/resources.py`、`tests/test_presentations_api.py`；`frontend/src/services/presentations.ts`及测试、`editor/presentationAutosaveEngine.ts`及测试、`hooks/usePresentationAutosave.ts`、`views/Editor/PresentationAutosaveStatus.vue`及测试；`molin_docs/TrainPPTAgent作品API契约.md`、`output/playwright/t13_conflict.js`、5张T13截图和本执行主文档。
- 后端契约：PATCH必填`base_version >= 1`，SQL在同一UPDATE中绑定作品ID、owner、未删除、可编辑状态和旧版本并原子递增；同一基线并发只能一方成功。过期写返回409 `PRESENTATION_VERSION_CONFLICT`，`latest`只包含最新标题、当前版本和UTC更新时间，不回显`slides`或owner；资源消失仍统一404，竞争变为不可编辑状态仍返回稳定409。OpenAPI明确声明409错误模型。
- 冲突副本：duplicate可选接收经过同一schema、骨架和10MiB边界校验的浏览器本地稿，在事务内创建owner隔离的新作品；副本固定版本1，不携带owner、源版本、任务或瞬时计费状态，源作品不变。普通复制未提交本地稿时仍复制服务端当前稿。
- 前端行为：保存始终发送当前已加载版本；遇到结构合法的冲突摘要后停止自动保存与自动重试，后续本地编辑继续写隔离IndexedDB草稿并触发离开保护。用户可“加载最新”或“另存副本”；加载最新先成功读取服务端稿再删除被放弃的本地草稿，网络失败时仍保留冲突和草稿；另存副本成功后清理旧作品草稿并替换路由到新作品。
- TDD证据：后端新增公开行为测试后先出现2个预期红灯（旧PATCH未要求`base_version`且duplicate不接受本地`slides`）；前端服务测试先出现3个预期红灯，保存引擎先出现2个预期红灯（冲突仍落入普通error且无加载最新能力）。最小实现后全部转绿。真实SQLite并发测试使用两个TestClient、线程屏障和同一`base_version=1`，连续5轮均稳定得到一个200和一个409；另验证冲突本地稿原子复制为版本1且源作品不变。
- 自动化命令：`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run build`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_presentations_api.py -q`及并发用例5轮复验；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T13文件日志与敏感模式扫描。
- 自动化结果：前端14个测试文件65通过、0失败；`vue-tsc`和生产构建通过，4162个模块完成转换，仅有既有大chunk提示。后端全量170通过、0失败，作品API定向29通过、0失败，并发用例5轮共10次断言结果全部通过；仅1条既有Starlette TestClient弃用告警。Python编译和差异空白检查退出码0，差异检查只有既有LF/CRLF提示。
- 双标签浏览器证据：同一Chromium上下文的两个页面从v1保存，A以`base_version=1`成功到v2，B同基线得到409；B冲突后继续编辑标题与备注并等待2.3秒，请求数保持2，没有覆盖重试。点击“另存副本”后进入`/editor/copy-1`，标题为“标签B冲突后继续编辑 副本”、备注为“标签B冲突后备注”、版本为1，请求体不含owner或`base_version`。第二组从v2出发复现冲突后，“加载最新”回到A写入的v3与原作品路径。
- UI与浏览器控制台：1440/1024/768/390的文档宽度分别等于视口宽度、无横向溢出，前三档为desktop、390为mobile；四档均可见冲突摘要、“加载最新”和“另存副本”按钮，已人工检查桌面与移动截图。控制台只有两次测试刻意触发409时Chromium产生的`Failed to load resource`网络错误记录，没有应用异常或warning；不把预期409写成0 error。截图为`output/playwright/t13-conflict-{1440,1024,768,390}.png`和`t13-conflict-mobile.png`。
- 真实与Mock边界：浏览器路由拦截Mock详情/PATCH/duplicate，只证明真实UI、请求基线、冲突停止重试、草稿进入副本和响应式行为，不是生产MySQL、真实墨灵或公网Nginx验收。后端170项使用真实本地SQLite事务/API，实际并发条件更新和owner隔离均真实执行；未在现有MySQL写入作品。
- 审查与安全：按T13文件清单局部复核，修复“加载最新”先删除草稿导致读取失败时丢失本地兜底，以及实现注释仍把乐观锁误写为未来任务两项。冲突响应白名单解析且不含稿件正文，重复409不会自动覆盖，复制正文继续受schema和容量上限约束；未发现剩余T13阻塞项。
- 阻塞项：B-03保持`partial_verified`，乐观锁、脱敏409和本地稿副本子契约已冻结；B-04仍待T14以检查点容量、保留和恢复实测关闭。T13无外部阻塞。
- 风险与回滚：可撤回`base_version`条件、冲突状态条与本地稿duplicate扩展，恢复为T12串行保存，但G2必须保持不通过且不得开放多设备编辑。回滚不删除作品、版本或本地草稿。T13自有5782 Vite和`t13proof`、`t13final`浏览器会话已停止，未停止未知进程；未commit、push、创建PR、部署、切换流量或开启计费，`BILLING_ENABLED=false`。
- 下一任务：`T14`，当前Gate为G2；T13依赖已满足并立即开始检查点版本和恢复。

### 2026-07-23 T14 验证记录

- 状态：`completed`；M4与G2已通过，并按固定顺序推进M5的T15。G2只证明本地作品数据与编辑链路，不提前宣称生产MySQL、真实墨灵、计费、对象存储或G5通过。
- 修改文件：`backend/main_api/schemas/presentations.py`、`api/presentations.py`、`services/presentations.py`、`repositories/resources.py`、`main.py`、`tests/test_presentations_api.py`；`frontend/src/services/presentations.ts`及测试、`store/presentationEditor.ts`、`hooks/usePresentationAutosave.ts`、`views/Editor/PresentationVersionPanel.vue`及测试、Editor入口；`molin_docs/TrainPPTAgent作品API契约.md`、`TrainPPTAgent持久任务租约与容量基线.md`、`output/playwright/t14_versions.js`、4张T14截图和本执行主文档。既有T06迁移已包含`presentation_versions`表与作品内版本唯一约束，本任务未重复改写已执行迁移。
- API与owner契约：新增检查点创建/列表/恢复路由。创建仅接受`base_version`和`manual|ai|export|periodic`原因，不接受owner或历史正文；同作品同版本唯一，首次201、重复200复用。列表按版本倒序且只返回原因、时间、SHA-256和解压字节数，不返回稿件。恢复仍绑定owner、未删除、可编辑状态和当前基线，成功返回完整详情；他人、删除、缺失统一404，旧基线返回脱敏409。
- 版本与容量：当前规范JSON使用确定性gzip并以`gzip+base64-v1`信封写入既有LONGTEXT；压缩后默认不超过1MiB才允许内联，T19 Storage Adapter未实现前更大检查点稳定返回503 `CHECKPOINT_STORAGE_UNAVAILABLE`。读取同时限制压缩体和最大10MiB解压输出，拒绝压缩炸弹；兼容迁移前原始JSON历史。默认最近20个，新检查点/恢复先独立事务提交，再由FastAPI响应后任务清理最旧记录；清理失败不回滚新版本且日志只含作品ID哈希。
- 恢复语义：恢复历史v1时以当前v2为条件更新，生成新的当前v3及`reason=restore`检查点，原v1/v2行保持不变；恢复后SHA-256与目标历史一致、与被替换当前稿不同。版本重复、容量、清理、损坏历史、owner隔离、Origin、状态和OpenAPI响应均有测试覆盖。
- 前端行为：历史版本面板支持打开/关闭、加载/空/错误状态、保存当前检查点、恢复确认、忙碌禁用和结果反馈；四档均有真实按钮交互。手动检查点会先完成当前稿保存，离线或未保存成功时阻止创建/恢复。恢复响应在自动保存追踪暂停期间原子替换稿件并重建撤销栈，再把新版本作为保存基线；避免把服务端恢复误判为本地修改。
- TDD与浏览器故障证据：后端4个公开行为测试先稳定得到4个404红灯；前端服务先有3个“方法不存在”红灯，版本面板先因组件不存在红灯，随后最小实现转绿。真实浏览器首轮发现恢复后完整重载会重挂载编辑器、关闭面板并丢失成功反馈；改为保存引擎上下文内切换后补组件/Store测试并重跑通过。另在审查中把同步清理改为响应后任务，并增加压缩炸弹受限解压。
- 自动化命令：`npm.cmd run test:unit -- --reporter=dot`；`npm.cmd run build`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_presentations_api.py -q`及检查点定向；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T14文件日志与敏感模式扫描。
- 自动化结果：前端15个测试文件71通过、0失败；`vue-tsc`和生产构建通过，4165个模块完成转换，仅有既有大chunk提示。后端全量175通过、0失败，作品API定向34通过、0失败，只有1条既有Starlette TestClient弃用告警；Python编译和差异空白检查退出码0，差异检查只有既有LF/CRLF提示。
- 真实SQLite证据：使用真实本地SQLite事务/API依次创建v1检查点、保存不同v2、恢复v1为新v3；列表版本链为`3 restore → 2 ai → 1 manual`，v3与v1正文哈希相同且v2不同，数据库保留3行。连续创建22个检查点后只保留v22～v3共20个；约1.1MiB不可压缩正文在对象存储未启用时不写版本行；超过10MiB解压输出的构造gzip稳定返回500而不分配无界正文。
- 真实浏览器与四档证据：新鲜Chromium在390px从v2点击保存检查点，编辑标题与备注并保存到v3，再以`base_version=3`恢复v2为v4；请求体只有基线与原因，最终当前备注为“检查点内容 v2”，列表保留`v4 restore`和`v2 manual`。1440/1024/768/390的文档宽度分别等于视口宽度、无水平溢出，前三档desktop、390为mobile，四档面板、保存与恢复操作均可见，控制台0 error、0 warning。截图为`output/playwright/t14-versions-{1440,1024,768,390}.png`。
- 真实与Mock边界：浏览器路由Mock只证明真实UI、请求序列、版本切换和响应式行为，不是生产MySQL、真实墨灵或公网Nginx验收；后端175项与容量链使用真实本地SQLite，但未在现有MySQL写入作品。gzip内联、清理和受限解压已真实执行；大检查点对象存储仍明确留给T19，不伪称已归档。
- 审查与安全：按T14文件清单局部复核，修复恢复反馈丢失、同步清理不符合提交后异步规则、gzip无界解压及旧原始JSON损坏错误码不稳定四项。检查点API不接收owner/正文，摘要不返回正文，日志不打印原始作品ID、稿件或密钥；未发现剩余T14阻塞项。
- 阻塞项：B-03保持`partial_verified`，版本历史子契约已冻结；B-04推进为`partial_verified`，T14关闭版本计量、内联阈值、最近20个和提交后清理，用户总配额、对象占额与大检查点Storage Adapter仍由T19关闭。T14无外部阻塞。
- 风险与回滚：可停止注册版本路由并隐藏版本面板，已存在`presentation_versions`数据继续保留；应用回滚不执行迁移降级或删历史。T14自有5783 Vite与所有`t14*`浏览器会话已停止，未停止未知进程；未commit、push、创建PR、部署、切换流量或开启计费，`BILLING_ENABLED=false`。
- 下一任务：`T15`，当前Gate为G3；T14依赖已满足并立即开始权益解析和计费策略，真实运营金额未确认前继续保持配置化且`BILLING_ENABLED=false`。

### 2026-07-23 T15 验证记录

- 状态：`completed`；已按固定顺序推进T16。G3仍未通过，T15只冻结权益解析与金额策略，不创建收费任务、不执行reserve/settle/release。
- 运营决策：依照本文推荐默认值关闭O-01/O-02/O-04。整套PPT预占与固定结算分别读取`PPT_GENERATION_RESERVE_POINTS`和`PPT_GENERATION_SETTLE_POINTS`，仓库不提供生产数字；固定结算必须为正整数且不超过预占。权益按active、usable、未过期、单个足额过滤，最早过期优先，永久权益最后，同到期按entitlement ID稳定排序，第一版不拆分多个权益。真实金额未确认期间`BILLING_ENABLED=false`且两个金额可留空。
- 修改文件：`backend/main_api/services/billing.py`、`integrations/moling.py`、`core/config.py`、`tools/verify_billing_readonly.py`、`tests/test_billing_policy.py`、`tests/test_moling_client.py`、`tests/test_config.py`、`env_template.txt`、`molin_docs/TrainPPTAgent计费策略契约.md`和本执行主文档。
- 策略行为：新增精确`Decimal`的预占/固定结算策略、确定性单权益选择和只读余额提示。`remaining=null`作为不限量；两个各6积分权益不能组合承担10积分。无有效权益返回`BILLING_ENTITLEMENT_UNAVAILABLE`，单个均不足返回`BILLING_ENTITLEMENT_INSUFFICIENT`。余额提示只返回是否值得尝试reserve，最终权威固定为`platform_reserve`，禁止“查余额后直接运行Agent”。
- 平台并发与安全：平台原子reserve在余额读取后返回`60005`仍映射为额度不足，不自动换另一个权益重试；平台错误消息不进入本地异常。权益列表强制查询配置商品，调用方不能覆盖product；列表每项user和余额响应的user/entitlement必须匹配请求作用域，否则作为协议错误拒绝整批响应。过期时间改为强类型datetime，畸形时间稳定归类协议错误。
- TDD证据：策略测试先因`services.billing`不存在产生1个预期收集红灯；跨用户/跨权益/跨商品客户端测试先产生3个预期红灯；固定结算大于预占的配置测试先产生1个预期红灯。最小实现后定向52通过，覆盖无权益、多个权益、过期、剩余不足、不限量、不拆分、相同到期稳定顺序、余额变化和平台并发拒绝。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_billing_policy.py backend/main_api/tests/test_moling_client.py backend/main_api/tests/test_config.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\python.exe backend/main_api/tools/verify_billing_readonly.py`；`git diff --check`；T15文件日志与敏感模式扫描。
- 自动化结果：T15三组定向52通过、0失败；后端全量185通过、0失败，只有1条既有Starlette TestClient弃用告警；Python编译和差异空白检查退出码0，差异检查只有既有LF/CRLF提示。敏感扫描只命中配置模板空键、测试假令牌/假敏感正文、客户端内部令牌字段和只读工具的受控汇总`print`，无真实值或原始响应输出。
- 真实墨灵只读验证：本机`.env`具备平台地址、内部令牌和商品配置，工具以SQLite只读URI读取T04已验证Session主体，真实调用权益列表得到`entitlement_count=3`、`usable_count=3`，并对确定性首选候选完成1次真实余额读取；输出仅含数量、布尔值和`billing_enabled=false`，不含用户ID、权益ID、额度、令牌、request ID或响应正文。这不是reserve、settle、release或扣费成功证据。
- 审查：按T15文件清单局部复核，补上平台返回跨作用域数据的拒绝、配置商品不可覆盖、结算不得大于预占、真实过期时间强类型解析和只读验证脚本脱敏五项。测试假数据使用明确假令牌；生产代码无新增业务正文日志，未发现剩余T15阻塞项。
- 阻塞项：O-01/O-02按“配置化但无生产数字”缩减范围关闭，O-04按推荐策略关闭；真实运营积分值仍是G3/G5前置，不影响T16～T18代码与Mock/契约测试。B-03保持`partial_verified`，计费客户端查询契约与策略已冻结，收费任务和计费状态API由T16～T18补齐。T15无代码阻塞。
- 风险与回滚：保持`BILLING_ENABLED=false`即可保证策略不会进入真实收费路径；可撤回`services/billing.py`及T15调用准备，不影响现有SSO、作品、任务或版本数据。只读验证没有写平台或本地Session库；未commit、push、创建PR、部署、切换流量或开启计费。
- 下一任务：`T16`，当前Gate为G3；T15依赖已满足并立即开始计费型任务与request幂等，T17前不得调用真实reserve。

### 2026-07-23 T16 验证记录

- 状态：`completed`；已按固定顺序推进T17。G3仍未通过，本任务只创建本地计费意图和Worker前置闸门，没有调用真实reserve、settle或release。
- 修改文件：`backend/main_api/models/domain.py`、`repositories/resources.py`、`services/presentations.py`、`main.py`、`migrations/versions/20260723_0005_task_owner_request_and_billing_intent.py`、`tests/test_presentations_api.py`、`tests/test_db_and_migrations.py`、`molin_docs/TrainPPTAgent作品API契约.md`、`molin_docs/TrainPPTAgent计费策略契约.md`和本执行主文档。
- 幂等与原子性：把任务唯一约束由全局`request_id`改为`(owner_user_id, request_id)`；同用户、同完整业务载荷复用原作品/任务/计费意图，不同载荷稳定409，不同用户相同客户端值各自创建。计费开启时作品、任务和`billing_operations`在同一事务创建；计费关闭时保留原非计费路径且不创建计费记录。
- 计费闸门：计费作品初始为`billing_pending`，任务为`billing_required/awaiting_reserve`，意图为`planned`；三把键分别由持久task ID派生为reserve、settle、release。T08 Worker仅领取`pending`，实测`run_once=false`且Agent调用计数为0。T16不选择权益、不写平台，T17预占成功前不得把任务推进为可领取。
- TDD红灯：首轮4个边界测试中跨用户隔离和不同载荷冲突转绿，计费重试与并发各因临时task ID和既有稳定键不同得到409红灯；改为核对既有task ID派生键后4项转绿。局部审查再发现reserve后刷新会因状态不再是`planned`误报409，新增状态推进重试测试稳定红灯，随后只核对不可变业务配置与稳定键后转绿。
- 并发与迁移证据：同一用户两个并发POST连续复验5轮，每轮均1通过且最终只有1个作品、1个任务、1条计费意图，响应为一个新建、一个复用。真实SQLite先升级到0004并插入既有任务，再执行0005：原行保留，另一用户可插入同客户端键，同用户重复仍由数据库拒绝；应用在0005缺失时启动前稳定报迁移未完成。
- 自动化命令：T16定向`pytest`；并发用例连续5轮；`test_presentations_api.py + test_db_and_migrations.py + test_task_worker.py`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T16文件日志敏感模式扫描。
- 自动化结果：T16核心定向5通过、0失败，迁移定向2通过、0失败，三组相关回归54通过、0失败；后端全量190通过、0失败，只有1条既有Starlette TestClient弃用告警。Python编译和差异空白检查退出码0，差异检查只有既有LF/CRLF提示；敏感扫描仅命中既有测试子进程的受控`print`，没有令牌、正文或计费明细日志。
- 真实与Mock边界：数据库约束、事务、迁移、并发和Worker领取使用真实本地SQLite与真实Worker代码，不是静态判断；计费参数是测试配置73/20/15，仅为明确假数据，不是运营值。当前本地配置读取确认`billing_enabled=false`；未写真实墨灵、MySQL、对象存储或生产数据，也未把HTTP 202写成Agent或扣费成功。
- 审查与安全：按T16文件清单局部复核，修复临时ID错误比较、状态推进后重试误冲突和旧0004数据库可带流量三项。业务载荷只存任务表，不新增日志；owner来自服务端Session，客户端不能注入商品、金额、计费状态或owner。T16没有前端页面，不涉及四档UI或按钮验收。
- 阻塞项：B-03保持`partial_verified`，收费任务创建与request幂等子契约已冻结；reserve/settle/release状态和对账API由T17、T18继续补齐。T16无外部阻塞，真实运营金额仍是G3/G5前置但不阻止本地Mock与契约开发。
- 风险与回滚：保持`BILLING_ENABLED=false`可完全绕过收费任务路径。应用回滚必须保留0005复合唯一约束和既有数据；不同用户一旦复用客户端键，不得直接降级为全局唯一约束。未commit、push、创建PR、部署、生产迁移、切换流量或开启计费。
- 下一任务：`T17`，当前Gate为G3；T15/T16依赖已满足并立即开始三动作编排，仍以Mock/契约测试为主且生产`BILLING_ENABLED=false`。

### 2026-07-23 T17 验证记录

- 状态：`completed`；已按固定顺序推进T18。G3仍未通过，T17完成Mock/契约和真实本地数据库状态机，不代表真实墨灵扣费已验收。
- 修改文件：`backend/main_api/integrations/moling.py`、`repositories/billing.py`、`repositories/tasks.py`、`services/generation_orchestrator.py`、`workers/main.py`、`core/config.py`、`tests/test_moling_client.py`、`tests/test_billing_orchestrator.py`、`tests/test_config.py`、`molin_docs/TrainPPTAgent计费策略契约.md`和本执行主文档。
- 平台契约：Moling Client新增reserve/settle/release，金额只发送decimal字符串，三动作使用不同稳定键；严格验证响应状态、金额和响应hold归属。hold ID兼容平台正整数或受限字符串并统一存字符串；平台正文、令牌、额度和hold不进入日志。`quota_reserved`按权益聚合值解释，允许其他并发hold导致非零，不把它误判为当前hold失败。
- 状态与顺序：常驻Worker先从持久`planned`意图预占，SQLite/MySQL通用条件更新只允许一个执行者调用平台；reserve成功并保存hold后才把任务推进`pending`。Agent返回后再次只读确认产物，存在才settle，明确失败/无产物才release；普通异常、取消和超时也先探测，探测异常冻结为`inspect/billing_pending`。
- 失败与未知终态：平台原子`60005`在Agent前失败且不换权益；reserve/settle/release超时、协议错或响应归属错均不猜测成功。平台写成功但本地终态条件提交失败时分别写`*_LOCAL_COMMIT_FAILED`并冻结，reserve同时保留hold；原`reserving|settling|releasing`和动作键可供T18恢复。settle未知时不release，release未知时不宣称退款。
- 幂等与停机安全：重复settle/release命中本地终态不再次调用平台；两个线程以Barrier并发预占连续5轮，每轮平台reserve调用均为1。`BILLING_ENABLED=false`只停止新收费任务和新reserve；运行配置完整时继续收尾遗留hold，配置不足时TaskLease候选查询与条件更新双重排除计费任务，禁止裸跑Agent。
- TDD红灯：客户端写接口缺失首先产生2个收集错误；实现后补响应状态/释放金额红灯。审查阶段又确认并修复权益聚合预占误判、平台成功本地提交失败、关闭计费后遗留任务裸跑、异常/超时未经探测释放及响应hold错配；每项均先补失败测试再转绿。
- 自动化命令：T17客户端与编排定向；计费策略、任务Worker、核心持久化和配置相关回归；并发预占连续5轮；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T17文件敏感日志模式扫描。
- 自动化结果：T17客户端31通过，编排12通过，六组相关回归84通过、0失败；后端全量208通过、0失败，只有1条既有Starlette TestClient弃用告警。Python编译与差异空白检查退出码0，差异检查只有既有LF/CRLF提示；敏感扫描0项生产日志命中。
- 真实SQLite与调用计数：成功链严格为一次reserve→一次Agent→产物持久化→一次settle，重复轮询不再调用；明确Agent/持久化失败为一次reserve→一次release且Agent不重跑；额度不足Agent调用0。reserve/settle/release平台成功但本地终态提交失败三种情形均实际落为`billing_pending`，reserve情形保留同一hold。
- Mock与真实边界：平台写请求全部使用MockTransport/Fake客户端，没有调用真实墨灵reserve、settle、release或改变真实积分；数据库事务、并发条件更新、Worker领取/取消/超时和状态恢复使用真实本地SQLite与真实Worker代码。当前本地读取再次确认`billing_enabled=false`、`task_worker_enabled=false`，未开启生产计费或常驻收费Worker。
- 双轴审查：因T01～T17均为未提交工作区、没有可靠Git fixed point，`code-review`技能按T17文件清单执行Standards与Spec双轴只读审查。初审发现中文并发注释、裸状态字符串、仓储穿透、并发测试同步、聚合额度语义、本地提交失败、关闭开关收尾、异常探测和hold归属问题，均修复；两轴最终复审均为0项阻塞。
- 运营与阻塞：O-03按推荐默认推进为`defaulted`，单页费用保留独立`SLIDE_REGENERATION_POINTS`，真实值未确认前不开放该收费入口。B-03保持`partial_verified`，三动作和状态机契约已冻结；T18补对账查询、退避和人工状态。T17无外部代码阻塞。
- 风险与回滚：关闭`BILLING_ENABLED`后不得删除平台配置，Worker可继续settle/release已有hold；若配置也必须撤除，TaskLease会跳过所有计费任务，需由T18/人工对账后再恢复。禁止直接清理`billing_operations`、重复reserve或把`billing_pending`改成成功/退款。未commit、push、创建PR、部署、真实平台写、生产迁移或流量切换。
- 下一任务：`T18`，当前Gate为G3；实现未知终态对账、指数退避、最大重试和owner隔离查询，仍不得开启真实生产计费。

### 2026-07-23 T18 验证记录

- 状态：`completed`；M5本地代码与契约Gate G3已通过，并按固定顺序推进M6的T19。G3不包含真实墨灵积分写入，真实流水一致性仍由T23/G5验收。
- 修改文件：新增`repositories/reconciliation.py`、`workers/reconciliation.py`、`api/tasks.py`、`services/tasks.py`、`schemas/tasks.py`和`tests/test_billing_reconciliation.py`；修改`repositories/billing.py`、`workers/main.py`、`main.py`、`core/config.py`、`env_template.txt`、`molin_docs/TrainPPTAgent计费策略契约.md`及本执行主文档。
- 对账状态机：`billing_pending`到期后以数据库条件更新认领为`reconciling`；settle/release只重放T16持久化的原幂等键，成功后在同一事务提交账务、任务和作品终态。未知reserve因平台没有hold状态查询接口，禁止自动重放并直接转`manual_required`；`inspect`先只读探测产物，再选择settle或release。
- 重启、退避与人工边界：`retry_count`、`next_retry_at`和动作均持久化，按配置周期指数退避并封顶1小时；`BILLING_RECONCILE_MAX_RETRIES`默认8、范围1～100。达到上限后停止平台请求；最后一次认领后进程崩溃时，等待退避与在途租约均到期后原子转人工，避免永久悬挂。
- 并发与租约：退避周期与平台调用租约分离。生产租约覆盖Moling Client的pool/connect/write/read四段配置超时并增加5秒余量；`reserving/settling/releasing/reconciling`未超过租约时不得被另一进程重放，认领继续以原status、retry_count和updated_at条件更新决定唯一赢家。异步慢调用测试中第二Worker跨退避点仍未重放，平台最大并发写调用为1。
- 任务查询与脱敏：新增`GET /api/tasks/{task_id}`，owner只来自服务端Session；不存在、已删除归属或跨用户统一404。公开计费摘要只返回status、action、retry_count、next_retry_at和manual_required，不返回hold、三把幂等键、权益ID、预占额或结算额。
- TDD红灯：首次定向测试因`backend.main_api.api.tasks`不存在产生1个预期收集错误；最小实现后转绿。局部审查继续以失败测试捕获并修复在途平台调用被提前重放、最后一次认领崩溃永久悬挂、平台超时预算大于退避窗口和默认60秒退避/41秒租约错误耦合四类问题。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_billing_reconciliation.py backend/main_api/tests/test_config.py -k "reconcil or default_backoff" -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q --disable-warnings`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`git diff --check`；T18公开响应与日志敏感字段扫描；本地开关只读检查。
- 自动化结果：T18定向12通过、0失败；后端全量220通过、0失败，只有1条既有Starlette TestClient弃用告警；Python编译和`git diff --check`退出码0，差异检查仅有既有LF/CRLF提示；新增未跟踪文件尾随空白扫描0命中。当前本地`BILLING_ENABLED=false`、`TASK_WORKER_ENABLED=false`。
- 真实SQLite与Fake平台证据：实际数据库事务验证settle已在平台生效但响应丢失时同键重放后恢复ready，release同键重放后保持失败且不虚假承诺退款；服务重启读取持久退避，三次失败转人工；并发认领只有一个赢家；慢平台写期间第二Worker调用数为0。Fake账本最终记录与本地动作一致，但它不是墨灵真实平台流水。
- 双轴审查：`code-review`技能因T01～T18均为未提交工作区而无法使用Git fixed point，改按T18文件清单执行Standards与Spec双轴。初审/复审发现的在途竞态、崩溃收敛、租约预算和默认构造问题均先补测试再修复，最终两轴均为0项剩余阻塞。
- 阻塞与运营：B-03继续为`partial_verified`，对账与任务查询子契约已冻结，文件API待T19/T20。O-09按可逆非生产默认推进为100件作品/1GiB存储并保持配置项，生产值必须在T23前确认；这允许T19完成配额代码和真实存储最小验证，不代表生产容量决策已验收。
- 未验证边界：未调用真实墨灵reserve/settle/release，无法给出真实hold或积分流水；未在生产MySQL运行对账竞争；没有对象存储写入、前端页面、四档UI、PPTX生成或PowerPoint打开。本任务无前端按钮。
- 风险与回滚：保持`BILLING_ENABLED=false`阻止新收费任务；已有hold需要保留平台运行配置，由对账Worker以原键收尾。若撤除查询路由或对账进程，必须保留`billing_operations`数据和人工清单，禁止删除记录、重复reserve或把`billing_pending`手工改成成功/退款。未commit、push、创建PR、部署、生产迁移、切换流量或开启计费。
- 下一任务：`T19`，当前Gate为G4；先落实O-09非生产配额默认和Storage Adapter公开行为测试，再执行真实对象存储最小写读删，不打印凭据。

### 2026-07-23 T19 验证记录

- 状态：`completed`；B-04代码阻塞已关闭，按固定顺序推进T20。G4仍未通过，T19不包含历史PPTX下载与PowerPoint实际打开。
- 运营决策：O-09按可逆非生产默认推进为`USER_PRESENTATION_LIMIT=100`、`USER_STORAGE_QUOTA_BYTES=1073741824`，仓库模板给出数值但`STORAGE_ENABLED=false`。存储开启时两个值均必填；生产容量仍必须在T23前由运营确认，不把1GiB写成生产承诺。
- 修改文件：新增`integrations/storage.py`、`repositories/files.py`、`services/files.py`、`migrations/versions/20260723_0006_owner_storage_usage.py`、`tests/test_file_storage.py`和`tools/verify_storage_roundtrip.py`；修改`models/domain.py`、`models/__init__.py`、`services/presentations.py`、`main.py`、`core/config.py`、`requirements.txt`、`env_template.txt`、相关配置/迁移/作品测试、容量基线文档和本执行主文档。
- Storage Adapter：声明`boto3`直接依赖，S3兼容适配器统一path-style、SigV4、连接/读取超时和有限重试。服务端生成受限对象键，客户端文件名和路径不参与；写入后用head核对大小和metadata SHA-256，读取先核对Content-Length、最多读取声明大小+1并复验SHA-256，删除和存在性查询使用稳定脱敏错误。
- 文件安全：支持PDF、UTF-8文本/Markdown/JSON、PNG/JPEG/WebP、gzip和OpenXML；PPTX/DOCX不仅检查ZIP头，还要求`[Content_Types].xml`及对应`ppt/presentation.xml`/`word/document.xml`。purpose分别应用上传50MiB、PPTX 100MiB和缩略图2MiB上限；owner、作品和未删除条件均在数据库查询中绑定。
- 配额与幂等：新增`owner_storage_usage`，0006把既有`uploading/active`文件回填。占额使用单条条件UPDATE原子判断，SQLite/MySQL均不依赖`FOR UPDATE`行为；并发复验5轮均只有一个上传通过。同作品/用途/MIME/大小/SHA相同内容复用对象且不重复占额或put；复用条件touch租约，GC已抢占时返回可重试，禁止从SQLAlchemy identity map返回旧active。
- 崩溃与删除状态机：文件先`uploading`占额，完整性验证后才`active`。陈旧上传条件认领为`recovering_upload`，与原上传者activate互斥；未引用陈旧检查点由`active→deleting`认领。delete响应未知保留状态和占额；`deleting`在重启后检查引用，有引用恢复active，无引用按同键幂等重删并释放，覆盖物理删除成功但本地提交前崩溃。
- 大检查点：超过1MiB内联阈值时以`storage-gzip-v1`文件引用保存，读回仍受10MiB解压边界保护。版本裁剪后引用感知GC只删除没有任何`presentation_versions`信封引用且超过租约的对象；测试3个对象裁剪为2个版本和2个对象，引用对象保持可读。
- TDD红灯：首次测试因`integrations.storage`不存在产生1个预期收集错误；最小实现后3项转绿。并发复跑暴露SQLite忽略行锁时双配额通过，改为条件UPDATE。双轴审查再以失败测试修复删除失败释放占额、恢复未接线、未引用对象泄漏、验证脚本遗留、超时无界、upload/GC竞态、deleting崩溃和ORM旧快照八类问题。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_file_storage.py -q`；并发用例连续5轮；迁移/配置/作品相关回归；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q --disable-warnings`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\alembic.exe -c alembic.ini history`；`git diff --check`；日志/print扫描；真实存储验证脚本。
- 自动化结果：T19定向15通过、0失败；最终后端全量236通过、0失败，仅1条既有Starlette TestClient弃用告警；Python编译与差异空白检查退出码0，迁移头为`20260723_0006`，差异检查只有既有LF/CRLF提示。生产模块无新增logger/print；验证工具只输出三个布尔状态。
- 真实对象存储证据：使用当前本地配置在隔离前缀生成随机服务端键，真实执行put→head→get→SHA-256比对→delete→head不存在，最终`storage_roundtrip=passed`、`hash_match=true`、`deleted=true`。首次尝试因配置前缀尾部`/`被本地安全校验拒绝，未发网络写；规范化前缀后成功。脚本finally在任何读/校验失败时仍尽力同键删除，不输出endpoint、bucket、对象键或凭据。
- 双轴审查：`code-review`技能按T19文件清单执行Standards与Spec。审查发现的对象/索引原子性、租约、GC、超时、验证清理和identity map问题均补测试修复；最终两轴均为0项剩余阻塞。
- 阻塞项：B-04关闭；B-03继续`partial_verified`，存储内部契约已冻结但用户下载API由T20补齐；B-07仍`open`，PPTX归档、缩略图与历史下载由T20关闭。O-09生产值仍是T23/G5运营前置，不阻止本地代码链。
- 未验证边界：真实存储只验证隔离小文本对象写读删，不是PPTX归档、缩略图或生产容量/并发验收；未写真实MySQL，未执行生产迁移，未生成/打开PowerPoint，未做文件下载API或前端四档。本任务没有前端页面和按钮。
- 风险与回滚：保持`STORAGE_ENABLED=false`可绕过对象化路径；回滚应用时保留0006及对象/文件索引，禁止直接降级删汇总表。故障时停止新上传，保留`uploading/recovering_upload/deleting`记录与占额，由同键恢复清理，禁止先删数据库索引。未commit、push、创建PR、部署、切换流量或修改生产资源。
- 下一任务：`T20`，当前Gate为G4；实现PPTX/缩略图归档和owner下载，验证同Blob哈希、软删除/越权/过期失效及历史PPTX再次下载并实际打开。

### 2026-07-23 T20 验证记录

- 状态：`completed`；B-03、B-07已关闭，M6与G4通过，并按固定顺序进入M7的T21。G4只证明文件归档链，不代表正式域名、真实积分或最终多用户UAT。
- 修改文件：新增`api/exports.py`、`schemas/exports.py`、`services/exports.py`、`repositories/exports.py`、`migrations/versions/20260723_0007_export_idempotency.py`、`tests/test_exports_api.py`、`tools/verify_export_roundtrip.py`、前端`services/exports.ts`及其测试、`hooks/__tests__/useExportArchiveState.spec.ts`和`frontend/tools/create_t20_pptx.mjs`；修改`models/domain.py`、`repositories/files.py`、`services/files.py`、`core/config.py`、`main.py`、配置/迁移相关测试、`useExport.ts`、`ExportPPTX.vue`、移动编辑器、`env_template.txt`、作品API契约及本执行主文档。
- 同Blob与重试：PptxGenJS只调用一次`write({outputType:'blob'})`；`saveAs`和归档函数持有同一个Blob对象，浏览器与服务端分别计算SHA-256。本地保存先执行，归档失败不撤销下载；原Blob和幂等键提升到页面模块生命周期，关闭/重开弹窗或移动端仍显示可操作重试入口，重试不再次本地保存或生成PPTX。
- 归档与下载契约：`POST /presentations/{id}/exports/pptx`接收OpenXML原始字节、版本、SHA和owner作用域幂等键；0007增加`(owner_user_id, request_id)`唯一约束。历史列表返回5分钟短期下载地址，HMAC绑定owner/file/expiry且下载仍要求Session；响应`no-store`、安全双文件名和SHA头。跨用户、软删除、无效签名统一不可读，真实过期严格返回410 `DOWNLOAD_URL_EXPIRED`。
- 容量、并发与回滚：服务端复验ZIP/OpenXML签名、大小和SHA。版本变化、软删除、同键并发输家、缩略图提交异常均通过引用感知`active→deleting`补偿；对象删除成功后才释放占额，删除响应未知保留状态和配额供启动恢复。缩略图换代只回收已无作品引用的旧对象；归档、缩略图和检查点恢复共享用途级引用检查，source/attachment不会被通用回收器误删。
- OpenAPI与错误：PPTX/PNG二进制`requestBody`、响应Pydantic模型及400/403/404/409/410/413/415/503稳定错误已进入OpenAPI并由测试冻结；客户端owner、对象键、文件ID归属、服务端版本和下载签名均不能由浏览器绕过。
- TDD红灯：前端首先因`services/exports`不存在产生预期收集失败，后端因`api.exports`不存在产生预期收集失败；纵向切片转绿后，审查继续以失败测试捕获版本冲突占额泄漏、缩略图换代泄漏、并发幂等输家泄漏、缩略图软删除竞态、伪过期测试、弹窗重开丢重试状态和OpenAPI二进制请求缺失，逐项最小修复。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_exports_api.py -q`；文件/迁移/配置相关回归；`.venv312\Scripts\python.exe -m pytest backend/main_api -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api`；`.venv312\Scripts\alembic.exe heads`；前端`npm.cmd run test:unit`、`npm.cmd run type-check`、`npm.cmd run build-only`；`git diff --check`及T20文件秘密模式扫描。
- 自动化结果：T20导出定向9通过、0失败；最终后端全量245通过、0失败，仅1条既有Starlette TestClient弃用告警。一次并行全量中的既有启动子进程测试以Windows `0xC0000005`无stderr退出，单测复跑和最终全量串行均通过，判定为并行资源瞬时故障而非业务回归。前端17个文件74测试全通过，类型检查与生产构建退出码0；迁移头`20260723_0007`，Python编译和差异检查退出码0，差异检查仅有既有LF/CRLF提示。秘密扫描只命中`env_template.txt`既有`ALI_API_KEY=sk-xxx`占位符，没有真实密钥。
- 真实对象存储与文件证据：PptxGenJS生成45,964字节真实PPTX；通过当前本地对象存储配置执行归档、索引、签名历史下载和finally删除，回读仍为45,964字节，源文件与下载文件SHA-256均为`8ACAD5954C7060C083FEEC1E30B46097E8A408E8A575975AA4F3B5EAEF819300`，`hash_match=true`，隔离对象已删除。验证工具不输出endpoint、bucket、对象键或凭据。
- PowerPoint与UI：本机Microsoft PowerPoint COM以只读方式实际打开对象存储回读文件，页数1，正常关闭且不保存。Playwright在1440、1024、768、390宽度复验，页面`scrollWidth`分别等于视口宽度；桌面导出弹窗按钮可操作，390移动端“下载”真实生成`未命名演示文稿.pptx`，控制台累计0 error、0 warning。最终截图位于`output/playwright/t20/`。
- 双轴审查：按`implement`要求使用`code-review`技能。两轮审查发现并修复对象/配额泄漏、缩略图竞态、并发同键完整三元组、重试状态、严格过期和OpenAPI请求契约问题；Standards与Spec最终复审均为0项阻塞。
- 未验证边界：未在生产MySQL应用0007，未切换生产流量；真实缩略图对象写入只由适配器/本地契约覆盖，本次真实云往返对象是PPTX。没有调用真实墨灵reserve/settle/release；`BILLING_ENABLED=false`、`TASK_WORKER_ENABLED=false`、模板`STORAGE_ENABLED=false`继续保持。生产容量O-09仍须T23确认。
- 风险与回滚：故障时保持`STORAGE_ENABLED=false`或暂停新归档；保留0007、exports/files/usage记录和对象，不批量删除。`deleting`记录必须由同键恢复器完成，禁止先删索引或手工减配额。前端可回退到本地下载，但已归档历史必须继续提供只读下载或明确维护状态。未commit、push、创建PR、部署、生产迁移、生产计费或流量切换。
- 下一任务：`T21`，当前Gate为G4.5；读取错误、审计、限流、健康检查任务卡与B-05，先冻结公开错误/审计/健康行为测试，再实施，不跨入T22。

### 2026-07-23 T21 验证记录

- 状态：`completed`；B-05关闭，M7与G4.5通过，并按固定顺序进入M8的T22。G4.5证明本地错误、安全和运维契约，不代表生产监控平台、正式域名或真实墨灵依赖已验收。
- 修改文件：新增`core/observability.py`、`core/health.py`、`api/health.py`、`tests/test_operational_safety.py`和《TrainPPTAgent运维观测与故障恢复手册》；修改`main.py`、`api/auth.py`、`api/exports.py`、`api/presentations.py`、`core/config.py`、`integrations/storage.py`、`personaldb/main.py`、配置/认证/旧身份/存储测试、`env_template.txt`及本执行主文档。
- 错误与关联：所有主API响应统一生成或安全复用`X-Request-Id`；未处理异常、FastAPI HTTP错误和422校验错误返回稳定错误码、中文安全文案、`retryable`与同一请求ID，不回显异常正文、下游URL、输入值或框架`detail`。既有作品、导出和认证错误也复用全局关联ID。
- 限流与审计：关键作品写入、PPT生成、PPTX归档、缩略图和退出按服务端Session owner共用滑动窗口配额，资源ID和接口切换不能绕过；生产禁止关闭`RATE_LIMIT_ENABLED`。进程内限流由T22网关再加外层保护。写审计只记录`event/request_id/user_id/method/path/status/outcome`，不读取或记录query、Cookie、Authorization、请求体、票据、提示词、URL或密钥。
- 健康与恢复：`/healthz`只证明进程存活；`/readyz`对数据库常量查询、对象存储只读bucket、大纲/内容Agent卡片、PersonalDB存活以及SSO启用时的墨灵健康接口返回逐项`up/down`，任何异常正文都被吞掉。运维手册冻结错误矩阵、结构化审计样例、首版告警阈值、租约/计费/存储恢复顺序和可逆回滚边界。
- TDD与故障注入：初始测试因`api.health`不存在按预期红灯；转绿后覆盖安全/非法请求ID、未处理异常、HTTP 502和422秘密不回显、同owner 429、跨owner独立、跨资源ID不可绕过、审计元数据，以及数据库/存储/墨灵/大纲Agent/内容Agent/PersonalDB逐项异常均映射503且不泄露凭证。S3 `head_bucket`超时也映射稳定存储错误。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_operational_safety.py backend/main_api/tests/test_session_auth.py backend/main_api/tests/test_current_user_auth.py backend/main_api/tests/test_file_storage.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；`.venv312\Scripts\python.exe -m compileall -q backend/main_api backend/personaldb backend/slide_agent`；前端`npm.cmd run test:unit -- --reporter=dot`、`npm.cmd run type-check`、`npm.cmd run build`；`git diff --check`与日志秘密模式扫描。
- 自动化结果：T21最终定向58通过、0失败；最终后端全量257通过、0失败。前端17个文件74测试通过，类型检查和生产构建退出码0。Python编译和差异空白检查退出码0；仅有既有Starlette TestClient弃用告警、Vite大chunk提示及LF/CRLF提示。日志扫描清理了PersonalDB旧URL、临时路径、异常正文、堆栈和`print`输出，剩余T21生产路径无秘密正文日志。
- 本地真实探针：用真实主应用TestClient调用，`/healthz`为200且带请求ID；`/readyz`为503，真实本地状态为`outline=up`、`content=up`、`personaldb=down`。这证明PersonalDB当前不可用会正确摘除就绪，不把端口或Mock写成通过；当前功能开关关闭，因此本轮未实际探测数据库、对象存储和墨灵。
- 审查与安全：按T21文件清单局部复核，修复同步Session解析阻塞事件循环、按资源ID限流可绕过、框架detail泄露、响应头/体请求ID不一致、PersonalDB记录URL/临时路径/异常正文以及审计logger被其他测试静默关闭等问题；最终无剩余任务内阻塞项。
- 未验证边界：未接入生产日志聚合/告警平台，未执行真实数据库、对象存储或墨灵故障演练，未验证多实例分布式限流；这些部署与真实UAT边界分别由T22、T23负责。本任务未修改UI，四档视觉不重复冒充验收；只运行既有74项前端回归。
- 风险与回滚：开发/测试可通过配置调整阈值，生产不能关闭限流；依赖异常应保持实例不就绪，禁止把必需依赖改为可选伪造通过。代码回滚不涉及迁移；回退中间件/健康路由后重启即可，计费继续保持`BILLING_ENABLED=false`。未commit、push、创建PR、部署、生产计费、生产迁移或流量切换。
- 下一任务：`T22`，当前Gate为G5；核对正式构建、Nginx、Secure Cookie、可信代理头、history回退和无HMR契约，先写部署配置测试再实施，不跨入T23真实UAT。

### 2026-07-23 T22 验证记录

- 状态：`completed`；正式静态构建与Nginx部署契约通过，按固定顺序进入T23。G5仍未通过，真实HTTPS域名、真实墨灵、积分和双用户UAT不能由本任务替代。
- 修改文件：新增`docker-compose.production.yml`、根目录与前端`.dockerignore`、`frontend/nginx-security-headers.conf`、`frontend/tools/serve-dist.mjs`和`tests/test_production_deployment.py`；修改前后端Dockerfile、`frontend/nginx.conf`、`vite.config.ts`、`package.json`、认证部署断言、`README_PRODUCTION.md`及本执行主文档。
- 正式拓扑：前端Docker多阶段执行`npm ci`和正式build，最终镜像只含`dist`与Nginx；主API从仓库根上下文构建并保留`backend.main_api`包布局。生产compose不挂载源码，main/Agent/PersonalDB/可选Worker只在容器网络expose，唯一宿主端口为回环地址的静态Nginx；本地及任意子目录`.env`均排除出构建上下文。
- Nginx与安全：`/enter`精确代理且关闭访问日志，`/api/`只去除一次前缀；正式上游为`main_api:6800`，不再使用`host.docker.internal`。入口/API有外层限流；固定Docker子网/网关限定可信`X-Forwarded-For`来源，协议和端口只接受规范值。HTML为`no-store`，hash资源为一年`immutable`，缺失asset严格404；增加nosniff、referrer、frame和permissions安全头。
- 深链修复：TDD在首次正式build发现`base:''`生成相对资源，`/editor/:id`会错误请求`/editor/assets`；改为根域`base:'/'`并冻结测试，最终`dist/index.html`只引用`/assets/<hash>`，`/works`和编辑器history深链直接访问、刷新均成功。
- 自动化命令：`.venv312\Scripts\python.exe -m pytest backend/main_api/tests/test_production_deployment.py -q`；`.venv312\Scripts\python.exe -m pytest backend/main_api/tests -q`；前端`npm.cmd run test:unit -- --reporter=dot`、`npm.cmd run type-check`，以`VITE_SSO_ENABLED=true`和公开门户URL执行`npm.cmd run build`；HMR/开发端口扫描；PyYAML compose解析；Python编译与`git diff --check`。
- 自动化结果：T22部署定向6通过、0失败；最终后端全量263通过、0失败，仅1条既有Starlette TestClient弃用告警。前端17个文件74测试通过，类型检查与正式构建退出码0；build转换4166模块，仅有既有大chunk提示。`/@vite/client`、`__vite_ping`、`vite-hmr`、WebSocket和开发端口扫描0命中；compose解析为6个服务且敏感`.env`不进入前端或镜像上下文。
- 真实Nginx验证：本机没有Docker/Nginx，故从[NGINX官方下载页](https://nginx.org/en/download.html)取得官方Windows 1.31.3临时包到`output/t22/nginx-verify/`，只用于本地测试。最终渲染配置`nginx -t`语法成功；临时监听`127.0.0.1:4180`时`/works`和`/editor/production-demo`均200且返回同一index，HTML `no-store`、JS `immutable`、`nosniff`均实际生效，随后确认监听停止。Windows包仅作配置/本地验证，不作为Linux生产运行时。
- 浏览器与四档：Chrome headless对独立`dist`服务器执行1440、1024、768、390四档直达，页面`scrollWidth`分别等于视口宽度；编辑器深链直达和刷新路径均保持`/editor/production-demo`，资源只从`/assets`加载。累计0 console error/warning、0 page error、0失败请求、0 WebSocket、0错误asset路径；截图位于`output/playwright/t22/`。API使用明确浏览器路由Mock，只证明正式静态页面和路由，不冒充真实后端UAT。
- 审查与修复：按T22文件清单复核，修复相对asset深链、主API镜像包路径、后端公网端口/源码挂载、构建上下文泄露子目录`.env`、不可信代理头、共享代理IP导致外层限流失真、缓存头继承、缺失asset回退HTML、验证服务器畸形编码崩溃及旧测试写死host网关等问题；最终无任务内阻塞项。
- 未验证边界：本机没有Docker CLI，未实际构建或启动compose镜像；compose完成仓库契约与YAML解析，Nginx由官方Windows二进制独立实测。未修改公网TLS终止层、DNS或生产代理，未验证正式域名Cookie/CORS；未执行生产迁移、部署或流量切换。`BILLING_ENABLED=false`继续强制覆盖，Worker profile未启动。
- 风险与回滚：TLS代理只应访问回环5778并覆盖可信转发头；若固定Docker子网冲突，subnet和gateway必须成对修改。回滚切换上一版镜像，保留向前兼容迁移、数据库和对象；禁止降级删表或清理用户文件。未commit、push、创建PR、部署、生产迁移、生产计费或流量切换。
- 下一任务：`T23`，当前Gate仍为G5；先核对运营值、真实环境与两名测试用户准备度，再执行授权范围内的只读预检和UAT证据盘点。缺少生产部署/真实计费授权时必须明确记录并停止伪造验收。

### 2026-07-23 T23 验证记录

- 状态：`blocked`；T23未完成、G5未通过、Goal继续保持`in_progress`。阻塞来自生产部署/迁移/切流和真实计费的明确权限边界、两名真实测试用户未准备及运营值未确认，不能用本地或Mock证据替代。
- 修改文件：新增`molin_docs/TrainPPTAgent真实UAT与发布验收报告.md`和不记录正文/凭据的`output/t23/verify_evidence_generation.py`；更新本执行主文档的项目状态、T23、B-06和证据记录。T23没有以业务代码修改代替真实验收。
- 正式域名只读核对：`https://ppt.axicomin.cn/`与`/works`均返回HTTP 200但响应含Vite开发客户端，缓存为`no-cache`；`/api/healthz`为200而`/api/readyz`为404。正式域名尚未运行T21/T22产物，因此“无HMR”、新就绪契约和正式静态拓扑均不能勾选通过。
- 真实墨灵只读证据：`.venv312\Scripts\python.exe -m backend.main_api.tools.moling_auth_preflight`返回`status=accepted`；只读计费验证返回权益3条、可用3条、余额查询成功且`billing_enabled=false`。未输出token、权益详情或余额数值；未调用reserve/settle/release。
- 配置准备度：当前解析结果为非production，正式应用基址未配置，SSO、持久化、对象存储和Worker均关闭，`BILLING_ENABLED=false`，真实计费金额未配置，O-09生产容量未确认。这是安全开发配置，不是生产就绪证据。
- B-06真实闭环：不停止归属未知的既有6800/9100进程，只在本轮6801/9101/10012启动当前代码；`/readyz`显示outline/content/personaldb全部`up`。TXT真实上传后完成缓存转换、向量化和同一复合主体知识库检索；依据大纲HTTP 200，随后最小单页依据正文HTTP 200、5095字符且含`[DONE]`。长篇大纲调用持续返回处理中但页数过多，主动取消且不计完成。最后只停止本轮三个服务并确认端口全部释放，据此关闭B-06。
- 继承真实证据：T20已完成真实对象存储PPTX往返、服务端/本地SHA-256一致和Microsoft PowerPoint只读实际打开；T22已完成四档正式静态浏览器、深链和无HMR本地验证。这些证据有效，但不冒充正式域名、两个真实用户或真实积分UAT。
- 自动化基线：沿用T22最终后端263通过、前端74通过、类型检查和正式构建通过；本轮`git diff --check`无空白错误，仅报告工作区既有LF/CRLF提示。T23报告逐项区分自动化、真实只读、真实最小联调、Mock和未验证边界。
- G5未满足：正式域名仍暴露Vite；真实入口仅完成只读预检；没有两名真实墨灵用户完整生成/作品/编辑/保存/导出/历史下载隔离；没有真实reserve→settle、失败release、重试和未知终态的双账比对；没有生产回滚和值班演练签字。
- 阻塞解除条件：由授权运维部署T22同版本产物、执行生产迁移并提供受控验收流量；运营确认O-09及reserve/settle积分；安全准备两名真实测试用户；单独授权有次数和积分上限的计费UAT；指定TLS/监控/回滚负责人。凭据不得进入聊天、日志或文档，通常生产计费继续关闭。
- 风险与回滚：当前未改生产状态，无外部回滚动作。未来验收失败先保持/恢复`BILLING_ENABLED=false`、暂停新收费任务并回滚上一镜像；迁移保持向前兼容，禁止删表或清理用户对象。未commit、push、创建PR、部署、生产迁移、真实计费或切换流量。
- 最小决策请求：请授权并安排上述受控验收环境、运营值、两名用户和小额计费窗口；在此之前依赖链停在G5，不将T23或Goal标记完成。

### 2026-07-23 T23 连续阻塞复查（第2次）

- 正式域名再次只读核对：`/`与`/works`仍为HTTP 200、`no-cache`并包含`/@vite/client`，`/api/healthz`为200而`/api/readyz`为404；没有部署T22产物的证据。
- 墨灵再次只读核对：鉴权预检为`accepted`；权益3条、可用3条、余额可查、`billing_enabled=false`。未输出秘密或数值余额，未执行计费写入。
- 准备度再次核对：当前仍非production，SSO/持久化/对象存储/Worker关闭；计费关闭，reserve/settle金额、O-09生产容量和两名UAT用户均未配置。
- 结论：相同阻塞条件连续第二次出现。Goal仍保持`in_progress`，因为阻塞审计尚未达到三轮阈值；T23保持`blocked`，G5不跨越。下一次继续前先检查外部状态是否变化。

### 2026-07-23 T23 连续阻塞复查（第3次）

- 正式域名第三次复查仍加载`/@vite/client`，`/api/readyz`仍为404；墨灵鉴权与权益只读查询仍通过且`billing_enabled=false`。
- 当前仍非production，无正式应用基址；SSO、持久化、对象存储、Worker关闭，计费金额、O-09生产容量和两名UAT用户均未准备。
- 同一阻塞条件已连续出现三轮。完成G5所需的部署、生产迁移、受控流量、真实计费写入和双用户UAT均超出当前授权或缺少外部输入，已没有可在现有权限内继续完成的验收工作。
- Goal状态同步为`blocked`；T23保持`blocked`、已完成任务仍为22、生产计费与生产流量继续关闭。用户提供解除条件后恢复时，先重新审计外部状态，再继续T23，不重做已完成的T01～T22和B-06证据。

### 2026-07-23 T23 Goal恢复复查（恢复后第1次）

- 用户明确要求“继续”，因此从T23断点恢复Goal；`goal_status`恢复为`in_progress`，不重做T01～T22，也不把既有本地、Mock或只读证据重复冒充G5真实验收。
- 正式域名实时只读核对：`/`与`/works`均为HTTP 200、`no-cache`并继续包含`/@vite/client`；`/api/healthz`为200，`/api/readyz`为404。正式域名仍没有部署T22同版本静态产物。
- 墨灵实时只读核对：内部鉴权预检为`accepted`；权益3条、可用3条、余额读取成功，`billing_enabled=false`。本轮未输出秘密、用户标识、权益明细或余额数值，未调用reserve、settle或release。
- 当前本地解析配置为`development`，应用基址已有配置但不是production验收环境；SSO、持久化、对象存储和Worker关闭，计费关闭，真实reserve/settle金额与O-09生产容量仍未配置。两名真实UAT用户及生产发布/回滚负责人仍无准备证据。
- 结论：恢复后的第1次审计仍命中相同外部阻塞。T23保持`blocked`、G5不通过，生产计费与生产流量继续关闭；Goal保持`in_progress`，等待授权或外部状态变化后再次审计。

### 2026-07-23 T23 Goal恢复复查（恢复后第2次）

- 工作区仍完整保留T01～T23既有改动，未发现新的生产部署、运营决策、双用户UAT或计费授权文件；未执行reset、clean、checkout、commit、push、部署或删除。
- 正式域名重新请求后结果不变：`/`和`/works`均为HTTP 200、`no-cache`且包含`/@vite/client`；`/api/healthz`为200，`/api/readyz`为404。
- 墨灵只读探针重新执行：内部鉴权为`accepted`；权益3条、可用3条、余额读取成功、`billing_enabled=false`。未调用reserve、settle或release，未输出任何秘密或数值余额。
- 当前配置仍为`development`；应用基址已配置但不是production验收，SSO、持久化、对象存储、Worker、计费均关闭；真实reserve/settle金额和O-09生产容量仍未配置。模板中的非生产默认容量不作为生产确认值。
- 结论：恢复后的相同阻塞条件连续第2次出现。T23保持`blocked`、G5不通过；Goal保持`in_progress`，生产计费与生产流量保持关闭。下一轮先再次核对外部状态，不能用只读成功代替真实写入和双用户验收。

### 2026-07-23 T23 Goal恢复复查（恢复后第3次）

- 工作区与外部准备信号再次核对，仍没有生产部署授权、真实计费值、O-09生产容量、两名真实UAT用户或生产发布/回滚负责人的新增证据。
- 正式域名第三次实时请求仍为开发态：`/`和`/works`返回HTTP 200、`no-cache`并含`/@vite/client`；`/api/healthz`为200，`/api/readyz`为404。
- 墨灵只读探针第三次仍通过：内部鉴权`accepted`，权益3条、可用3条、余额读取成功、`billing_enabled=false`；没有任何平台写入。
- 当前配置第三次仍为`development`，SSO、持久化、对象存储、Worker和计费关闭；真实reserve/settle金额与生产容量未配置。模板中的非生产默认容量不构成运营确认。
- 结论：恢复后的同一阻塞条件已连续出现三轮。完成T23/G5需要新的生产部署/迁移/受控流量授权、运营值、两名真实用户和有上限的计费UAT授权，当前已无可在既定权限内继续完成的验收工作。Goal正式恢复为`blocked`；生产计费与生产流量继续关闭，未来解除条件后从T23再次恢复，不重做T01～T22。

### 2026-07-23 T23 生产验收授权恢复记录

- 用户已明确授权：在受控验收环境部署T22产物、执行向前兼容生产迁移、切换受控验收流量，并在有限次数和有限积分范围内执行真实计费UAT；允许两个真实测试账号完成入口、生成、编辑、保存、导出、历史下载和跨用户隔离；失败时关闭计费、暂停新任务并回滚上一版本；禁止删除生产表、用户文件或扩大到普通生产流量。
- 权限阻塞已解除，Goal与T23恢复执行，`goal_status`更新为`in_progress`。该授权不等同于验收完成，也不自动提供生产主机访问、运营数字、测试账号或回滚负责人。
- 当前盘点：本机没有Docker CLI，用户SSH配置中没有部署Host；仓库与本地环境未发现生产主机访问目标。`.env`仍为开发配置，未配置真实reserve/settle积分、O-09生产容量或两个UAT账号的安全引用。
- 安全门禁：在部署目标、非敏感运营数字、计费最大次数/积分上限、两名账号安全准备信号和生产责任人明确前，继续保持`BILLING_ENABLED=false`与`production_traffic_enabled=false`，不执行猜测性生产写入。
