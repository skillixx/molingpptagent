# 科技蓝扁平 PPT 模板素材与 QA 记录

## 1. 记录信息

| 项目 | 内容 |
|---|---|
| 模板 ID | `template_8` |
| 模板名称 | 科技蓝扁平 |
| 参考 PPT | `C:\Users\sk20\Desktop\扁平风格(38).pptx` |
| 验收日期 | 2026-08-21 |
| 当前状态 | `DONE` |
| 页面比例 | 16:9 |
| 逻辑画布 | 1000 × 562.5 |
| MVP 页数 | 12 |
| 生产版页数 | 18 |
| Git 状态 | 已提交并推送至 `codex/fix-template-8-generation`；未创建PR、合并或部署 |

本记录保存 `template_8` 的素材来源、页面结构、自动测试、浏览器端到端验证、PPTX往返证据和已知限制。

## 2. 参考模板与版权处理

- 参考 PPT 实际为27页，项目前端 `pptxtojson` 链路成功解析。
- 27页已逐页检查，页面映射记录位于 `.codex-tmp/template_8_goal/template-frame-map.json`。
- 原稿只用于深蓝灰、青色低多边形、斜线、线框网络和页面类型参考。
- 原城市照片、固定年份、“XXX设计PPT模版”“FEI ER SHE JI”和英文示例正文均未进入生产模板。
- 原稿使用的非标准字体未进入生产模板；模板统一使用微软雅黑和 Arial。
- 生产模板使用原创生成位图与PPTist可编辑形状，不复用来源不明的照片和装饰。

## 3. 最终素材

### 3.1 文件清单

| 文件 | 字节 | 尺寸 | 模式 | SHA-256前12位 | 结果 |
|---|---:|---:|---|---|---|
| `template_8_asset_bg_dark_v1.jpg` | 75,707 | 1920×1080 | RGB | `dd12ada828f3` | 中央低干扰；无文字和水印 |
| `template_8_asset_network_mesh_v1.png` | 441,657 | 1672×941 | RGBA | `ae3f8af7fdb0` | Alpha 0～255；完整透明边缘 |
| `template_8_asset_tech_glow_v1.png` | 886,617 | 1672×941 | RGBA | `dd9c2b0263aa` | Alpha 0～252；无矩形底 |
| `template_8.jpg` | 35,980 | 960×540 | RGB | `219a706307a8` | 由真实封面导出并压缩 |

- 3项 `template_8_asset_*` 素材全部被JSON引用，没有缺失或未引用素材。
- 背景小于300KB；两张透明装饰均小于1MB。
- 原始图片保留在 `.codex-tmp/template_8_goal/source-assets/`。

### 3.2 生成方式和提示词

生成方式：Codex 内置图片生成工具，规划口径为 GPT Image 2（`gpt-image-2`）。每种素材独立生成，发布文件复制到 `backend/main_api/template/`。

#### 深色背景

```text
Use case: stylized-concept
Asset type: 16:9 PowerPoint full-slide background for a reusable technology presentation template
Primary request: an original restrained deep slate-blue and charcoal technology background, premium flat-design mood, subtle matte paper-grain texture, extremely faint cyan atmospheric glow near the far lower-left and far upper-right edges
Style/medium: polished abstract digital background, mostly flat and minimal, not a UI, not a dashboard
Composition/framing: exact widescreen 16:9 landscape; keep the central 80% calm, dark, and low-detail for editable titles, paragraphs, diagrams, and images; all visual interest must stay close to the perimeter
Lighting/mood: quiet professional technology atmosphere, high readability, restrained contrast
Color palette: deep slate blue #404F64, near-black navy #17191D, cyan accents #46A4DB and #28A7CF
Constraints: fully original; no text, letters, numbers, logos, watermarks, people, products, screens, charts, icons, city photography, frames, borders, or embedded slide elements; no large foreground objects; no bright center; no collage
Avoid: cyberpunk neon, glossy 3D, busy circuits, dramatic lens flares, stock-template text areas
```

#### 透明网络装饰

