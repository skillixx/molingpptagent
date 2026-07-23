# TrainPPTAgent 文件能力与 G0 回归基线

> 验证时间：2026-07-23（Asia/Shanghai）
> 范围：M0 / G0；不代表真实墨灵入口、生产计费或生产流量验收。
> 安全约束：本文不记录主机名、账号、令牌、数据库 URL 或对象存储凭据。

## 1. 结论

- 现有大纲和正文服务完成真实 DeepSeek 调用，均返回 HTTP 200；正文流包含结束标记和幻灯片字段，不是 Mock 200。
- TXT、DOCX、PDF、PPTX 均完成真实转换和 PersonalDB `/upload/` 处理，四种格式都返回非空 Markdown 和 Embedding 结果；隔离测试用户的真实检索返回了本次样例标记。
- 依据文件链路的“转换、Embedding、检索”已分别通过；经主 API 串联“上传后生成大纲和正文”的一次长调用未在合理窗口内结束，由本次测试主动终止，因此不得记为依据文件生成通过。B-06 继续由 T07、T23 关闭。
- 现有编辑器可进入，浏览器控制台无错误；本地 PPTX 成功导出并由 Microsoft PowerPoint COM 实际打开。截图只证明页面可见和布局状态，不证明生成内容的视觉质量。
- 当前 MySQL 完成只读连通和版本检查；对象存储完成只读 Bucket 元数据请求。没有对真实数据库执行迁移，也没有向对象存储写入或删除对象。

## 2. 服务与生成基线

| 能力 | 验证方式 | 结果 | 边界 |
|---|---|---|---|
| 主 API | `GET http://127.0.0.1:6800/healthz` | HTTP 200 | 健康检查不等于下游可用 |
| Outline Agent | `GET /.well-known/agent.json`，再调用 `/tools/aippt_outline` | HTTP 200，返回非空真实模型内容 | 未评价内容质量 |
| Content Agent | `GET /.well-known/agent.json`，再调用 `/tools/aippt` | HTTP 200，包含 `[DONE]` 和幻灯片字段 | 未进行逐页视觉验收 |
| PersonalDB | 端口、真实上传与检索 | 四格式上传和隔离用户检索通过 | 进程命令行归属因本机 CIM 查询失败未完全证明，但未停止或修改该进程 |
| 前端 | Playwright 打开首页与编辑器 | HTTP 200；控制台 0 error、0 warning | 仅桌面 G0 回归，四档适配在对应前端任务验收 |

运行中的 Python/Node 进程启动时间与本项目既有服务一致，但本轮没有重启服务，也没有停止任何未知端口进程。

## 3. 文件支持矩阵

隔离标识：测试用户 `990023`，文件 ID `99002301`～`99002304`。样例位于 `output/g0/`，不含真实用户数据。

| 格式 | 直接转换 | 主文本特征 | PersonalDB 上传 | Embedding | 隔离检索 | 已知限制 |
|---|---:|---:|---:|---:|---:|---|
| TXT | 通过，62字符 | 精确标记存在 | HTTP 200，62字符 | 通过 | 通过 | 仅验证 UTF-8 小文件 |
| DOCX | 通过，76字符 | 标题与 `MOLING` 可检出；完整标记被结构分段 | HTTP 200，76字符 | 通过 | 通过 | 结构提取通过，不代表版式保真 |
| PDF | 通过，74字符 | 精确标记存在 | HTTP 200，74字符 | 通过 | 通过 | 仅验证文本型 PDF，未验证扫描 OCR |
| PPTX | 通过，91字符 | 精确标记存在 | HTTP 200，91字符 | 通过 | 通过 | 仅验证文本提取，不代表母版、动画或视觉保真 |

检索请求针对隔离用户返回 HTTP 200、非空结果，并命中 `MOLING_G0_KNOWLEDGE_20260723`。这项G0证据只证明本次样例的转换、Embedding与检索，不单独证明多用户命名空间隔离；B-08的后续关闭证据见下方T07复验。

### T07 复合命名空间复验（2026-07-23）

