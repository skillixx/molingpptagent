# TrainPPTAgent 对接墨灵平台及功能增强需求分析

> 文档状态：DRAFT（需求分析，不代表功能已实现）  
> 编写日期：2026-07-22  
> 适用项目：`D:\molinggithub\TrainPPTAgent`  
> 修改边界：只规划 TrainPPTAgent，不修改、复制或覆盖 `D:\molingproject\molinppt` 代码  
> 名词说明：本文将“墨灵平台”简称为“墨灵”，接口契约以本项目 `molin_docs/app/` 中现有文档为准。

## 1. 文档目的

本次建设的目标不是把另一个 PPT 项目覆盖进 TrainPPTAgent，而是在保留 TrainPPTAgent 现有大纲生成、内容生成、模板选择、PPTist 在线编辑和 PPTX 导出能力的基础上，补齐以下两类能力：

1. **墨灵平台对接**：用户从墨灵进入 TrainPPTAgent 后免登录使用，TrainPPTAgent 能识别真实用户、校验产品权益，并按照墨灵计费契约完成额度预占、结算、释放和异常对账。
2. **产品功能增强**：用户能够查看自己生成过的 PPT 列表，打开历史作品，继续二次编辑，自动或手动保存，并重新导出 PPTX。

本文用于产品确认、技术评审、任务拆分和后续验收，不包含正式代码开发。

## 2. 用户与业务价值

### 2.1 目标用户

- 已在墨灵购买或获得 PPT 产品权益的普通用户。
- 需要通过主题、上传文件或已有大纲生成 PPT 的用户。
- 需要跨页面、刷新浏览器或下次登录后继续编辑历史 PPT 的用户。
- 需要查看任务、计费和失败原因的运营及技术支持人员。

### 2.2 当前用户问题

1. TrainPPTAgent 没有接入墨灵一次性启动票据，无法形成可信的墨灵用户登录态。
2. 后端部分接口直接接受前端传入的 `user_id`，服务端没有证明该 ID 属于当前访问者，存在越权读取文件或冒用身份的风险。
3. 编辑器中的作品数据主要保存在前端 Pinia 和临时 IndexedDB 中。刷新、关闭页面、清理浏览器数据或更换设备后，不能可靠恢复作品。
4. PPTX 由浏览器直接下载，平台没有稳定保存“作品记录、当前编辑稿、导出文件、缩略图和版本”的完整关系。
5. 用户没有统一的“我的作品”入口，无法完成“生成后找到文件 → 打开 → 修改 → 保存 → 再次导出”的闭环。
6. 生成过程没有接入墨灵额度预占与结算，无法避免并发超额、生成失败仍扣费或重复请求重复扣费。

## 3. 已核实的当前状态

核实日期：2026-07-22。以下结论来自 TrainPPTAgent 当前代码的静态检查，未代表生产环境已经运行验证。

| 模块 | 当前能力 | 当前缺口 | 代码依据 |
|---|---|---|---|
| 前端路由 | 已有大纲、编辑器、PPT 和 APP 页面 | 没有“我的作品”和作品详情路由 | `frontend/src/router/index.ts:4-23` |
| 编辑状态 | Pinia 保存当前幻灯片，Dexie/IndexedDB 保存撤销快照 | 没有用户级服务端作品持久化 | `frontend/src/store/slides.ts:35-161`、`frontend/src/store/snapshot.ts:13-124` |
| 临时数据库 | 页面离开时把当前数据库 ID 放入待清理列表 | 不能作为长期历史作品存储 | `frontend/src/App.vue:31-50` |
| PPTX 导出 | 使用 PptxGenJS 在浏览器生成并下载 | 导出文件和版本没有自动归档到服务端 | `frontend/src/hooks/useExport.ts:445-958` |
| 主 API | 已有大纲、文件生成、模板和健康检查接口 | 没有登录 Session、作品 CRUD 和所有权校验 | `backend/main_api/main.py:60-381` |
| 用户标识 | 上传与生成请求可携带 `user_id`/`sessionId` | 用户 ID 来自客户端，不可作为可信身份 | `backend/main_api/main.py:67-103`、`:205-217`、`:312-318` |
| 跨域策略 | 当前允许任意来源 | 生产环境需要改为墨灵和应用域名白名单 | `backend/main_api/main.py:36-44` |
| 服务部署 | 由 main、outline、content、personaldb、frontend 五个服务组成 | 缺少业务数据库、内部服务鉴权和持久化任务协调 | `docker-compose.yml:2-94` |
| 模型配置 | 支持多模型、写作模型、检查模型及三个内部服务地址 | 尚未包含墨灵平台、应用、Session、计费和作品存储配置 | `env_template.txt:87-134` |

