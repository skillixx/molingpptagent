# TrainPPTAgent 作品 API 契约（T09～T16）

## 1. 路径与身份

- 浏览器公共前缀：`/api`。
- Vite/Nginx 去掉一次 `/api` 后转发到主 API；例如公共 `GET /api/presentations` 对应后端 `GET /presentations`。
- 所有 owner 均来自服务端 HttpOnly Session。请求体、查询参数和路径不能指定 `owner_user_id`。
- SSO 开启时，`POST`、`PATCH`、`DELETE` 和复制操作必须携带与 `APP_BASE_URL` 一致的 `Origin`；跨站请求返回 HTTP 403。
- 响应返回 `X-Request-Id`。仅接受不超过128字符的安全请求ID字符集，否则服务端重新生成。

## 2. 创建作品与任务

`POST /api/presentations`

请求头：

```http
Idempotency-Key: create-client-request-001
Content-Type: application/json
```

请求体：

```json
{
  "title": "2026年季度经营汇报",
  "content": "生成一份季度经营汇报",
  "language": "chinese",
  "model": "deepseek-chat",
  "template_id": null,
  "generate_from_uploaded_file": false,
  "generate_from_web_search": true
}
```

规则：标题1～255字符，生成内容1～20000字符，模型最多64字符，模板ID最多64字符；两个布尔字段分别控制知识库和网络搜索。额外字段被拒绝，因此客户端不能注入owner、状态、任务ID或计费字段。`Idempotency-Key`在服务端Session用户作用域内唯一：同一owner、同一完整业务载荷的重试返回原作品/任务并令`reused=true`；同一owner复用键但改变标题、正文、语言、模型、模板、搜索模式或计费模式时返回脱敏409；不同owner可以安全使用相同客户端键，各自创建独立记录。

墨灵 SSO 构建下，模板页“生成PPT”必须调用本接口，不能再调用旧 `/tools/aippt` 流式入口绕过持久任务和预占。浏览器在网络重试时复用同一幂等键，创建成功后进入 `/editor/{presentation_id}` 状态页，页面轮询作品状态直至可编辑或明确失败。非 SSO 本地开发仍可保留旧流式路径用于兼容调试。

`BILLING_ENABLED=false`时，作品和非计费任务在同一事务内创建，状态分别为`generating`和`pending/queued`。`BILLING_ENABLED=true`时，作品、任务和一条计费意图在同一事务内创建，状态分别为`billing_pending`、`billing_required/awaiting_reserve`和`planned`；计费意图记录配置商品、预占/结算金额，并以任务ID派生互不相同的reserve、settle、release幂等键。T16不发起平台写调用，Worker也不能领取`billing_required`任务；只有T17预占成功后才能推进到可领取状态。计费状态后续已推进时，相同请求仍复用原任务，不因状态变化误报冲突。

HTTP 202：

```json
{
  "presentation": {
    "id": "8a835986-6b74-4e11-9fba-601725fef0d6",
    "title": "2026年季度经营汇报",
    "status": "generating",
    "current_version": 1,
    "slide_count": 0,
    "template_id": null,
    "thumbnail_file_id": null,
    "created_at": "2026-07-23T03:30:00Z",
    "updated_at": "2026-07-23T03:30:00Z"
  },
  "task": {
    "id": "db3f4ca5-1d15-4aa7-b030-b385757764e3",
    "status": "pending",
    "stage": "queued",
    "progress": 0,
    "retryable": true
  },
  "reused": false
}
```

## 3. 列表与详情

`GET /api/presentations?page=1&page_size=20&search=&status=&sort=updated_desc`

- `page`：1～10000；`page_size`：1～100，默认20。
- `search`：标题包含搜索，最多100字符；`%`和`_`按普通字符转义。
- `status`：`draft`、`generating`、`ready`、`failed`、`billing_pending`。
- `sort`：`updated_desc`、`updated_asc`、`created_desc`、`title_asc`；服务端以ID作稳定次排序。
- 软删除作品不会出现在列表。