```text
Use case: stylized-concept
Asset type: reusable transparent PowerPoint decorative cutout
Primary request: one original sparse geometric technology network mesh made of thin cyan-blue lines, small circular nodes, and a few subtle diamond facets, inspired by clean flat corporate presentation graphics
Style/medium: crisp minimal digital linework, flat and elegant, no 3D scene
Composition/framing: a single wide corner-oriented cluster with an irregular triangular silhouette; complete linework and nodes visible; generous transparent padding; visual density concentrated toward one outer corner and fading inward
Color palette: cyan #46A4DB, bright cyan #28A7CF, a few white highlights with restrained transparency
Constraints: genuinely transparent background with alpha channel; one isolated decorative object only; no rectangle, no dark backdrop, no text, letters, numbers, logos, icons, watermark, people, screens, charts, or UI; no cropped nodes or lines; suitable for placement at the upper-right or lower-left edge of a 16:9 slide
Avoid: busy circuit board, neon cyberpunk glow, stock watermark, opaque background, checkerboard pattern
```

#### 透明科技光晕

```text
Use case: stylized-concept
Asset type: reusable transparent PowerPoint lighting-effect cutout
Primary request: one soft restrained cyan technology glow, a smooth elongated diagonal light haze with a few very subtle particles, designed to add depth behind editable flat slide shapes without becoming a focal object
Style/medium: minimal atmospheric light effect, clean corporate presentation aesthetic
Composition/framing: wide low-density effect with generous transparent padding; brightest area offset toward one end and fading fully to transparency on every edge; complete effect visible
Color palette: cyan #46A4DB, pale cyan #8EDDF2, tiny white highlights
Lighting/mood: quiet, refined, professional, low contrast
Constraints: genuinely transparent background with alpha channel; one isolated glow effect only; no rectangle, no dark backdrop, no text, letters, numbers, logos, icons, watermark, people, screens, charts, mesh, lens-flare rings, or hard-edged shapes
Avoid: neon cyberpunk, opaque gradient box, checkerboard pattern, saturated electric blue, strong center hotspot
```

可选城市剪影未生成。首版18页没有实际引用需求，避免增加未引用资源。

## 4. 模板结构

| 页面类型 | 数量 | 版式 |
|---|---:|---|
| 封面 `cover` | 2 | 几何封面、图文封面 |
| 目录 `contents` | 6 | 2、3、4、5、6、10项 |
| 章节 `transition` | 2 | 标准、光效变体 |
| 内容 `content` | 6 | 单结论、2项、3项、4项、单图文、双图文 |
| 结束 `end` | 2 | 简洁、网络变体 |
| 合计 | 18 | 12页标记为MVP |

结构检查结果：

- JSON：217,001字节，小于1MB。
- 页面和元素ID合计409个，409个唯一。
- 4个内容图片槽全部不带 `groupId`，可以直接单击替换。
- 背景和装饰使用 `imageType: decoration`。
- 内容图片使用 `imageType: content`。
- JSON不包含Base64大图。

## 5. 修改和新增文件

- `backend/main_api/template/template_8.json`
- `backend/main_api/template/template_8.jpg`
- `backend/main_api/template/template_8_asset_bg_dark_v1.jpg`
- `backend/main_api/template/template_8_asset_network_mesh_v1.png`
- `backend/main_api/template/template_8_asset_tech_glow_v1.png`
- `backend/main_api/main.py`
- `backend/main_api/tests/test_template_8.py`
- `doc/科技蓝扁平PPT模板开发说明.md`
- `doc/科技蓝扁平PPT模板开发Goal.md`
- `doc/科技蓝扁平PPT模板素材与QA记录.md`

初版开发未修改模板渲染器和前端业务代码；后续真实生成故障修复已增加模板错误分类、资源校验和前端安全失败提示，详见第12节。

后续故障修复涉及：

- `backend/main_api/workers/template_renderer.py`
- `backend/main_api/workers/presentation_handler.py`
- `backend/main_api/api/presentations.py`
- `backend/main_api/repositories/resources.py`
- `backend/main_api/services/presentations.py`
- `backend/main_api/schemas/presentations.py`
- `backend/main_api/tests/test_template_renderer.py`
- `backend/main_api/tests/test_presentation_handler.py`
- `backend/main_api/tests/test_presentations_api.py`
- `backend/main_api/tests/fixtures/template_8_real_outlines.json`
- `frontend/src/services/presentations.ts`
- `frontend/src/store/presentationEditor.ts`
- `frontend/src/views/Editor/PresentationLoader.vue`
- 对应的前端状态仓库和加载页测试。

## 6. 自动化验证

### 6.1 模板专项与渲染器

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_8.py backend/main_api/tests/test_template_renderer.py -q
```

结果：`36 passed in 0.91s`。

专项测试覆盖：

- 18页结构和12页MVP标记。
- 2、3、4、5、6、10项目录精确选择。
- 1～4项纯文字内容选择。
- 8项内容分页和顺序保持。
- 长正文不静默截断。
- 0、1、2张内容图。
- 内容图与装饰图隔离。
- 空图片地址、损坏JSON、外置资源和ID唯一性。
- 字号门槛和示例文案清理。

### 6.2 全量后端

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests -q
```