### 3.1 应保留且不得破坏的现有能力

- 主题生成大纲。
- 根据上传文件生成大纲。
- 大纲确认后逐页生成内容。
- 模板选择与内容填充。
- PPTist 在线编辑能力。
- 图表、图片、文本、形状等现有页面元素。
- PPTX 浏览器端导出能力。
- `outline_api`、`content_api`、`personaldb` 现有服务的内部职责。
- 已有模型供应商配置方式，新增配置不得要求用户重复填写同一份模型密钥。

## 4. 本期范围

### 4.1 P0：墨灵平台对接

1. 墨灵一次性启动票据登录。
2. TrainPPTAgent 应用 Session。
3. 从服务端 Session 获取当前用户，禁止前端自行指定操作用户。
4. 查询用户对应产品的可用权益。
5. 生成整套 PPT 的额度预占、成功结算、失败释放。
6. 幂等控制和计费异常对账。
7. 用户级作品、文件和任务权限隔离。
8. 生产环境跨域白名单、内部接口密钥和敏感配置管理。

### 4.2 P0：历史作品与二次编辑

1. “我的作品”列表。
2. 作品详情和完整幻灯片 JSON 加载。
3. 打开历史作品进入 PPTist 编辑器。
4. 手动保存与防抖自动保存。
5. 乐观锁版本控制，防止多标签页静默覆盖。
6. 保存作品标题、缩略图、页数、状态和更新时间。
7. 从当前版本重新导出 PPTX，并保存导出记录。
8. 软删除作品；已删除作品默认不出现在列表中。

### 4.3 P1：可恢复任务与使用体验

1. 生成任务进度查询。
2. 网络中断后按原任务 ID 恢复状态，不直接重复创建收费任务。
3. 失败任务在确认计费终态后允许重试。
4. 作品列表分页、搜索、排序和状态筛选。
5. 自动保存状态提示：保存中、已保存、保存失败、版本冲突。
6. 桌面、平板和手机适配；手机端至少支持列表查看、预览和基础文字编辑。

### 4.4 本期明确不做

- 不修改 `D:\molingproject\molinppt` 的任何文件。
- 不迁移 molinppt 的历史数据库和历史作品。
- 不复制 molinppt 的模板渲染器或 Node.js 业务代码。
- 不开发多人实时协同编辑。
- 不开发公开模板交易市场、团队空间、组织权限和审批流。
- 不在本期实现 PPTX 导入后百分之百还原所有 PowerPoint 特效。
- 不把墨灵 `INTERNAL_API_TOKEN` 或模型密钥下发给浏览器。
- 不把尚未联调的外部接口描述为已经通过。

## 5. 总体业务流程

```text
墨灵用户点击“打开应用”
        │
        ▼
TrainPPTAgent 接收一次性 launch_ticket
        │
        ├─ 服务端向墨灵验证票据
        ├─ 校验 app_id / product_id
        ├─ 解析可用 entitlement_id
        └─ 创建 TrainPPTAgent HttpOnly Session
        │
        ▼
用户进入“我的作品”或创建新 PPT
        │
        ├─ 创建任务并生成全局幂等键
        ├─ 墨灵预占额度 reserve
        ├─ 调用 outline/content Agent
        ├─ 成功：保存作品 → settle
        └─ 失败：保存失败状态 → release
        │
        ▼
用户打开作品 → PPTist 编辑 → 自动保存 → 再次导出
```

### 5.1 登录流程