HTTP 200：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_more": false
}
```

`GET /api/presentations/{presentation_id}` 返回上述摘要字段和解析后的`slides`当前编辑稿。不存在、已删除和他人作品均返回相同404。

T11起，当前稿标准结构为：

```json
{
  "schema_version": 1,
  "slides": [{ "id": "slide-1", "elements": [] }],
  "theme": {
    "themeColors": ["#5b9bd5"],
    "fontColor": "#333333",
    "fontName": "",
    "backgroundColor": "#ffffff"
  },
  "viewport_size": 1000,
  "viewport_ratio": 0.5625
}
```

`slides` 为PPTist完整页面数组，`theme`为可选主题覆盖，画布宽度允许320～10000，比例允许0.1～3。迁移期兼容缺少`schema_version`、`theme`和画布字段的旧`{"slides":[]}`，缺省值为版本1、PPTist默认主题、1000和0.5625。未知schema版本或畸形页面/元素结构在前端收敛为协议错误，不把部分稿件写入全局Store。精确10MiB UTF-8稿件可读；超限保存由PATCH契约拒绝，不在详情响应中回显原始错误或用户内容。

## 4. 保存当前稿

`PATCH /api/presentations/{presentation_id}`

```json
{
  "base_version": 7,
  "title": "2026年季度经营汇报（修订）",
  "slides": {
    "schema_version": 1,
    "slides": [{ "id": "slide-1", "elements": [] }],
    "theme": {},
    "viewport_size": 1000,
    "viewport_ratio": 0.5625
  }
}
```

只保存`ready`或`draft`作品，owner仍只取服务端Session；请求必须提交已读取的`base_version`，不能提交owner、状态、服务端当前版本或文件字段。服务端按UTF-8紧凑JSON计算`slides`大小，精确10MiB允许，超过返回HTTP 413；schema、页面骨架、元素ID/类型和视口损坏返回稳定422且不写入。保存以owner、作品ID、可编辑状态和`current_version = base_version`作为同一条条件更新，成功返回HTTP 200完整详情，原子更新标题、当前稿、页数和更新时间，并将`current_version`递增1。

同一浏览器实例通过2秒防抖和单请求在途队列避免自身乱序；断网稿先写按身份与作品隔离的IndexedDB，联网后不会自动重放，必须由用户确认。多标签或多设备以同一版本保存时只能有一个条件更新成功，失败方得到HTTP 409 `PRESENTATION_VERSION_CONFLICT`和不含稿件正文的`latest`摘要；客户端停止自动重试并保留本地草稿，必须由用户选择“加载最新”或“另存副本”。加载最新只有在重新读取成功后才删除本地草稿；读取失败仍保留冲突状态和草稿。

## 5. 复制与删除

`POST /api/presentations/{presentation_id}/duplicate`

```json
{
  "title": "季度经营汇报副本",
  "slides": { "schema_version": 1, "slides": [] }
}
```

标题可省略，默认追加“ 副本”并保持255字符上限；`slides`也可省略，普通复制沿用服务端当前稿。冲突处理可提交仍在浏览器内的合法本地稿，服务端在一个事务中创建独立副本；请求不能提交owner、源版本号或目标状态。副本不继承任务、版本号或瞬时生成/失败/计费状态，新作品版本固定从1开始；源作品为`ready`时副本为`ready`，其他状态统一为`draft`。成功返回HTTP 201及作品详情，原作品保持不变。

`DELETE /api/presentations/{presentation_id}` 执行软删除。owner重复删除返回HTTP 204；他人或从未存在的作品返回统一404。删除后列表和详情均不可见，后续编辑、文件和下载接口也必须继续校验作品未删除状态。

## 6. 检查点版本与恢复

`POST /api/presentations/{presentation_id}/versions` 为当前服务端版本创建检查点：

```json
{"base_version": 7, "reason": "manual"}
```

`reason`只允许`manual`、`ai`、`export`或`periodic`。请求不接收稿件正文和owner；服务端在owner、未删除、可编辑状态及当前版本校验后读取当前稿，按规范JSON计算SHA-256并以确定性gzip压缩。压缩后不超过`CHECKPOINT_INLINE_MAX_BYTES`（默认1MiB）才写入数据库；更大检查点在T19对象存储适配完成前返回HTTP 503 `CHECKPOINT_STORAGE_UNAVAILABLE`，不能回退为无界LONGTEXT。`(presentation_id, version)`唯一，同一当前版本重复创建返回HTTP 200及原摘要，首次创建返回201。

`GET /api/presentations/{presentation_id}/versions` 按版本倒序返回摘要：版本号、原因、UTC创建时间、规范正文SHA-256和解压字节数，不返回历史稿正文。默认只保留最近`CHECKPOINT_MAX_COUNT=20`个；新检查点先提交，再在独立事务清理更老版本，清理失败不能撤销刚完成的版本。

`POST /api/presentations/{presentation_id}/versions/{version}/restore` 请求体为`{"base_version": 9}`。恢复仍执行owner与乐观锁；成功把历史稿写成新的当前版本`base_version + 1`，同时新增`reason=restore`检查点，原历史行不修改，返回HTTP 200完整作品详情。旧基线返回脱敏409摘要；历史损坏或受限解压失败返回稳定500且不回显压缩体。读取兼容迁移前的原始JSON检查点，新写入统一使用`gzip+base64-v1`自描述信封。

## 7. PPTX归档、缩略图与历史下载

`POST /api/presentations/{presentation_id}/exports/pptx` 的请求体是浏览器PptxGenJS生成的原始PPTX字节，`Content-Type`固定为OpenXML PPTX类型；请求头必须带`Idempotency-Key`、`X-Presentation-Version`和浏览器对同一Blob计算的`X-Content-SHA256`。服务端重新计算SHA、校验真实ZIP/OpenXML结构并通过Storage Adapter保存，owner只取Session。同一owner和幂等键的完全相同请求返回同一导出记录并标记`reused=true`；内容、作品或版本变化返回409，不能重复占额或创建记录。第一版PPTX导出免费，不触发计费接口。

`PUT /api/presentations/{presentation_id}/thumbnail` 接收PNG原始字节和SHA头，成功后把owner作品的`thumbnail_file_id`指向对象存储文件。缩略图失败不回滚已经成功的本地下载或PPTX归档。

`GET /api/presentations/{presentation_id}/exports` 返回当前owner、未软删除作品的导出历史、服务端文件SHA和短期`download_url`。`GET /api/files/{file_id}/download?expires=...&signature=...`仍要求有效Session；签名绑定owner、file ID和过期时间，默认5分钟，最长1小时。跨owner、软删除作品、无效签名统一不能读取；过期返回410。响应使用`Cache-Control: no-store`、安全ASCII回退文件名和RFC 5987 UTF-8文件名，并返回`X-Content-SHA256`。浏览器下载后再次核对SHA才保存到本地。

## 8. 稳定错误体

```json
{
  "code": "PRESENTATION_NOT_FOUND",
  "message": "作品不存在",
  "retryable": false,
  "request_id": "d73b3b4de9c44c669178185710a1cb95"
}
```

| HTTP | code | 含义 |
|---|---|---|
| 400 | `PRESENTATION_IDEMPOTENCY_KEY_INVALID` | 幂等键缺失或格式无效 |
| 403 | `AUTH_ORIGIN_REJECTED` | 写请求来源不受信任 |
| 404 | `PRESENTATION_NOT_FOUND` | 不存在、已删除或不属于当前用户 |
| 409 | `PRESENTATION_REQUEST_CONFLICT` | 幂等键被不兼容请求占用 |
| 409 | `PRESENTATION_LIMIT_REACHED` | 达到已配置的用户作品上限 |
| 409 | `PRESENTATION_NOT_EDITABLE` | 作品仍在生成、待结算或失败，不能保存当前稿 |
| 409 | `PRESENTATION_VERSION_CONFLICT` | `base_version`已过期；响应只给最新标题、版本和更新时间摘要，不回显服务端稿件 |
| 413 | `PRESENTATION_DOCUMENT_TOO_LARGE` | 当前稿UTF-8 JSON超过配置的10MiB上限 |
| 503 | `CHECKPOINT_STORAGE_UNAVAILABLE` | 压缩检查点超过1MiB且T19对象存储适配尚不可用 |
| 422 | `PRESENTATION_DOCUMENT_INVALID` | 当前稿schema或页面/元素骨架无效 |
| 422 | FastAPI校验错误 | 字段类型、长度、枚举或额外字段不合法 |
| 500 | `PRESENTATION_DATA_INVALID` | 已存编辑稿损坏，响应不回显原始数据 |
| 500 | `PRESENTATION_VERSION_DATA_INVALID` | 历史检查点损坏、超限或无法受限解压 |
| 400 | `EXPORT_HASH_MISMATCH` | 浏览器声明摘要与服务端计算结果不一致 |
| 404 | `EXPORT_NOT_FOUND` | 作品、归档或文件不存在、已删除或不属于当前用户 |
| 409 | `EXPORT_IDEMPOTENCY_CONFLICT` | 同一导出幂等键被用于不同内容 |
| 409 | `EXPORT_VERSION_CONFLICT` | 归档时作品版本已变化 |
| 410 | `DOWNLOAD_URL_EXPIRED` | 短期下载地址已过期，需刷新历史列表 |

## 9. 当前边界

- T09～T14已实现创建、列表、详情、复制、软删除、自动保存、多标签乐观锁、检查点列表与恢复；T20增加同Blob归档、缩略图和历史下载。
- T15～T18已在持久任务外层增加票据权益固化及reserve/settle/release；是否创建计费意图仍由环境开关控制。
- 真实业务处理器已复用大纲/正文 A2A Agent，并用租约令牌围栏持久化基础可编辑文档；已确认的 Markdown 大纲不会重复调用大纲 Agent。
- 部署环境在完成对应 Gate 前仍保持`BILLING_ENABLED=false`和`TASK_WORKER_ENABLED=false`；HTTP 202只证明事务入队，不等于Agent、结算或PPT生成成功。