结果：`403 passed in 45.77s`。

### 6.3 前端

```powershell
cd frontend
npm run type-check
npm run test:unit -- --run
npm run build-only
```

结果：

- Vue/TypeScript类型检查通过。
- 23个测试文件、101项测试通过。
- Vite生产构建通过。
- 构建保留项目已有的大包体警告，没有新增前端依赖或业务代码。

## 7. 接口与运行基线

主API使用根 `.env`、`RELEASE_COMMIT` 和 `RELEASE_CHANNEL=production` 最小重启后完成复验。

| 检查 | 结果 |
|---|---|
| `GET /healthz` | 200，release commit正确 |
| `GET /templates` | 返回“科技蓝扁平”与`template_8` |
| `GET /data/template_8.json` | 200，`application/json` |
| `GET /data/template_8.jpg` | 200，`image/jpeg` |
| 3项素材接口 | 全部200，MIME正确 |

本次只重启主API；前端、大纲服务、Slide Agent和Worker没有因模板注册被重启。

## 8. 端到端QA

### 8.1 真实生成

- 使用生产 `PresentationTemplateRenderer` 生成覆盖五种页面类型的作品。
- 输入包含1～4项正文、单图文、双图文和8项分页。
- 8项内容被拆成两页，生成结果共12页。
- 12页在项目编辑器中全部加载，控制台无警告和错误。
- 生成结果总览：`.codex-tmp/template_8_goal/qa/template_8_12page_generated_montage.jpeg`。

### 8.2 文字编辑

- 双击内容页标题进入编辑状态。
- 将“先给出一个明确结论”改为“结论清晰，行动自然发生”。
- 页面立即显示新文本，编辑器没有控制台错误。

### 8.3 图片替换

- 初次检查发现内容图与文字共用 `groupId`，导致只能选中整组。
- 修复后，所有内容图片槽均不带 `groupId`。
- 单击内容图片后显示“替换图片”入口。
- 选择新图片后，内容图源变为新的Base64数据。
- 背景和装饰仍保持 `/api/data/template_8_asset_*` 地址。

### 8.4 模板选择与设备适配

- 模板列表显示“科技蓝扁平”和真实封面。
- 点击后类名从 `template-card` 变为 `template-card selected`。
- 生成和返回按钮均可见。

| 视口 | 页面宽度 | 文档宽度 | 横向溢出 | 生成按钮 |
|---|---:|---:|---|---|
| 1920×1080 | 1920 | 1920 | 无 | 可见 |
| 1366×768 | 1366 | 1362 | 无 | 可见 |
| 768×1024 | 768 | 763 | 无 | 可见 |
| 390×844 | 390 | 386 | 无 | 可见 |

- 生成失败场景显示“PPT生成中断，请返回模板页重试”。
- 失败后按钮恢复为可点击“生成PPT”，可以重试。

### 8.5 PPTX导出和重新打开

- 导出文件：`.codex-tmp/template_8_goal/exports/template_8_qa.pptx`。
- 文件大小：7,056,470字节。
- ZIP完整性：`ZipFile.testzip()` 返回 `None`。
- OOXML幻灯片：12页；备注：12页。
- 项目编辑器重新导入：12页，控制台无警告和错误。
- 重新导入后封面、结束页、字体、图片和装饰保持可见。
- PPTX重新导入后逻辑尺寸归一为960×540，比例仍为16:9，页面内容和布局保持稳定。

通用演示文稿辅助渲染工具在当前Windows环境无法渲染该PPTX，也没有返回具体页面错误。最终采用项目自身 `pptxtojson` 重新导入和OOXML ZIP结构两条独立路径验证。

## 9. 视觉证据

- 18页模板总览：`.codex-tmp/template_8_goal/qa/template_8_18page_montage.jpeg`。
- 12页生成结果总览：`.codex-tmp/template_8_goal/qa/template_8_12page_generated_montage.jpeg`。
- QA PPTX：`.codex-tmp/template_8_goal/exports/template_8_qa.pptx`。
- 真实封面源图：`.codex-tmp/template_8_goal/exports/template_8_cover_source.jpeg`。
- 参考PPT解析结果：`.codex-tmp/template_8_goal/reference-import.json`。
- 页面映射：`.codex-tmp/template_8_goal/template-frame-map.json`。