1. 墨灵将用户跳转到 TrainPPTAgent，例如：`GET /auth/launch?ticket=lt_xxx`。
2. TrainPPTAgent 后端调用 `POST /api/internal/app-launch/verify`，请求头携带 `X-Internal-Token`。
3. 平台返回 `user_id`、`app_id`、`product_id`；TrainPPTAgent 必须与本地配置的应用和产品 ID 比对。
4. 票据验证成功后，后端创建应用 Session，并通过 `HttpOnly`、`SameSite=Lax` Cookie 返回浏览器。
5. 浏览器后续只使用 Session Cookie，不再提交可信 `user_id`。
6. 票据过期、已消费、应用不匹配或内部鉴权失败时，不创建 Session，并展示可追踪的中文错误。

### 5.2 权益解析与计费流程

本期建议采用墨灵 prepaid 额度模式。具体扣减单价由墨灵商品/套餐运营配置决定，TrainPPTAgent 不写死商业价格。

1. 使用 `GET /api/internal/user-entitlements?user_id={uid}&product_id={pid}` 获取当前产品可用权益。
2. 使用 `GET /api/internal/entitlement-balance` 查询 `remaining` 和 `usable`。
3. 整套 PPT 生成属于耗时且可能失败的操作，必须执行：
   - 开始前：`POST /api/internal/entitlement-reserve`。
   - 成功后：`POST /api/internal/entitlement-settle`。
   - 失败后：`POST /api/internal/entitlement-release`。
4. reserve、settle、release 必须使用不同但可重复计算的 `idempotency_key`。
5. reserve 结果未知、settle 失败或 release 失败时，将任务标记为 `billing_pending`，禁止用户直接重复发起同一收费操作。
6. 后端对账任务重试原结算或释放请求；对账成功后再开放作品或重试入口。
7. 浏览器不得直接调用任何 `/api/internal/*` 接口。

### 5.3 作品创建和保存流程

1. 用户确认大纲后，后端先创建 `presentation` 和 `generation_task`。
2. Agent 逐页生成时，前端可以流式展示，但服务端仍以任务 ID 记录生成状态。
3. 生成完成后，将完整 `slides JSON` 保存为作品当前版本，而不是只保留在 Pinia。
4. 编辑器加载历史作品时，先读取服务端当前版本，再初始化 Pinia 和撤销快照。
5. 用户编辑后触发 2 秒防抖自动保存；页面离开前若仍有未保存修改，必须显示确认提示。
6. 每次保存携带 `version`。版本不一致返回 HTTP 409，前端提示用户刷新最新版本或另存副本。
7. 自动保存失败时保留浏览器内的未提交草稿，恢复网络后可再次保存，但不得静默覆盖服务端新版本。

## 6. 功能需求

### FR-01 墨灵免登录

- 用户从墨灵应用入口进入后，无需再次输入账号密码。
- 启动票据只能使用一次，过期或重放必须拒绝。
- 登录成功后跳转到 `/works`；首次使用且没有作品时展示空状态和“新建 PPT”按钮。
- `GET /api/me` 返回当前用户 ID、当前产品 ID、可用权益摘要和 Session 到期时间。

### FR-02 我的作品列表

- 新增路由 `/works`。
- 默认按 `updated_at` 倒序显示当前用户未删除的作品。
- 每页默认 20 条，支持第 1 页开始的分页。
- 每个作品卡片至少展示：缩略图、标题、页数、状态、最近更新时间。
- 支持标题关键字搜索和状态筛选。
- 只允许查看当前 Session 用户自己的作品。
- 空列表、加载失败、无权限和服务不可用必须有不同提示。

### FR-03 打开历史作品

- 新增路由 `/editor/:presentationId`。
- 打开时请求作品详情及当前 `slides JSON`。
- `generating` 状态进入任务进度页；`billing_pending` 状态禁止编辑和导出；`ready` 状态进入编辑器。
- 作品不存在、已删除或不属于当前用户时统一返回 404，避免泄露其他用户作品是否存在。
- 刷新浏览器后仍能重新加载同一作品。

### FR-04 二次编辑与保存