- 使用当前代码在独立9101端口启动本仓库PersonalDB；既有9100进程因无法取得完整命令行归属而保持不动，未停止、替换或借其冒充新代码验证。
- 主体契约为`moling:<environment>:<app_id>:<user_id>`，PersonalDB只接受该结构、固定本地主体或旧数字主体；复合主体经SHA-256摘要映射到Chroma安全集合名，日志只记录不可逆短摘要。
- TXT、DOCX、PDF、PPTX再次真实上传，均返回HTTP 200、非空Markdown和Embedding结果；字符数分别为62、76、74、91，与G0样例结果一致。
- 两个隔离测试主体使用相同文件名`same-name.txt`和相同file ID写入不同标记，各自检索只命中自己的标记且不含另一主体标记，证明跨用户同名文件隔离通过；环境、应用和用户任一维度变化会产生不同集合的行为另有自动化测试。
- 当前代码的旧大纲接口真实尝试返回HTTP 200并收到真实Agent分片，但调用未形成客户端可记录的完整终态，随后只停止本轮创建的6801主API门面，未停止大纲/正文Agent。因此本项记为“真实分片已出现、完整生成未验证”，不把200或分片写成依据文件生成通过；B-06继续保持`partial_verified`并由T23完成最终端到端验收。
- 支持边界不变：TXT仅验证UTF-8小文件；DOCX/PPTX只证明文本提取，不证明版式、母版或动画；PDF只验证文本型文件，扫描件OCR仍未验证。主API对其他扩展名返回HTTP 415和明确中文提示。
- 复验脚本：`output/t07/verify_personaldb_namespace.py`；两个测试集合及其向量保留在本地测试Chroma数据中，未执行批量删除或触碰既有用户数据。本轮9101和6801门面均已停止。

## 4. 编辑、导出与 PowerPoint

- Playwright 从首页进入 `/editor`，页面截图：`output/playwright/g0-editor.png`。
- 浏览器控制台：2条普通消息，0条错误，0条警告。
- 导出文件：`.playwright-cli/G0回归验证.pptx`，45,824字节，1页。
- OOXML 基本结构存在：`[Content_Types].xml` 可读取。
- SHA-256：`A970C2E5628A2D15AD14AD96536F4292FEF1508A8F7FA804D9799E2D184F9086`。
- Microsoft PowerPoint COM 实际打开成功，读取到1页。

本轮打开的是空白编辑页，能够证明既有编辑与导出回归，但不能证明模型生成主题的页面视觉质量。主题内容生成已在 API 层真实通过，端到端主题套用和视觉验收留在 T23。

## 5. MySQL 与对象存储

### MySQL

- 使用当前本地 `.env` 的现有连接做只读 `SELECT 1` 和 `SELECT VERSION()`，结果成功。
- 实际版本为 MySQL 8.0.46，支持设计中优先采用的 `SKIP LOCKED`。
- 没有执行 Alembic、建表、写入、锁竞争或降级操作；G0 只要求最小连通。

### 对象存储

- 使用现有配置进行签名的只读 `HeadBucket`，返回 HTTP 200。
- 没有上传、覆盖、下载或删除对象，也没有创建或删除云资源。
- 当前 endpoint 使用 HTTP 而非 HTTPS；仅可作为当前环境的只读连通证据，生产接入前必须提供 TLS endpoint 或经受控内网反向代理完成加密边界评审。

## 6. 可复现命令与证据

- 自动化：`.venv312\\Scripts\\python.exe -m pytest backend/main_api -q`，34通过。
- 文件上传：`.venv312\\Scripts\\python.exe output/g0/verify_personaldb.py`。
- 依据文件串联尝试：`.venv312\\Scripts\\python.exe output/g0/verify_basis_generation.py`；长时间无终态后仅终止本轮自有测试进程，未停止项目服务。
- Alembic：`.venv312\\Scripts\\alembic.exe -c alembic.ini history`。
- 浏览器证据：`output/playwright/g0-editor.png` 与 `.playwright-cli/G0回归验证.pptx`。

## 7. 未验证边界与回滚

- 未调用真实墨灵 SSO、verify、计费、历史作品或生产页面；`BILLING_ENABLED` 保持 `false`。
- 未验证生产 MySQL 迁移、对象存储写读删、多用户隔离、任务恢复、计费幂等和历史归档。
- 未验证扫描 PDF OCR、复杂 Word/PPT 版式、Embedding 质量指标、生成 PPT 的逐页视觉质量。
- G0 证据文件和隔离 PersonalDB 样例可在后续验收完成后按明确数据清理规则处理；本轮不删除既有数据。
- 发生回归时可关闭新增功能开关并停止使用 M0 新链路；空迁移基线不含业务表，禁止通过数据库降级删除业务数据。