18页逐页检查结果：

- 标题、正文、图片和装饰没有意外重叠。
- 页面标题保持单行。
- 目录两位编号没有拆行。
- 单图文和双图文的图片框可替换。
- 没有残留参考模板文字、城市照片、第三方Logo和水印。
- 相邻页面保持统一视觉语言，封面、目录、章节、内容和结束页构图有区分。

## 10. 已知限制

- 模板不包含真实公司Logo、真实人物和固定内容照片；真实项目由用户或图片池提供内容图。
- QA双图文使用模板原创网络和光效素材作为替换示例，不代表真实业务内容。
- 当前机器的通用演示辅助渲染工具不可用；项目编辑器导入、OOXML结构和浏览器逐页总览均已通过。
- 经用户授权，本任务已提交并推送至 `codex/fix-template-8-generation`；未创建PR、合并或部署。

## 11. 人工确认

自动验收状态：已通过。

Goal状态：`DONE`。

用户已于 2026-08-24 明确回复“确认完成”，人工确认门禁已通过，持久Goal可以执行最终闭合。

## 12. 生产故障回归证据（2026-08-24）

旧的人工确认只适用于模板初次开发，不能替代本次生产故障修复的G8验收。本次状态以本节为准。

### 12.1 自动回归

| 检查 | 结果 |
|---|---|
| template_8专项 | 55通过 |
| backend/main_api/tests | 444通过 |
| 前端类型检查 | 通过 |
| 前端单元测试 | 23文件、110通过 |
| 前端生产构建 | 通过，只有既有大包体警告 |
| 模板JSON | 18页，12页MVP，约220KB |
| 资源与ID | 外置资源存在，页面和元素ID唯一 |

### 12.2 新增夹具与红绿证据

- 脱敏夹具：`backend/main_api/tests/fixtures/template_8_real_outlines.json`。
- 修复前：11个新增容量用例稳定出现 `TemplateRenderError`。
- 第一轮模板修复后：48个template_8用例通过。
- 真实任务在最后阶段再次暴露结束页容量后，新增结束页100字说明与80字标题用例；修复前失败，第一轮扩容后49项通过；补齐正文长度矩阵、混排目录和资源缺失后最终55项通过。
- 任何测试均未截断文字、删除项目、降低原断言或跳过边界校验。

### 12.3 外部阻断

正文Agent日志确认上游模型返回 `Insufficient Balance`，LiteLLM重试3次后仍失败，A2A流式连接表现为HTTP 503与`incomplete chunked read`。重启正文Agent不能恢复，因为根因是上游额度而不是本机进程。

该阻断随后恢复。新一轮真实任务取得3个template_8连续成功和1个template_7成功，全部为ready、succeeded、100%，错误码为空。余额故障作为独立历史事件保留，不计入模板回归失败。

### 12.4 真实任务和编辑器证据

- template_8任务：`80232f15-2648-4191-8d41-fc06de2cb7bd`、`dabd62bd-017d-4bff-afe1-52ab28b8069d`、`f9396c9f-2e5e-4d1d-bf1a-60d01e1caefe`。
- template_7回归任务：`9cbd62cf-5d0f-41b3-9744-e4ed4578d021`。
- 真实任务结构审计：所有任务ID唯一；template_8真实页面最小字号12.5px；template_7最小字号12px。
- 文字编辑：封面标题改为“社交媒体与品牌营销·验收通过”，编辑器显示“已保存”。
- 图片替换：内容图源从项目资源地址变为新PNG的Data URL，装饰仍使用项目资源地址，编辑器显示“已保存”。
- PPTX：`.codex-tmp/template_8_goal/exports/template_8_real_editor_qa.pptx`，7,867,363字节，12页。
- 重新导入：项目同款 `pptxtojson` 解析为12页、273个元素。
- 响应式截图：`.codex-tmp/template_8_goal/qa/editor-responsive-1920x1080.png`、`editor-responsive-1366x768.png`、`editor-responsive-768x1024.png`、`editor-responsive-390x844.png`。
- 失败提示截图：`.codex-tmp/template_8_goal/qa/failed-retry-390x844.png`。
- 四种视口的页面 `scrollWidth` 均等于 `clientWidth`，无横向溢出；浏览器控制台无warning/error。

### 12.5 最终状态

自动验收状态：`DONE`。

用户已于2026-08-24明确回复“确认完成”，本次故障修复的最终人工门禁已通过，持久Goal已标记为DONE。