- 支持 PPTist 当前已有的文本、图片、形状、图表和页面级编辑。
- 支持 Ctrl+S/Command+S 手动保存。
- 支持停止编辑 2 秒后的自动保存。
- 顶部显示保存状态和最近成功保存时间。
- 保存请求包含当前 `version`；服务端成功后返回递增的新版本。
- 版本冲突时不覆盖服务器数据，并提供“加载最新版本”和“另存为副本”两个操作。
- 单次作品 JSON 请求体上限建议为 10 MiB，超过限制时给出可执行的资源压缩提示。

### FR-05 导出与文件归档

- 保留现有浏览器端 PptxGenJS 导出能力。
- 导出成功后，将生成的 PPTX 上传到服务端并写入导出记录。
- “我的作品”详情显示最新导出文件及导出时间。
- 下载前必须再次校验文件归属。
- 文件下载响应应使用短期签名地址或受 Session 保护的下载接口，并设置 `Cache-Control: no-store`。
- 同一作品允许存在多次导出记录，但列表默认只展示最新一次。

### FR-06 删除与恢复边界

- 删除作品采用软删除，不立即物理删除对象存储文件。
- 删除操作需要二次确认。
- 已删除作品不能继续编辑、导出或通过旧地址下载。
- 后台物理清理及回收站恢复不属于本期前台范围，但数据模型应预留 `deleted_at`。

### FR-07 任务与失败恢复

- 每次收费生成操作必须先创建持久化任务。
- 前端按任务 ID 查询状态，不能仅依赖当前 SSE 连接是否存在。
- 网络超时后先查询原任务状态，再决定是否允许重试。
- 状态至少包括：`queued`、`running`、`billing_pending`、`succeeded`、`failed`、`cancelled`。
- 失败响应包含稳定的业务错误码、中文提示、是否可重试和 `request_id`，不返回供应商原始响应、密钥或堆栈。

## 7. 页面与交互需求

| 页面/区域 | 主要内容 | 桌面端 | 平板端 | 手机端 |
|---|---|---|---|---|
| 墨灵登录处理中 | 加载状态、失败原因、返回墨灵入口 | 居中卡片 | 居中卡片 | 满屏卡片 |
| 我的作品 `/works` | 搜索、筛选、作品卡片、新建按钮 | 3～4 列 | 2 列 | 1 列 |
| 作品编辑 `/editor/:id` | 缩略图栏、画布、属性面板、保存状态 | 三栏完整编辑 | 可折叠侧栏 | 单画布＋抽屉式工具栏 |
| 任务进度 | 当前阶段、进度、耗时、失败建议 | 页面/弹窗 | 页面/弹窗 | 全屏状态页 |
| 导出记录 | 最新文件、时间、下载和重新导出 | 表格/抽屉 | 列表 | 卡片列表 |

响应式验收宽度至少覆盖：`1440px`、`1024px`、`768px`、`390px`。编辑画布必须保持 16:9 比例缩放，不因响应式布局改变内部坐标系。

## 8. 后端接口需求

以下是 TrainPPTAgent 自身的应用接口，不是墨灵平台内部接口。所有 `/api/*` 用户接口除健康检查和启动票据入口外，都必须校验应用 Session。

### 8.1 身份接口

#### `GET /auth/launch?ticket={launch_ticket}`

- 验证墨灵启动票据并创建 Session。
- 成功：HTTP 302 跳转 `/works`。
- 失败：跳转到登录失败页面，禁止在 URL 中回显票据。

#### `GET /api/me`

```json
{
  "user_id": 123,
  "app_id": 15,
  "product_id": 73,
  "entitlement": {
    "id": 456,
    "remaining": "20",
    "usable": true
  },
  "session_expires_at": "2026-07-29T10:00:00Z"
}
```

### 8.2 作品接口

#### `GET /api/presentations?page=1&page_size=20&keyword=&status=`

```json
{
  "items": [
    {
      "id": "ppt_uuid",
      "title": "季度经营汇报",
      "status": "ready",
      "slide_count": 12,
      "thumbnail_url": "/api/files/file_uuid",
      "version": 7,
      "updated_at": "2026-07-22T09:30:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

#### `POST /api/presentations`

- 创建作品和生成任务。
- 请求包含主题、大纲、模板、页数和生成来源。
- `owner_user_id` 必须来自 Session，不接受浏览器提交。
- 返回 HTTP 202、`presentation_id` 和 `task_id`。

#### `GET /api/presentations/{id}`

- 返回作品元信息、当前完整 `slides` 和 `version`。
- 非本人作品统一返回 404。

#### `PATCH /api/presentations/{id}`

```json
{
  "title": "季度经营汇报（修订版）",
  "slides": [],
  "version": 7
}
```

- 保存成功返回新版本 `8`。
- 版本冲突返回 HTTP 409、错误码 `PRESENTATION_VERSION_CONFLICT` 和服务端当前版本号。

#### `POST /api/presentations/{id}/duplicate`

- 在版本冲突或用户主动另存时创建副本。
- 新副本归当前 Session 用户所有，版本从 1 开始。

#### `DELETE /api/presentations/{id}`

- 执行软删除。
- 重复删除必须幂等。

### 8.3 任务和导出接口

#### `GET /api/tasks/{task_id}`

- 返回任务状态、进度、错误码、是否可重试和计费状态。
- 只允许任务所有者查询。

#### `POST /api/presentations/{id}/exports`

- 接收浏览器生成的 PPTX 文件或由后端触发导出。
- 返回 `export_id`、`file_id`、文件名和创建时间。

#### `GET /api/files/{file_id}`

- 校验 Session 用户与文件所有者一致后下载。
- 已删除作品关联文件不可下载。

## 9. 数据模型需求

生产环境建议使用 MySQL 或 PostgreSQL 保存业务数据。向量知识库只用于文档检索，不得代替业务数据库保存作品和计费状态。

| 数据表 | 核心字段 | 用途 |
|---|---|---|
| `app_sessions` | `id`、`user_id`、`app_id`、`product_id`、`entitlement_id`、`expires_at` | TrainPPTAgent 登录态 |
| `presentations` | `id`、`owner_user_id`、`title`、`status`、`slide_count`、`current_version`、`thumbnail_file_id`、`deleted_at` | 作品主记录 |
| `presentation_versions` | `id`、`presentation_id`、`version`、`slides_json`、`created_by`、`created_at` | 当前稿及可追踪版本 |
| `generation_tasks` | `id`、`presentation_id`、`owner_user_id`、`status`、`progress`、`error_code`、`request_id` | 可恢复生成任务 |
| `billing_operations` | `id`、`task_id`、`entitlement_id`、`hold_id`、`reserved_amount`、`actual_amount`、`status`、`idempotency_key` | 计费终态和对账 |
| `files` | `id`、`owner_user_id`、`presentation_id`、`role`、`storage_key`、`mime_type`、`size_bytes`、`status` | PPTX、缩略图和上传文件 |
| `exports` | `id`、`presentation_id`、`version`、`file_id`、`format`、`created_at` | 每次导出记录 |

数据约束：

- `presentations(owner_user_id, updated_at)` 建联合索引，支持用户作品列表。
- `presentation_versions(presentation_id, version)` 必须唯一。
- `billing_operations.idempotency_key` 必须唯一。
- `files.storage_key` 必须唯一，且不得接受包含绝对路径或 `..` 的客户端输入。
- 删除作品时只写 `deleted_at` 和状态；物理文件清理由独立后台任务处理。

## 10. 配置需求

在根目录 `env_template.txt` 中增加占位配置，真实密钥只允许写入未提交的 `.env` 或云端密钥服务。

| 配置项 | 必填 | 说明 |
|---|---|---|
| `MOLIN_API_BASE_URL` | 是 | 墨灵平台服务端地址 |
| `MOLIN_INTERNAL_API_TOKEN` | 是 | TrainPPTAgent 调用墨灵内部接口的共享密钥 |
| `MOLIN_APP_ID` | 是 | TrainPPTAgent 在墨灵的应用 ID |
| `MOLIN_PRODUCT_ID` | 是 | 对应计费商品 ID |
| `APP_BASE_URL` | 是 | TrainPPTAgent 对外访问地址 |
| `SESSION_SECRET` | 是 | 应用 Session 签名或加密密钥 |
| `SESSION_TTL_SECONDS` | 是 | Session 有效期 |
| `DATABASE_URL` | 是 | 业务数据库连接串 |
| `STORAGE_ENDPOINT` | 生产必填 | S3/OSS/MinIO 兼容对象存储地址 |
| `STORAGE_BUCKET` | 生产必填 | PPT 文件 Bucket |
| `STORAGE_ACCESS_KEY_ID` | 生产必填 | 对象存储访问标识 |
| `STORAGE_SECRET_ACCESS_KEY` | 生产必填 | 对象存储密钥 |
| `CORS_ALLOWED_ORIGINS` | 是 | 允许访问 API 的应用域名白名单 |
| `BILLING_RECONCILE_INTERVAL_SECONDS` | 是 | 计费异常对账周期 |

现有 `MODEL_PROVIDER`、`LLM_MODEL`、`PPT_WRITER_*`、`PPT_CHECKER_*`、`OUTLINE_API`、`CONTENT_API` 和 `PERSONAL_DB` 保持兼容，不要求重复配置。

## 11. 权限与安全要求

1. 所有用户资源均以服务端 Session 中的 `user_id` 作为所有者，禁止相信请求体、表单或 URL 中的用户 ID。
2. `/api/internal/*` 只允许后端调用，使用 `X-Internal-Token` 和 IP 白名单，禁止经过公网前端代理暴露。
3. Session Cookie 必须设置 `HttpOnly`；生产环境设置 `Secure`；默认 `SameSite=Lax`。
4. 启动票据、内部 Token、模型密钥、对象存储密钥不得出现在前端包、URL、日志和错误响应中。
5. CORS 不得继续使用 `*`，必须读取 `CORS_ALLOWED_ORIGINS`。
6. 作品查询、保存、删除、导出和下载都必须执行 owner 校验。
7. 错误日志记录 `request_id`，但需要脱敏原始模型响应、文件本地路径、Cookie、Token、用户隐私和计费 hold 标识。
8. 上传文件必须校验 MIME、扩展名、实际文件签名和大小；文件名不能直接拼接为服务器路径。
9. 生成、保存和删除接口应有用户级速率限制。

## 12. 非功能需求

### 12.1 性能目标

- 作品列表在 1,000 条用户作品规模下，服务端 P95 响应时间不高于 500 ms，不包含公网网络耗时。
- 作品详情在 `slides JSON ≤ 10 MiB` 时，服务端 P95 响应时间不高于 1 s。
- 自动保存防抖时间为 2 秒；正常网络下保存请求完成后 1 秒内更新为“已保存”。
- 首屏不一次性加载所有作品缩略图原图，列表使用压缩缩略图和懒加载。

### 12.2 可用性目标

- 用户刷新编辑页面后能恢复到同一作品。
- SSE 中断不等于任务失败，前端可通过任务接口恢复状态。
- 计费终态未知时默认锁定收费操作，不能通过重复点击造成重复生成或重复扣费。
- 对象存储暂时不可用时，编辑稿仍可保存到数据库；导出文件状态标记为失败并允许后续重试。

### 12.3 可观测性目标

- 每个 HTTP 响应包含 `X-Request-Id`。
- 生成任务、计费操作、作品 ID 和请求 ID 可关联查询。
- 至少记录登录验证、创建任务、生成成功/失败、计费预占/结算/释放、保存冲突、导出和下载审计事件。

## 13. 失败场景要求

| 场景 | 期望处理 |
|---|---|
| 启动票据过期或重复使用 | 拒绝登录，不创建 Session，提示从墨灵重新打开应用 |
| 用户没有可用权益 | 禁止开始收费任务，引导用户返回墨灵购买或续费 |
| reserve 明确失败 | 不调用生成 Agent，不创建可编辑成品 |
| reserve 返回结果未知 | 标记 `billing_pending`，先查账或对账，禁止立即重复请求 |
| Agent 生成失败 | 保存失败任务；已成功 reserve 时调用 release |
| settle 失败 | 保留生成结果但锁定编辑/导出，完成对账后开放 |
| release 失败 | 不承诺已经退款，标记待对账并禁止原任务直接重试 |
| 自动保存断网 | 保留本地未保存草稿，显示失败状态，恢复网络后重试 |
| 两个标签页同时保存 | 后提交的旧版本收到 409，不覆盖新版本 |
| 对象存储失败 | 作品编辑稿可保存；缩略图或导出记录显示待重试 |
| 用户访问他人作品或文件 | 统一返回 404，不泄露资源存在性 |

## 14. 分阶段实施建议

| 阶段 | 内容 | 优先级 | 依赖 |
|---|---|---|---|
| M1 | 业务数据库、Session、墨灵票据验证、`/api/me`、owner 中间件 | P0 | 墨灵应用配置和内部 Token |
| M2 | 作品表、版本表、作品 CRUD、`/works` 列表和历史打开 | P0 | M1 |
| M3 | 编辑器自动保存、版本冲突、另存副本、响应式适配 | P0 | M2 |
| M4 | 持久化生成任务、reserve/settle/release、异常对账 | P0 | M1、M2、墨灵权益配置 |
| M5 | PPTX 上传归档、下载鉴权、缩略图和导出记录 | P0 | M2、对象存储 |
| M6 | 搜索筛选、任务恢复、运营观测和体验优化 | P1 | M1～M5 |

依赖关系：

```text
M1 身份与数据基础
 ├─> M2 作品持久化 ──> M3 二次编辑与保存
 │                  └─> M5 导出与文件归档
 └─> M4 计费与任务恢复

M2 + M3 + M4 + M5 ──> M6 完整体验与运营观测
```

排序原因：必须先得到可信用户身份，才能正确建立作品所有权和计费关系；必须先完成服务端作品持久化，历史打开、自动保存和导出归档才有可靠数据对象。

## 15. 验收标准

### 15.1 墨灵接入

1. 有效启动票据能够创建 Session 并跳转 `/works`。
2. 无效、过期、已使用票据不能创建 Session。
3. 浏览器请求即使伪造 `user_id`，也不能读取、修改、删除或下载其他用户资源。
4. 生成整套 PPT 成功时，出现且只出现一次 reserve 和一次 settle，预占余额最终归零。
5. 生成明确失败时，已预占额度执行 release，作品状态为失败且不会出现在可编辑成品列表中。
6. settle/release 失败时任务进入待对账状态，用户不能直接重复发起同一收费操作。
7. 前端包、浏览器网络响应和普通日志中不包含内部 Token、模型密钥和对象存储密钥。

### 15.2 历史作品与二次编辑

1. 用户生成完成后，作品在 `/works` 列表中出现。
2. 关闭并重新打开浏览器后，登录同一用户仍能找到作品。
3. 点击作品后可以加载完整幻灯片进入 `/editor/:presentationId`。
4. 修改标题或页面元素后，2 秒内触发自动保存并显示新版本。
5. 刷新编辑页面后，服务端返回的内容与最后一次成功保存一致。
6. 两个标签页编辑同一版本时，第二个旧版本保存返回 409，服务器内容不被覆盖。
7. 导出 PPTX 后产生归属当前用户的导出记录，用户可以再次下载。
8. 用户 A 无法通过猜测作品 ID 或文件 ID 访问用户 B 的内容。
9. 删除作品后，列表、详情、编辑、导出和旧文件下载均不可用。

### 15.3 设备适配

1. 在 1440、1024、768、390 像素宽度下，作品列表无横向溢出。
2. 编辑画布在四种宽度下保持 16:9，不改变幻灯片内部逻辑坐标。
3. 手机端可打开作品、切换页面、修改基础文本并保存。
4. 保存状态、任务失败和计费待处理提示在四种宽度下均可见且不遮挡主要操作。

## 16. 测试计划

| 层级 | 测试内容 | 最低新增用例建议 |
|---|---|---:|
| 单元测试 | Session、owner 校验、版本冲突、幂等键、状态机、配置校验 | 30 |
| API 集成测试 | 票据登录、作品 CRUD、跨用户拒绝、任务查询、文件下载 | 20 |
| 墨灵契约测试 | user-entitlements、balance、reserve、settle、release 和异常映射 | 12 |
| 前端组件测试 | 作品卡片、空状态、保存状态、409 冲突、分页筛选 | 15 |
| E2E | 登录→生成→列表→打开→编辑→保存→导出→下载 | 6 |
| 响应式视觉检查 | 1440、1024、768、390 四档主要页面 | 4 组 |
| 安全测试 | 伪造 user_id、越权 ID、票据重放、CORS、路径穿越、密钥泄露 | 12 |

本地自动化通过不能替代真实墨灵测试账号、真实权益、真实对象存储和真实浏览器下载的联调验收，最终报告必须分别标注。

## 17. 回滚方案

1. 新功能通过环境开关控制，例如 `MOLIN_INTEGRATION_ENABLED`、`PRESENTATION_PERSISTENCE_ENABLED`。
2. 数据库迁移只能向前新增表和字段，回滚应用版本时保留新表，避免删除用户作品。
3. 新作品保存失败时可临时回退到现有单次编辑和本地导出流程，但必须明确提示“作品不会进入历史记录”。
4. 计费功能上线后不能通过清空内部 Token 来回滚；应关闭新收费入口并完成所有 `billing_pending` 对账。
5. 对象存储切换失败时保留数据库中的作品版本，暂停新导出，不删除已有文件索引。

## 18. 工作量初步估算

以下按一名熟悉 Vue、FastAPI 和关系数据库的开发人员估算，不包含墨灵平台侧运营审核等待时间。

| 工作项 | 估算 |
|---|---:|
| 墨灵登录、Session、配置与权限中间件 | 3～4 人日 |
| 作品/版本/任务/文件数据模型与迁移 | 3～4 人日 |
| 作品列表、详情、删除和历史打开 | 4～5 人日 |
| 编辑器自动保存、冲突处理、另存副本 | 4～6 人日 |
| prepaid 计费、幂等、状态机和对账 | 5～7 人日 |
| PPTX 归档、缩略图和下载鉴权 | 3～4 人日 |
| 响应式 UI 适配 | 3～4 人日 |
| 自动化测试、真实联调和验收修复 | 6～8 人日 |
| **合计** | **31～42 人日** |

影响估算的主要变量：作品 JSON 实际大小、对象存储类型、墨灵计费单价和扣费时点、是否要求服务端生成 PPTX、是否要求完整版本历史恢复。

## 19. 待产品与运营确认

以下事项不阻塞需求文档成立，但在正式开发前必须确定：

1. 整套 PPT 生成的预占额度和实际结算规则。
2. 单页 AI 重新生成是否单独收费；普通手工编辑和自动保存建议不收费。
3. PPTX 导出是否收费；本需求建议本期不单独收费。
4. 作品保留期限、单用户作品数量和总存储上限。
5. 是否允许用户恢复软删除作品，以及回收站保留天数。
6. 是否保存所有历史版本；本期最低要求保存当前版本并保留可扩展的数据结构。
7. 手机端编辑范围是否只限基础文本，还是需要完整桌面编辑能力。
8. 生产环境使用 MySQL 还是 PostgreSQL，以及对象存储使用 OSS、S3 还是 MinIO。

## 20. 参考文档

- `molin_docs/app/developer-integration-guide.md`：应用接入总流程。
- `molin_docs/app-launch-entry-requirement.md`：启动票据及入口要求。
- `molin_docs/app/billing-integration-spec.md`：权益解析和计费接口契约。
- `molin_docs/app/developer-requirements.md`：应用侧安全与计费要求。
- `README.md`：TrainPPTAgent 当前功能和服务结构。
- `README_PRODUCTION.md`：当前部署说明。

## 21. 需求完成定义

本需求只有在以下条件全部满足时才能标记为完成：

1. P0 功能代码、数据库迁移、配置模板和运维说明均已交付。
2. 自动化测试覆盖身份、权限、作品、版本、任务、计费和文件链路。
3. 使用两个不同墨灵用户完成跨用户隔离测试。
4. 使用真实墨灵权益完成一次成功结算、一次失败释放和一次异常对账测试。
5. 在四档设备宽度完成作品列表、编辑、保存和导出人工验收。
6. 生成的 PPTX 已实际下载并使用 Microsoft PowerPoint 或兼容软件打开检查。
7. 验收报告明确区分本地测试、模拟接口、真实墨灵联调、对象存储和视觉检查结果。

